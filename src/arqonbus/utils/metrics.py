"""Metrics collection for ArqonBus commands and system."""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from ..config.config import get_config


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with metadata."""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricCollector:
    """Collects and manages metrics for ArqonBus."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize metric collector.
        
        Args:
            max_history: Maximum number of metric values to keep in history
        """
        self.max_history = max_history
        self._metrics: Dict[str, Dict[str, List[MetricValue]]] = defaultdict(lambda: defaultdict(list))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        
        # Command execution metrics
        self._command_metrics = {
            "executions": defaultdict(int),
            "durations": defaultdict(list),
            "successes": defaultdict(int),
            "failures": defaultdict(int),
            "errors": defaultdict(int)
        }
        
        # System metrics
        self._system_metrics = {
            "start_time": datetime.utcnow(),
            "uptime_seconds": 0,
            "active_connections": 0,
            "total_messages": 0,
            "total_commands": 0,
            "error_rate": 0.0
        }
        
        # Performance metrics
        self._performance_metrics = {
            "message_routing_latency": deque(maxlen=100),
            "command_execution_latency": deque(maxlen=100),
            "websocket_connection_time": deque(maxlen=100),
            "storage_operation_time": deque(maxlen=100)
        }
    
    def record_counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Record a counter metric.
        
        Args:
            name: Metric name
            value: Counter value
            labels: Optional labels for the metric
        """
        labels = labels or {}
        self._counters[name] += value
        
        # Add to history
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels
        )
        self._metrics[name]["counter"].append(metric_value)
        
        # Trim history if needed
        if len(self._metrics[name]["counter"]) > self.max_history:
            self._metrics[name]["counter"] = self._metrics[name]["counter"][-self.max_history:]
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels for the metric
        """
        labels = labels or {}
        self._gauges[name] = value
        
        # Add to history
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels
        )
        self._metrics[name]["gauge"].append(metric_value)
        
        # Trim history if needed
        if len(self._metrics[name]["gauge"]) > self.max_history:
            self._metrics[name]["gauge"] = self._metrics[name]["gauge"][-self.max_history:]
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric.
        
        Args:
            name: Metric name
            value: Histogram value
            labels: Optional labels for the metric
        """
        labels = labels or {}
        
        # Add to history
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels
        )
        self._metrics[name]["histogram"].append(metric_value)
        
        # Trim history if needed
        if len(self._metrics[name]["histogram"]) > self.max_history:
            self._metrics[name]["histogram"] = self._metrics[name]["histogram"][-self.max_history:]
    
    def start_timer(self, name: str) -> "TimerContext":
        """Start a timer for a metric.
        
        Args:
            name: Timer metric name
            
        Returns:
            Timer context manager
        """
        return TimerContext(self, name)
    
    def record_command_execution(
        self,
        command_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record command execution metrics.
        
        Args:
            command_name: Name of executed command
            duration: Execution duration in seconds
            success: Whether command succeeded
            error: Error message if failed
        """
        self._command_metrics["executions"][command_name] += 1
        self._command_metrics["durations"][command_name].append(duration)
        
        if success:
            self._command_metrics["successes"][command_name] += 1
        else:
            self._command_metrics["failures"][command_name] += 1
            if error:
                self._command_metrics["errors"][command_name] += 1
        
        # Keep only recent durations (last 100 executions per command)
        if len(self._command_metrics["durations"][command_name]) > 100:
            self._command_metrics["durations"][command_name] = \
                self._command_metrics["durations"][command_name][-100:]
        
        # Record histogram
        self.record_histogram(f"command_duration_seconds", duration, {"command": command_name})
        
        # Record success/failure counters
        if success:
            self.record_counter(f"command_success_total", 1, {"command": command_name})
        else:
            self.record_counter(f"command_failure_total", 1, {"command": command_name})
    
    def record_message_routing(self, duration: float, message_type: str, destination: str):
        """Record message routing metrics.
        
        Args:
            duration: Routing duration in seconds
            message_type: Type of message routed
            destination: Routing destination
        """
        self._performance_metrics["message_routing_latency"].append(duration)
        
        # Record histogram
        self.record_histogram(
            "message_routing_duration_seconds",
            duration,
            {"message_type": message_type, "destination": destination}
        )
        
        # Record counter
        self.record_counter("message_routing_total", 1, {"message_type": message_type})
    
    def record_websocket_connection(self, connection_time: float, client_id: str):
        """Record WebSocket connection metrics.
        
        Args:
            connection_time: Time to establish connection in seconds
            client_id: Client identifier
        """
        self._performance_metrics["websocket_connection_time"].append(connection_time)
        
        # Record histogram
        self.record_histogram(
            "websocket_connection_duration_seconds",
            connection_time,
            {"client_id": client_id}
        )
    
    def record_storage_operation(self, operation: str, duration: float, success: bool):
        """Record storage operation metrics.
        
        Args:
            operation: Type of storage operation
            duration: Operation duration in seconds
            success: Whether operation succeeded
        """
        self._performance_metrics["storage_operation_time"].append(duration)
        
        # Record histogram
        self.record_histogram(
            "storage_operation_duration_seconds",
            duration,
            {"operation": operation, "success": str(success)}
        )
        
        # Record counter
        self.record_counter(
            "storage_operation_total",
            1,
            {"operation": operation, "success": str(success)}
        )
    
    def update_system_metrics(self, active_connections: int, total_messages: int, total_commands: int):
        """Update system-level metrics.
        
        Args:
            active_connections: Number of active connections
            total_messages: Total messages processed
            total_commands: Total commands executed
        """
        self._system_metrics["active_connections"] = active_connections
        self._system_metrics["total_messages"] = total_messages
        self._system_metrics["total_commands"] = total_commands
        self._system_metrics["uptime_seconds"] = (datetime.utcnow() - self._system_metrics["start_time"]).total_seconds()
        
        # Calculate error rate
        total_executions = sum(self._command_metrics["executions"].values())
        total_errors = sum(self._command_metrics["errors"].values())
        self._system_metrics["error_rate"] = total_errors / max(1, total_executions)
        
        # Record gauge metrics
        self.record_gauge("active_connections", active_connections)
        self.record_gauge("total_messages", total_messages)
        self.record_gauge("total_commands", total_commands)
        self.record_gauge("uptime_seconds", self._system_metrics["uptime_seconds"])
        self.record_gauge("error_rate", self._system_metrics["error_rate"])
    
    def get_command_metrics(self, command_name: Optional[str] = None) -> Dict[str, Any]:
        """Get command execution metrics.
        
        Args:
            command_name: Specific command to get metrics for (None for all)
            
        Returns:
            Command metrics dictionary
        """
        if command_name:
            if command_name not in self._command_metrics["executions"]:
                return {}
            
            durations = self._command_metrics["durations"][command_name]
            return {
                "command": command_name,
                "executions": self._command_metrics["executions"][command_name],
                "successes": self._command_metrics["successes"][command_name],
                "failures": self._command_metrics["failures"][command_name],
                "errors": self._command_metrics["errors"][command_name],
                "success_rate": self._command_metrics["successes"][command_name] / max(1, self._command_metrics["executions"][command_name]),
                "average_duration": sum(durations) / len(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "duration_samples": len(durations)
            }
        else:
            # Return metrics for all commands
            all_metrics = {}
            for cmd_name in self._command_metrics["executions"].keys():
                all_metrics[cmd_name] = self.get_command_metrics(cmd_name)
            return all_metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics.
        
        Returns:
            System metrics dictionary
        """
        return {
            "start_time": self._system_metrics["start_time"].isoformat(),
            "uptime_seconds": self._system_metrics["uptime_seconds"],
            "active_connections": self._system_metrics["active_connections"],
            "total_messages": self._system_metrics["total_messages"],
            "total_commands": self._system_metrics["total_commands"],
            "error_rate": self._system_metrics["error_rate"],
            "counters": dict(self._counters),
            "gauges": dict(self._gauges)
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        metrics = {}
        
        for metric_name, values in self._performance_metrics.items():
            if values:
                metrics[metric_name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "recent_values": list(values)[-10:]  # Last 10 values
                }
            else:
                metrics[metric_name] = {"count": 0}
        
        return metrics
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.
        
        Returns:
            Complete metrics dictionary
        """
        return {
            "system": self.get_system_metrics(),
            "commands": self.get_command_metrics(),
            "performance": self.get_performance_metrics(),
            "raw_metrics": {
                name: {
                    metric_type: [
                        {"value": mv.value, "timestamp": mv.timestamp.isoformat(), "labels": mv.labels}
                        for mv in values
                    ]
                    for metric_type, values in metric_groups.items()
                }
                for name, metric_groups in self._metrics.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Add comment with timestamp
        lines.append(f"# Generated at {datetime.utcnow().isoformat()}")
        lines.append("")
        
        # Add system metrics
        lines.append("# System Metrics")
        lines.append(f'arqonbus_uptime_seconds {self._system_metrics["uptime_seconds"]}')
        lines.append(f'arqonbus_active_connections {self._system_metrics["active_connections"]}')
        lines.append(f'arqonbus_total_messages {self._system_metrics["total_messages"]}')
        lines.append(f'arqonbus_total_commands {self._system_metrics["total_commands"]}')
        lines.append(f'arqonbus_error_rate {self._system_metrics["error_rate"]}')
        lines.append("")
        
        # Add command metrics
        lines.append("# Command Metrics")
        for command_name, count in self._command_metrics["executions"].items():
            lines.append(f'arqonbus_command_executions_total{{command="{command_name}"}} {count}')
            lines.append(f'arqonbus_command_success_total{{command="{command_name}"}} {self._command_metrics["successes"][command_name]}')
            lines.append(f'arqonbus_command_failures_total{{command="{command_name}"}} {self._command_metrics["failures"][command_name]}')
        lines.append("")
        
        # Add performance metrics
        lines.append("# Performance Metrics")
        for metric_name, values in self._performance_metrics.items():
            if values:
                avg_value = sum(values) / len(values)
                lines.append(f'arqonbus_{metric_name}_avg {avg_value}')
        lines.append("")
        
        return "\n".join(lines)


class TimerContext:
    """Context manager for timing operations."""
    
    def __init__(self, collector: MetricCollector, metric_name: str):
        """Initialize timer context.
        
        Args:
            collector: Metric collector
            metric_name: Name of the metric
        """
        self.collector = collector
        self.metric_name = metric_name
        self.start_time = None
    
    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and record the metric."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_histogram(self.metric_name, duration)


# Global metric collector instance
_collector: Optional[MetricCollector] = None


def get_collector() -> MetricCollector:
    """Get the global metric collector instance.
    
    Returns:
        Metric collector instance
    """
    global _collector
    if _collector is None:
        _collector = MetricCollector()
    return _collector


def record_counter(name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
    """Record a counter metric.
    
    Args:
        name: Metric name
        value: Counter value
        labels: Optional labels for the metric
    """
    get_collector().record_counter(name, value, labels)


def record_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Record a gauge metric.
    
    Args:
        name: Metric name
        value: Gauge value
        labels: Optional labels for the metric
    """
    get_collector().record_gauge(name, value, labels)


def record_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Record a histogram metric.
    
    Args:
        name: Metric name
        value: Histogram value
        labels: Optional labels for the metric
    """
    get_collector().record_histogram(name, value, labels)


def start_timer(name: str) -> TimerContext:
    """Start a timer for a metric.
    
    Args:
        name: Timer metric name
        
    Returns:
        Timer context manager
    """
    return get_collector().start_timer(name)


def record_command_execution(
    command_name: str,
    duration: float,
    success: bool,
    error: Optional[str] = None
):
    """Record command execution metrics.
    
    Args:
        command_name: Name of executed command
        duration: Execution duration in seconds
        success: Whether command succeeded
        error: Error message if failed
    """
    get_collector().record_command_execution(command_name, duration, success, error)


def record_message_routing(duration: float, message_type: str, destination: str):
    """Record message routing metrics.
    
    Args:
        duration: Routing duration in seconds
        message_type: Type of message routed
        destination: Routing destination
    """
    get_collector().record_message_routing(duration, message_type, destination)


def record_websocket_connection(connection_time: float, client_id: str):
    """Record WebSocket connection metrics.
    
    Args:
        connection_time: Time to establish connection in seconds
        client_id: Client identifier
    """
    get_collector().record_websocket_connection(connection_time, client_id)


def record_storage_operation(operation: str, duration: float, success: bool):
    """Record storage operation metrics.
    
    Args:
        operation: Type of storage operation
        duration: Operation duration in seconds
        success: Whether operation succeeded
    """
    get_collector().record_storage_operation(operation, duration, success)


def get_all_metrics() -> Dict[str, Any]:
    """Get all collected metrics.
    
    Returns:
        Complete metrics dictionary
    """
    return get_collector().get_all_metrics()


def export_prometheus_format() -> str:
    """Export metrics in Prometheus format.
    
    Returns:
        Prometheus-formatted metrics string
    """
    return get_collector().export_prometheus_format()