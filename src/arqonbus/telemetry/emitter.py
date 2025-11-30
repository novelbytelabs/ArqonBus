"""Telemetry event emitter for ArqonBus.

This module provides a unified interface for emitting telemetry events
from throughout the ArqonBus system.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Callable
import time
import uuid

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TelemetryEmitter:
    """Unified telemetry event emitter for ArqonBus.
    
    Provides a centralized interface for emitting system events,
    business metrics, and operational telemetry throughout the application.
    """
    
    def __init__(self, telemetry_server=None, config: Optional[Dict[str, Any]] = None):
        """Initialize telemetry emitter.
        
        Args:
            telemetry_server: Telemetry server to emit events to
            config: Configuration dictionary
        """
        self.telemetry_server = telemetry_server
        self.config = config or {}
        self.enabled = self.config.get("telemetry_enabled", True)
        self.event_buffer = []
        self.buffer_size = self.config.get("event_buffer_size", 100)
        self.flush_interval = self.config.get("flush_interval", 5.0)
        self.batch_size = self.config.get("batch_size", 10)
        
        # Event emitters and subscribers
        self._event_emitters: Dict[str, Callable] = {}
        self._event_subscribers: List[Callable] = []
        
        # Statistics
        self._stats = {
            "events_emitted": 0,
            "events_buffered": 0,
            "events_dropped": 0,
            "emit_errors": 0,
            "last_emit_time": None
        }
        
        # Background tasks
        self._flush_task = None
        self._is_running = False
        
        # Common event types
        self.EVENT_TYPES = {
            # Client events
            "CLIENT_CONNECTED": "client_connected",
            "CLIENT_DISCONNECTED": "client_disconnected",
            "CLIENT_AUTHENTICATED": "client_authenticated",
            "CLIENT_AUTHORIZED": "client_authorized",
            "CLIENT_RATE_LIMITED": "client_rate_limited",
            
            # Message events
            "MESSAGE_SENT": "message_sent",
            "MESSAGE_RECEIVED": "message_received",
            "MESSAGE_ROUTED": "message_routed",
            "MESSAGE_FAILED": "message_failed",
            "MESSAGE_HISTORY_RETRIEVED": "message_history_retrieved",
            
            # Room and channel events
            "ROOM_CREATED": "room_created",
            "ROOM_DELETED": "room_deleted",
            "CHANNEL_CREATED": "channel_created",
            "CHANNEL_DELETED": "channel_deleted",
            "CLIENT_JOINED_ROOM": "client_joined_room",
            "CLIENT_LEFT_ROOM": "client_left_room",
            "CLIENT_JOINED_CHANNEL": "client_joined_channel",
            "CLIENT_LEFT_CHANNEL": "client_left_channel",
            
            # Command events
            "COMMAND_EXECUTED": "command_executed",
            "COMMAND_SUCCEEDED": "command_succeeded",
            "COMMAND_FAILED": "command_failed",
            "COMMAND_RATE_LIMITED": "command_rate_limited",
            
            # System events
            "SYSTEM_STARTED": "system_started",
            "SYSTEM_STOPPED": "system_stopped",
            "SYSTEM_ERROR": "system_error",
            "SYSTEM_WARNING": "system_warning",
            "SYSTEM_INFO": "system_info",
            
            # Storage events
            "STORAGE_OPERATION": "storage_operation",
            "STORAGE_ERROR": "storage_error",
            "STORAGE_BACKUP": "storage_backup",
            "STORAGE_RESTORE": "storage_restore",
            
            # Security events
            "SECURITY_VIOLATION": "security_violation",
            "AUTHENTICATION_FAILED": "authentication_failed",
            "AUTHORIZATION_DENIED": "authorization_denied",
            "SUSPICIOUS_ACTIVITY": "suspicious_activity"
        }
    
    async def start(self):
        """Start the telemetry emitter."""
        if not self.enabled:
            logger.info("Telemetry emitter is disabled")
            return
        
        self._is_running = True
        
        # Start background tasks
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
        logger.info("Telemetry emitter started")
    
    async def stop(self):
        """Stop the telemetry emitter."""
        self._is_running = False
        
        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self.flush_events()
        
        logger.info("Telemetry emitter stopped")
    
    async def emit_event(
        self,
        event_type: str,
        client_id: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Emit a telemetry event.
        
        Args:
            event_type: Type of event to emit
            client_id: Client identifier (if applicable)
            message_id: Message identifier (if applicable)
            metadata: Additional event metadata
            severity: Event severity (debug, info, warning, error, critical)
            timestamp: Event timestamp (defaults to current time)
            
        Returns:
            True if event was emitted successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Create event
            event = {
                "event_type": event_type,
                "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
                "client_id": client_id,
                "message_id": message_id,
                "metadata": metadata or {},
                "severity": severity,
                "source": "arqonbus",
                "event_id": str(uuid.uuid4())
            }
            
            # Add to buffer
            self.event_buffer.append(event)
            self._stats["events_emitted"] += 1
            self._stats["events_buffered"] += 1
            self._stats["last_emit_time"] = time.time()
            
            # Check if buffer should be flushed
            if len(self.event_buffer) >= self.buffer_size:
                await self.flush_events()
            
            # Notify subscribers
            await self._notify_subscribers(event)
            
            # Check if batch should be flushed
            if len(self.event_buffer) >= self.batch_size:
                asyncio.create_task(self.flush_events())
            
            return True
            
        except Exception as e:
            self._stats["emit_errors"] += 1
            logger.error(f"Error emitting telemetry event: {e}")
            return False
    
    async def flush_events(self):
        """Flush buffered events to telemetry server."""
        if not self.event_buffer or not self.telemetry_server:
            return
        
        events_to_send = self.event_buffer.copy()
        self.event_buffer.clear()
        self._stats["events_buffered"] = 0
        
        success_count = 0
        
        for event in events_to_send:
            try:
                result = await self.telemetry_server.broadcast_event(event)
                if result in ["buffered", "broadcast_success"]:
                    success_count += 1
                else:
                    self._stats["events_dropped"] += 1
            except Exception as e:
                self._stats["events_dropped"] += 1
                logger.warning(f"Failed to send event to telemetry server: {e}")
        
        if success_count > 0:
            logger.debug(f"Flushed {success_count} events to telemetry server")
    
    async def _periodic_flush(self):
        """Periodic task to flush event buffer."""
        while self._is_running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _notify_subscribers(self, event: Dict[str, Any]):
        """Notify event subscribers.
        
        Args:
            event: Event to notify about
        """
        for subscriber in self._event_subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                logger.warning(f"Error notifying event subscriber: {e}")
    
    # Client event methods
    async def emit_client_connected(self, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit client connected event.
        
        Args:
            client_id: Client identifier
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["CLIENT_CONNECTED"],
            client_id=client_id,
            metadata=metadata
        )
    
    async def emit_client_disconnected(self, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit client disconnected event.
        
        Args:
            client_id: Client identifier
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["CLIENT_DISCONNECTED"],
            client_id=client_id,
            metadata=metadata
        )
    
    async def emit_client_authenticated(self, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit client authenticated event.
        
        Args:
            client_id: Client identifier
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["CLIENT_AUTHENTICATED"],
            client_id=client_id,
            metadata=metadata
        )
    
    # Message event methods
    async def emit_message_sent(self, message_id: str, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit message sent event.
        
        Args:
            message_id: Message identifier
            client_id: Sender client identifier
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["MESSAGE_SENT"],
            client_id=client_id,
            message_id=message_id,
            metadata=metadata
        )
    
    async def emit_message_routed(self, message_id: str, route_info: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Emit message routed event.
        
        Args:
            message_id: Message identifier
            route_info: Routing information
            metadata: Additional metadata
        """
        event_metadata = {"route_info": route_info}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["MESSAGE_ROUTED"],
            message_id=message_id,
            metadata=event_metadata
        )
    
    async def emit_message_failed(self, message_id: str, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit message failed event.
        
        Args:
            message_id: Message identifier
            error: Error message
            metadata: Additional metadata
        """
        event_metadata = {"error": error}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["MESSAGE_FAILED"],
            message_id=message_id,
            metadata=event_metadata,
            severity="warning"
        )
    
    # Room and channel event methods
    async def emit_room_created(self, room_id: str, creator_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit room created event.
        
        Args:
            room_id: Room identifier
            creator_id: Creator client identifier
            metadata: Additional metadata
        """
        event_metadata = {"room_id": room_id}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["ROOM_CREATED"],
            client_id=creator_id,
            metadata=event_metadata
        )
    
    async def emit_channel_created(self, channel_id: str, creator_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit channel created event.
        
        Args:
            channel_id: Channel identifier
            creator_id: Creator client identifier
            metadata: Additional metadata
        """
        event_metadata = {"channel_id": channel_id}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["CHANNEL_CREATED"],
            client_id=creator_id,
            metadata=event_metadata
        )
    
    async def emit_client_joined_room(self, client_id: str, room_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit client joined room event.
        
        Args:
            client_id: Client identifier
            room_id: Room identifier
            metadata: Additional metadata
        """
        event_metadata = {"room_id": room_id}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["CLIENT_JOINED_ROOM"],
            client_id=client_id,
            metadata=event_metadata
        )
    
    # Command event methods
    async def emit_command_executed(self, command_name: str, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit command executed event.
        
        Args:
            command_name: Name of executed command
            client_id: Client identifier
            metadata: Additional metadata
        """
        event_metadata = {"command_name": command_name}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["COMMAND_EXECUTED"],
            client_id=client_id,
            metadata=event_metadata
        )
    
    async def emit_command_succeeded(self, command_name: str, client_id: str, execution_time_ms: float, metadata: Optional[Dict[str, Any]] = None):
        """Emit command succeeded event.
        
        Args:
            command_name: Name of executed command
            client_id: Client identifier
            execution_time_ms: Command execution time in milliseconds
            metadata: Additional metadata
        """
        event_metadata = {
            "command_name": command_name,
            "execution_time_ms": execution_time_ms,
            "success": True
        }
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["COMMAND_SUCCEEDED"],
            client_id=client_id,
            metadata=event_metadata
        )
    
    async def emit_command_failed(self, command_name: str, client_id: str, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit command failed event.
        
        Args:
            command_name: Name of failed command
            client_id: Client identifier
            error: Error message
            metadata: Additional metadata
        """
        event_metadata = {
            "command_name": command_name,
            "error": error,
            "success": False
        }
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["COMMAND_FAILED"],
            client_id=client_id,
            metadata=event_metadata,
            severity="warning"
        )
    
    # System event methods
    async def emit_system_started(self, metadata: Optional[Dict[str, Any]] = None):
        """Emit system started event.
        
        Args:
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["SYSTEM_STARTED"],
            metadata=metadata
        )
    
    async def emit_system_stopped(self, metadata: Optional[Dict[str, Any]] = None):
        """Emit system stopped event.
        
        Args:
            metadata: Additional metadata
        """
        return await self.emit_event(
            event_type=self.EVENT_TYPES["SYSTEM_STOPPED"],
            metadata=metadata
        )
    
    async def emit_system_error(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit system error event.
        
        Args:
            error: Error message
            metadata: Additional metadata
        """
        event_metadata = {"error": error}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["SYSTEM_ERROR"],
            metadata=event_metadata,
            severity="error"
        )
    
    async def emit_system_warning(self, warning: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit system warning event.
        
        Args:
            warning: Warning message
            metadata: Additional metadata
        """
        event_metadata = {"warning": warning}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["SYSTEM_WARNING"],
            metadata=event_metadata,
            severity="warning"
        )
    
    # Security event methods
    async def emit_security_violation(self, violation_type: str, client_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Emit security violation event.
        
        Args:
            violation_type: Type of security violation
            client_id: Client identifier (if applicable)
            metadata: Additional metadata
        """
        event_metadata = {"violation_type": violation_type}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["SECURITY_VIOLATION"],
            client_id=client_id,
            metadata=event_metadata,
            severity="warning"
        )
    
    async def emit_authentication_failed(self, client_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit authentication failed event.
        
        Args:
            client_id: Client identifier
            reason: Failure reason
            metadata: Additional metadata
        """
        event_metadata = {"reason": reason}
        if metadata:
            event_metadata.update(metadata)
        
        return await self.emit_event(
            event_type=self.EVENT_TYPES["AUTHENTICATION_FAILED"],
            client_id=client_id,
            metadata=event_metadata,
            severity="warning"
        )
    
    # Subscription methods
    def subscribe(self, subscriber: Callable):
        """Subscribe to telemetry events.
        
        Args:
            subscriber: Callable that will receive events
        """
        self._event_subscribers.append(subscriber)
    
    def unsubscribe(self, subscriber: Callable):
        """Unsubscribe from telemetry events.
        
        Args:
            subscriber: Subscriber to remove
        """
        if subscriber in self._event_subscribers:
            self._event_subscribers.remove(subscriber)
    
    def register_emitter(self, name: str, emitter_func: Callable):
        """Register a custom event emitter.
        
        Args:
            name: Name of the emitter
            emitter_func: Emitter function
        """
        self._event_emitters[name] = emitter_func
    
    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry emitter statistics.
        
        Returns:
            Dictionary with emitter statistics
        """
        return {
            "enabled": self.enabled,
            "buffer_size": len(self.event_buffer),
            "buffer_capacity": self.buffer_size,
            "stats": self._stats.copy(),
            "subscribers": len(self._event_subscribers),
            "custom_emitters": len(self._event_emitters)
        }


# Global emitter instance
_emitter: Optional[TelemetryEmitter] = None


def get_emitter() -> Optional[TelemetryEmitter]:
    """Get the global telemetry emitter instance.
    
    Returns:
        TelemetryEmitter instance or None if not configured
    """
    return _emitter


def set_emitter(emitter: TelemetryEmitter):
    """Set the global telemetry emitter instance.
    
    Args:
        emitter: TelemetryEmitter instance to set
    """
    global _emitter
    _emitter = emitter