"""Telemetry WebSocket server for ArqonBus.

This module provides a WebSocket server for broadcasting telemetry events
to connected monitoring clients.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
import uuid
import time

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False

from ..utils.logging import get_logger
from .handlers import TelemetryEventHandler

logger = get_logger(__name__)


class TelemetryServer:
    """WebSocket server for broadcasting telemetry events.
    
    Manages connected telemetry clients and broadcasts system events
    such as client connections, message routing, and system status.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize telemetry server.
        
        Args:
            config: Configuration dictionary with telemetry settings
        """
        self.config = config
        self.enabled = config.get("telemetry_enabled", True)
        self.host = config.get("telemetry_host", "localhost")
        self.port = config.get("telemetry_port", 8081)
        self.telemetry_rooms = config.get("telemetry_rooms", ["arqonbus:telemetry"])
        self.event_buffer_size = config.get("event_buffer_size", 1000)
        self.batch_size = config.get("batch_size", 10)
        self.flush_interval = config.get("flush_interval", 5.0)
        self.filtered_events = config.get("filtered_events", [])
        
        # WebSocket server
        self.server = None
        self.is_running = False
        
        # Connected telemetry clients
        self._telemetry_clients: Set = set()
        self._client_lock = asyncio.Lock()
        
        # Event buffering and batching
        self._event_buffer: List[Dict[str, Any]] = []
        self._batch_lock = asyncio.Lock()
        self._last_flush = time.time()
        
        # Event processing
        self.event_handler = TelemetryEventHandler()
        
        # Performance metrics
        self._metrics = {
            "events_broadcast_total": 0,
            "events_buffered": 0,
            "active_connections": 0,
            "average_broadcast_time_ms": 0.0,
            "total_clients_connected": 0,
            "failed_broadcasts": 0
        }
        
        # WebSocket connection management
        self._max_connections = config.get("max_telemetry_connections", 100)
        self._connection_timeout = config.get("connection_timeout", 30)
    
    async def start(self) -> bool:
        """Start the telemetry WebSocket server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if not self.enabled:
            logger.info("Telemetry server is disabled")
            return False
        
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("WebSockets not available, telemetry server disabled")
            return False
        
        try:
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client_connection,
                self.host,
                self.port
            )
            
            self.is_running = True
            logger.info(f"Telemetry server started on {self.host}:{self.port}")
            
            # Start background tasks
            asyncio.create_task(self._periodic_flush())
            asyncio.create_task(self._health_monitor())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start telemetry server: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the telemetry WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("Telemetry server stopped")
    
    async def _handle_client_connection(self, websocket, path):
        """Handle new WebSocket client connection.
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        try:
            # Check connection limit
            async with self._client_lock:
                if len(self._telemetry_clients) >= self._max_connections:
                    logger.warning(f"Telemetry connection limit reached ({self._max_connections})")
                    await websocket.close(code=1013, reason="Connection limit reached")
                    return
                
                self._telemetry_clients.add(websocket)
                self._metrics["active_connections"] += 1
                self._metrics["total_clients_connected"] += 1
            
            logger.info(f"Telemetry client connected: {websocket.remote_address}")
            
            # Send welcome message
            welcome_event = {
                "event_type": "telemetry_connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Connected to ArqonBus telemetry",
                "server_config": {
                    "host": self.host,
                    "port": self.port,
                    "filtered_events": self.filtered_events
                }
            }
            await websocket.send(json.dumps(welcome_event))
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from telemetry client: {message}")
                except Exception as e:
                    logger.error(f"Error handling telemetry client message: {e}")
            
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error in telemetry client connection: {e}")
        finally:
            # Clean up client connection
            async with self._client_lock:
                self._telemetry_clients.discard(websocket)
                self._metrics["active_connections"] = max(0, self._metrics["active_connections"] - 1)
            
            logger.info(f"Telemetry client disconnected: {websocket.remote_address}")
    
    async def _handle_client_message(self, websocket, data: Dict[str, Any]):
        """Handle message from telemetry client.
        
        Args:
            websocket: WebSocket connection
            data: Message data
        """
        message_type = data.get("type")
        
        if message_type == "ping":
            await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))
        elif message_type == "subscribe":
            # Handle client subscription to specific event types
            events = data.get("events", [])
            logger.info(f"Telemetry client subscribed to events: {events}")
        elif message_type == "unsubscribe":
            # Handle client unsubscription
            events = data.get("events", [])
            logger.info(f"Telemetry client unsubscribed from events: {events}")
        else:
            logger.warning(f"Unknown telemetry message type: {message_type}")
    
    async def broadcast_event(self, event: Dict[str, Any]) -> str:
        """Broadcast telemetry event to connected clients.
        
        Args:
            event: Event data to broadcast
            
        Returns:
            Broadcast result status
        """
        if not self.is_running:
            return "server_not_running"
        
        # Validate event
        event = await self.event_handler.process_event(event)
        
        # Check if event should be filtered
        if self.filtered_events and event.get("event_type") not in self.filtered_events:
            return "filtered"
        
        # Add to buffer
        async with self._batch_lock:
            self._event_buffer.append(event)
            self._metrics["events_buffered"] += 1
            
            # Check if batch should be flushed
            if len(self._event_buffer) >= self.batch_size:
                await self._flush_batch()
        
        return "buffered"
    
    async def _flush_batch(self):
        """Flush buffered events to connected clients."""
        if not self._event_buffer:
            return
        
        events_to_send = []
        
        async with self._batch_lock:
            events_to_send = self._event_buffer.copy()
            self._event_buffer.clear()
            self._metrics["events_buffered"] = 0
        
        if not events_to_send:
            return
        
        # Broadcast to all connected clients
        clients_to_remove = []
        
        for event in events_to_send:
            event_json = json.dumps(event)
            
            async with self._client_lock:
                for client in self._telemetry_clients.copy():
                    try:
                        start_time = time.time()
                        await client.send(event_json)
                        broadcast_time = (time.time() - start_time) * 1000
                        
                        # Update average broadcast time
                        self._metrics["average_broadcast_time_ms"] = (
                            (self._metrics["average_broadcast_time_ms"] * self._metrics["events_broadcast_total"] + broadcast_time) /
                            (self._metrics["events_broadcast_total"] + 1)
                        )
                        
                        self._metrics["events_broadcast_total"] += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to broadcast to telemetry client: {e}")
                        clients_to_remove.append(client)
                        self._metrics["failed_broadcasts"] += 1
        
        # Remove failed clients
        async with self._client_lock:
            for client in clients_to_remove:
                self._telemetry_clients.discard(client)
                self._metrics["active_connections"] -= 1
    
    async def _periodic_flush(self):
        """Periodic task to flush event buffer."""
        while self.is_running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_batch()
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _health_monitor(self):
        """Monitor telemetry server health."""
        while self.is_running:
            try:
                # Check server health
                health_data = await self.get_performance_metrics()
                
                # Log health status periodically
                if self._metrics["events_broadcast_total"] % 100 == 0:
                    logger.info(f"Telemetry health: {health_data['active_connections']} clients, "
                               f"{health_data['events_broadcast_total']} events broadcast")
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get telemetry server performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "events_broadcast_total": self._metrics["events_broadcast_total"],
            "events_buffered": self._metrics["events_buffered"],
            "active_connections": self._metrics["active_connections"],
            "average_broadcast_time_ms": round(self._metrics["average_broadcast_time_ms"], 2),
            "total_clients_connected": self._metrics["total_clients_connected"],
            "failed_broadcasts": self._metrics["failed_broadcasts"],
            "buffer_size": len(self._event_buffer),
            "server_running": self.is_running,
            "uptime_seconds": time.time() - (getattr(self, '_start_time', time.time()))
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get telemetry server health status.
        
        Returns:
            Dictionary with health status
        """
        return {
            "status": "healthy" if self.is_running else "stopped",
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "active_connections": self._metrics["active_connections"],
            "events_broadcast_total": self._metrics["events_broadcast_total"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def emit_client_event(self, client_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit client-related telemetry event.
        
        Args:
            client_id: Client identifier
            event_type: Type of client event
            metadata: Additional event metadata
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_id": client_id,
            "metadata": metadata or {}
        }
        await self.broadcast_event(event)
    
    async def emit_message_event(self, message_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit message-related telemetry event.
        
        Args:
            message_id: Message identifier
            event_type: Type of message event
            metadata: Additional event metadata
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": message_id,
            "metadata": metadata or {}
        }
        await self.broadcast_event(event)
    
    async def emit_system_event(self, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit system-related telemetry event.
        
        Args:
            event_type: Type of system event
            metadata: Additional event metadata
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": "arqonbus",
            "metadata": metadata or {}
        }
        await self.broadcast_event(event)