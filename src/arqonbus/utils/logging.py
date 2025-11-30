"""Structured logging utilities for ArqonBus."""
import logging
import logging.handlers
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
import traceback


class StructuredFormatter(logging.Formatter):
    """Structured JSON logging formatter for ArqonBus."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.
        
        Args:
            record: LogRecord to format
            
        Returns:
            JSON string representation of log entry
        """
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread_id": record.thread,
            "process_id": record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName', 
                'processName', 'process', 'getMessage', 'exc_info', 
                'exc_text', 'stack_info'
            }:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ArqonBusFormatter(logging.Formatter):
    """Human-readable formatter with ArqonBus-specific formatting."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability.
        
        Args:
            record: LogRecord to format
            
        Returns:
            Formatted log message string
        """
        # Add ArqonBus-specific context
        timestamp = datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Add component context if available
        component = getattr(record, 'component', 'arqonbus')
        
        # Format message
        formatted = f"[{timestamp}] [{component}] {record.levelname:8} {record.name}: {record.getMessage()}"
        
        # Add extra fields if present
        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName', 
                'processName', 'process', 'getMessage', 'exc_info', 
                'exc_text', 'stack_info', 'component'
            }:
                extra_fields.append(f"{key}={value}")
        
        if extra_fields:
            formatted += f" | {' '.join(extra_fields)}"
        
        # Add exception if present
        if record.exc_info:
            formatted += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
        
        return formatted


class LogContext:
    """Context manager for adding structured data to log entries."""
    
    def __init__(self, logger: logging.Logger, **context):
        """Initialize log context.
        
        Args:
            logger: Logger to add context to
            **context: Context data to add to log entries
        """
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and setup filter."""
        class ContextFilter(logging.Filter):
            def __init__(self, context):
                self.context = context
            
            def filter(self, record):
                for key, value in self.context.items():
                    setattr(record, key, value)
                return True
        
        self.old_factory = logging.getLogRecordFactory()
        self.context_filter = ContextFilter(self.context)
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            self.context_filter.filter(record)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original factory."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def setup_logging(
    level: str = "INFO",
    format_type: str = "structured",
    output: str = "stdout",
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup ArqonBus logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Format type ('structured', 'human')
        output: Output destination ('stdout', 'stderr', 'file')
        max_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger("arqonbus")
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    if format_type == "structured":
        formatter = StructuredFormatter()
    else:
        formatter = ArqonBusFormatter()
    
    # Setup handler
    if output in ["stdout", "stderr"]:
        stream = sys.stdout if output == "stdout" else sys.stderr
        handler = logging.StreamHandler(stream)
    else:
        # File output
        handler = logging.handlers.RotatingFileHandler(
            "arqonbus.log",
            maxBytes=max_size,
            backupCount=backup_count
        )
    
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)
    root_logger.addHandler(handler)
    
    # Setup third-party loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with ArqonBus naming convention.
    
    Args:
        name: Logger name (component name)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"arqonbus.{name}")
    
    # Add component attribute for formatting
    class ComponentFilter(logging.Filter):
        def filter(self, record):
            record.component = name
            return True
    
    logger.addFilter(ComponentFilter())
    return logger


def log_message_routing(
    logger: logging.Logger,
    message_id: str,
    sender_id: str,
    destination: str,
    message_type: str,
    recipient_count: int
):
    """Log message routing event with structured data.
    
    Args:
        logger: Logger instance
        message_id: Message identifier
        sender_id: Sender client ID
        destination: Routing destination (room:channel or global)
        message_type: Type of message
        recipient_count: Number of recipients
    """
    logger.info(
        "Message routed",
        extra={
            "event_type": "message_routing",
            "message_id": message_id,
            "sender_id": sender_id,
            "destination": destination,
            "message_type": message_type,
            "recipient_count": recipient_count
        }
    )


def log_client_event(
    logger: logging.Logger,
    event: str,
    client_id: str,
    **context
):
    """Log client-related event.
    
    Args:
        logger: Logger instance
        event: Event type (connected, disconnected, joined, left)
        client_id: Client identifier
        **context: Additional context data
    """
    logger.info(
        f"Client {event}",
        extra={
            "event_type": "client_event",
            "client_event": event,
            "client_id": client_id,
            **context
        }
    )


def log_room_event(
    logger: logging.Logger,
    event: str,
    room_id: str,
    channel_id: Optional[str] = None,
    **context
):
    """Log room-related event.
    
    Args:
        logger: Logger instance
        event: Event type (created, deleted, joined, left)
        room_id: Room identifier
        channel_id: Optional channel identifier
        **context: Additional context data
    """
    logger.info(
        f"Room {event}",
        extra={
            "event_type": "room_event",
            "room_event": event,
            "room_id": room_id,
            "channel_id": channel_id,
            **context
        }
    )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any],
    level: str = "error"
):
    """Log error with structured context.
    
    Args:
        logger: Logger instance
        error: Exception to log
        context: Error context data
        level: Log level ('error', 'warning', 'info')
    """
    log_func = getattr(logger, level.lower(), logger.error)
    
    log_func(
        f"Error: {error}",
        extra={
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        },
        exc_info=True
    )


# Type hint for Logger (to avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from logging import Logger


def create_performance_logger(name: str) -> logging.Logger:
    """Create a logger specifically for performance metrics.
    
    Args:
        name: Component name for the performance logger
        
    Returns:
        Performance logger instance
    """
    logger = get_logger(f"performance.{name}")
    return logger


def log_metric(
    logger: logging.Logger,
    metric_name: str,
    value: float,
    unit: str = "count",
    tags: Optional[Dict[str, str]] = None
):
    """Log performance metric.
    
    Args:
        logger: Performance logger instance
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Additional tags for the metric
    """
    logger.info(
        f"Metric: {metric_name}",
        extra={
            "event_type": "metric",
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "metric_tags": tags or {}
        }
    )


def log_business_event(
    logger: logging.Logger,
    event_name: str,
    properties: Dict[str, Any]
):
    """Log business-level event.
    
    Args:
        logger: Logger instance
        event_name: Name of the business event
        properties: Event properties
    """
    logger.info(
        f"Business event: {event_name}",
        extra={
            "event_type": "business_event",
            "business_event": event_name,
            "properties": properties
        }
    )