"""Prometheus metrics exporter for ArqonBus.

This module provides Prometheus-compatible metrics export for monitoring
and observability systems.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict, deque

from .metrics import get_collector, MetricCollector

logger = logging.getLogger(__name__)


class PrometheusMetricsExporter:
    """Exports ArqonBus metrics in Prometheus format.
    
    Converts internal metrics to Prometheus-compatible format and provides
    HTTP endpoints for Prometheus scraping.
    """
    
    def __init__(self, collector: Optional[MetricCollector] = None):
        """Initialize Prometheus metrics exporter.
        
        Args:
            collector: Metric collector to export from
        """
        self.collector = collector or get_collector()
        
        # Prometheus metric names and help text
        self.metric_names = {
            # System metrics
            "uptime_seconds": "arqonbus_uptime_seconds",
            "active_connections": "arqonbus_active_connections",
            "total_messages": "arqonbus_total_messages",
            "total_commands": "arqonbus_total_commands",
            "error_rate": "arqonbus_error_rate",
            
            # Message metrics
            "message_routing_duration": "arqonbus_message_routing_duration_seconds",
            "messages_processed_total": "arqonbus_messages_processed_total",
            "messages_failed_total": "arqonbus_messages_failed_total",
            
            # Command metrics
            "command_executions_total": "arqonbus_command_executions_total",
            "command_duration": "arqonbus_command_duration_seconds",
            "command_success_total": "arqonbus_command_success_total",
            "command_failure_total": "arqonbus_command_failure_total",
            
            # Connection metrics
            "websocket_connections_total": "arqonbus_websocket_connections_total",
            "websocket_connection_duration": "arqonbus_websocket_connection_duration_seconds",
            
            # Storage metrics
            "storage_operations_total": "arqonbus_storage_operations_total",
            "storage_operation_duration": "arqonbus_storage_operation_duration_seconds",
            
            # Telemetry metrics
            "telemetry_events_total": "arqonbus_telemetry_events_total",
            "telemetry_broadcast_duration": "arqonbus_telemetry_broadcast_duration_seconds",
            "telemetry_active_clients": "arqonbus_telemetry_active_clients",
            
            # HTTP metrics
            "http_requests_total": "arqonbus_http_requests_total",
            "http_request_duration": "arqonbus_http_request_duration_seconds",
            "http_errors_total": "arqonbus_http_errors_total"
        }
        
        # Help text for metrics
        self.metric_help = {
            "uptime_seconds": "Number of seconds the ArqonBus server has been running",
            "active_connections": "Number of currently active WebSocket connections",
            "total_messages": "Total number of messages processed",
            "total_commands": "Total number of commands executed",
            "error_rate": "Current error rate as a fraction",
            "message_routing_duration": "Time spent routing messages",
            "messages_processed_total": "Total number of messages processed",
            "messages_failed_total": "Total number of messages that failed processing",
            "command_executions_total": "Total number of command executions",
            "command_duration": "Time spent executing commands",
            "command_success_total": "Total number of successful commands",
            "command_failure_total": "Total number of failed commands",
            "websocket_connections_total": "Total number of WebSocket connections",
            "websocket_connection_duration": "Time to establish WebSocket connections",
            "storage_operations_total": "Total number of storage operations",
            "storage_operation_duration": "Time spent on storage operations",
            "telemetry_events_total": "Total number of telemetry events",
            "telemetry_broadcast_duration": "Time spent broadcasting telemetry",
            "telemetry_active_clients": "Number of active telemetry clients",
            "http_requests_total": "Total number of HTTP requests",
            "http_request_duration": "Time spent on HTTP requests",
            "http_errors_total": "Total number of HTTP errors"
        }
    
    def export_metrics(self) -> str:
        """Export all metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Add comment with generation timestamp
        lines.append(f"# Generated at {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"# ArqonBus Prometheus Metrics")
        lines.append("")
        
        # Get metrics data
        metrics_data = self.collector.get_all_metrics()
        
        # Export system metrics
        lines.extend(self._export_system_metrics(metrics_data.get("system", {})))
        
        # Export command metrics
        lines.extend(self._export_command_metrics(metrics_data.get("commands", {})))
        
        # Export performance metrics
        lines.extend(self._export_performance_metrics(metrics_data.get("performance", {})))
        
        # Export raw metric values
        lines.extend(self._export_raw_metrics(metrics_data.get("raw_metrics", {})))
        
        return "\n".join(lines)
    
    def _export_system_metrics(self, system_metrics: Dict[str, Any]) -> List[str]:
        """Export system metrics.
        
        Args:
            system_metrics: System metrics data
            
        Returns:
            List of Prometheus-formatted metric lines
        """
        lines = []
        
        # System metrics
        for metric_name, value in system_metrics.items():
            if metric_name in self.metric_names and isinstance(value, (int, float)):
                prometheus_name = self.metric_names[metric_name]
                help_text = self.metric_help.get(metric_name, f"ArqonBus {metric_name}")
                
                # Add help and type comments
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} gauge")
                
                # Add metric value
                lines.append(f"{prometheus_name} {value}")
                lines.append("")
        
        return lines
    
    def _export_command_metrics(self, command_metrics: Dict[str, Any]) -> List[str]:
        """Export command-specific metrics.
        
        Args:
            command_metrics: Command metrics data
            
        Returns:
            List of Prometheus-formatted metric lines
        """
        lines = []
        
        if not isinstance(command_metrics, dict):
            return lines
        
        for command_name, metrics in command_metrics.items():
            if not isinstance(metrics, dict):
                continue
            
            # Command execution counter
            executions = metrics.get("executions", 0)
            if executions > 0:
                prometheus_name = self.metric_names["command_executions_total"]
                help_text = self.metric_help["command_executions_total"]
                
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} counter")
                lines.append(f'{prometheus_name}{{command="{command_name}"}} {executions}')
                lines.append("")
            
            # Command success/failure counters
            successes = metrics.get("successes", 0)
            failures = metrics.get("failures", 0)
            
            if successes > 0:
                prometheus_name = self.metric_names["command_success_total"]
                help_text = self.metric_help["command_success_total"]
                
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} counter")
                lines.append(f'{prometheus_name}{{command="{command_name}"}} {successes}')
                lines.append("")
            
            if failures > 0:
                prometheus_name = self.metric_names["command_failure_total"]
                help_text = self.metric_help["command_failure_total"]
                
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} counter")
                lines.append(f'{prometheus_name}{{command="{command_name}"}} {failures}')
                lines.append("")
            
            # Command duration histogram
            if "average_duration" in metrics:
                duration = metrics["average_duration"]
                prometheus_name = self.metric_names["command_duration"]
                help_text = self.metric_help["command_duration"]
                
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} histogram")
                lines.append(f'{prometheus_name}{{command="{command_name}"}} {duration}')
                lines.append("")
        
        return lines
    
    def _export_performance_metrics(self, performance_metrics: Dict[str, Any]) -> List[str]:
        """Export performance metrics.
        
        Args:
            performance_metrics: Performance metrics data
            
        Returns:
            List of Prometheus-formatted metric lines
        """
        lines = []
        
        if not isinstance(performance_metrics, dict):
            return lines
        
        for metric_name, data in performance_metrics.items():
            if not isinstance(data, dict):
                continue
            
            # Map performance metrics to Prometheus names
            prometheus_name = None
            help_text = None
            
            if "message_routing_latency" in metric_name:
                prometheus_name = self.metric_names["message_routing_duration"]
                help_text = self.metric_help["message_routing_duration"]
            elif "command_execution_latency" in metric_name:
                prometheus_name = self.metric_names["command_duration"]
                help_text = self.metric_help["command_duration"]
            elif "websocket_connection_time" in metric_name:
                prometheus_name = self.metric_names["websocket_connection_duration"]
                help_text = self.metric_help["websocket_connection_duration"]
            elif "storage_operation_time" in metric_name:
                prometheus_name = self.metric_names["storage_operation_duration"]
                help_text = self.metric_help["storage_operation_duration"]
            
            if prometheus_name and "avg" in data:
                avg_value = data["avg"]
                
                lines.append(f"# HELP {prometheus_name} {help_text}")
                lines.append(f"# TYPE {prometheus_name} gauge")
                lines.append(f"{prometheus_name} {avg_value}")
                lines.append("")
        
        return lines
    
    def _export_raw_metrics(self, raw_metrics: Dict[str, Any]) -> List[str]:
        """Export raw metric values.
        
        Args:
            raw_metrics: Raw metrics data
            
        Returns:
            List of Prometheus-formatted metric lines
        """
        lines = []
        
        if not isinstance(raw_metrics, dict):
            return lines
        
        for metric_name, metric_groups in raw_metrics.items():
            if not isinstance(metric_groups, dict):
                continue
            
            prometheus_name = self.metric_names.get(metric_name, f"arqonbus_{metric_name}")
            
            for metric_type, values in metric_groups.items():
                if not isinstance(values, list):
                    continue
                
                # Add help and type for counter and gauge metrics
                if metric_type in ["counter", "gauge"]:
                    help_text = self.metric_help.get(metric_name, f"ArqonBus {metric_name}")
                    lines.append(f"# HELP {prometheus_name} {help_text}")
                    
                    if metric_type == "counter":
                        lines.append(f"# TYPE {prometheus_name} counter")
                    else:
                        lines.append(f"# TYPE {prometheus_name} gauge")
                
                # Export individual values
                for metric_value in values[-10:]:  # Last 10 values
                    if not isinstance(metric_value, dict):
                        continue
                    
                    value = metric_value.get("value", 0)
                    labels = metric_value.get("labels", {})
                    
                    # Build label string
                    label_strings = []
                    for label_name, label_value in labels.items():
                        label_strings.append(f'{label_name}="{label_value}"')
                    
                    label_str = ""
                    if label_strings:
                        label_str = "{" + ",".join(label_strings) + "}"
                    
                    lines.append(f"{prometheus_name}{label_str} {value}")
                
                if values:
                    lines.append("")
        
        return lines
    
    def export_single_metric(self, metric_name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> str:
        """Export a single metric in Prometheus format.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Optional labels for the metric
            
        Returns:
            Prometheus-formatted metric line
        """
        prometheus_name = self.metric_names.get(metric_name, f"arqonbus_{metric_name}")
        
        # Build label string
        label_strings = []
        if labels:
            for label_name, label_value in labels.items():
                label_strings.append(f'{label_name}="{label_value}"')
        
        label_str = ""
        if label_strings:
            label_str = "{" + ",".join(label_strings) + "}"
        
        return f"{prometheus_name}{label_str} {value}"
    
    def get_metrics_registry(self) -> Dict[str, Any]:
        """Get a registry of available metrics.
        
        Returns:
            Dictionary with metric registry information
        """
        return {
            "metrics": self.metric_names,
            "help_text": self.metric_help,
            "collector_type": type(self.collector).__name__,
            "export_format": "prometheus",
            "export_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def validate_metric_name(self, metric_name: str) -> bool:
        """Validate if a metric name is Prometheus-compatible.
        
        Args:
            metric_name: Metric name to validate
            
        Returns:
            True if metric name is valid for Prometheus
        """
        # Prometheus metric name validation: [a-zA-Z_:][a-zA-Z0-9_:]*
        import re
        
        pattern = r'^[a-zA-Z_:][a-zA-Z0-9_:]*$'
        return bool(re.match(pattern, metric_name))
    
    def sanitize_metric_name(self, metric_name: str) -> str:
        """Sanitize a metric name for Prometheus compatibility.
        
        Args:
            metric_name: Metric name to sanitize
            
        Returns:
            Sanitized metric name
        """
        # Replace invalid characters with underscores
        import re
        
        # Replace spaces and hyphens with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_:]', '_', metric_name)
        
        # Ensure it starts with a valid character
        if sanitized and not re.match(r'^[a-zA-Z_:]', sanitized):
            sanitized = "arqonbus_" + sanitized
        
        return sanitized or "arqonbus_unknown"


# Global exporter instance
_exporter: Optional[PrometheusMetricsExporter] = None


def get_exporter() -> PrometheusMetricsExporter:
    """Get the global Prometheus metrics exporter instance.
    
    Returns:
        PrometheusMetricsExporter instance
    """
    global _exporter
    if _exporter is None:
        _exporter = PrometheusMetricsExporter()
    return _exporter


def export_prometheus_metrics() -> str:
    """Export all metrics in Prometheus format.
    
    Returns:
        Prometheus-formatted metrics string
    """
    return get_exporter().export_metrics()


def export_single_metric(metric_name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> str:
    """Export a single metric in Prometheus format.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        labels: Optional labels for the metric
        
    Returns:
        Prometheus-formatted metric line
    """
    return get_exporter().export_single_metric(metric_name, value, labels)


def get_metrics_registry() -> Dict[str, Any]:
    """Get a registry of available metrics.
    
    Returns:
        Dictionary with metric registry information
    """
    return get_exporter().get_metrics_registry()