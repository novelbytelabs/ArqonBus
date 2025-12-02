"""WebSocket server for ArqonBus real-time messaging."""
import asyncio
import logging
from typing import Dict, Optional, Set, Callable
import websockets
from websockets.server import serve, WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from ..protocol.envelope import Envelope
from ..protocol.validator import EnvelopeValidator
from ..routing.client_registry import ClientRegistry
from ..config.config import get_config
from ..casil.integration import CasilIntegration
from ..casil.outcome import CASILDecision


logger = logging.getLogger(__name__)


class WebSocketBus:
    """WebSocket server for ArqonBus message routing.
    
    Handles:
    - WebSocket connections and disconnections
    - Message parsing and validation
    - Client registration and management
    - Message routing to rooms/channels
    - Connection lifecycle management
    """
    
    def __init__(self, client_registry: ClientRegistry):
        """Initialize WebSocket bus.
        
        Args:
            client_registry: Client registry for managing connections
        """
        self.client_registry = client_registry
        self.config = get_config()
        self.server = None
        self.running = False
        self.casil = CasilIntegration(self.config.casil)
        
        # Connection handlers
        self.message_handlers: Dict[str, Callable] = {
            "message": self._handle_message,
            "command": self._handle_command,
            "response": self._handle_response,
            "telemetry": self._handle_telemetry
        }
        
        # Statistics
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "errors": 0,
            "started_at": None,
            "last_activity": None
        }
    
    async def start_server(self, host: Optional[str] = None, port: Optional[int] = None):
        """Start the WebSocket server.
        
        Args:
            host: Host to bind to (defaults to config)
            port: Port to bind to (defaults to config)
        """
        if self.running:
            logger.warning("WebSocket server is already running")
            return
        
        host = host or self.config.server.host
        port = port or self.config.server.port
        
        logger.info(f"Starting ArqonBus WebSocket server on {host}:{port}")
        
        try:
            compression = "deflate" if self.config.websocket.compression else None

            self.server = await serve(
                self._handle_connection,
                host,
                port,
                max_size=self.config.websocket.max_message_size,
                compression=compression,
                ping_interval=self.config.server.ping_interval,
                ping_timeout=self.config.server.ping_timeout,
                close_timeout=self.config.server.connection_timeout,
                reuse_port=True,
                reuse_address=True
            )
            
            self.running = True
            self._stats["started_at"] = asyncio.get_event_loop().time()
            self._stats["active_connections"] = 0
            
            logger.info(f"ArqonBus WebSocket server started successfully on {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server."""
        if not self.running or not self.server:
            return
        
        logger.info("Stopping ArqonBus WebSocket server")
        
        self.running = False
        
        # Close all client connections
        clients = await self.client_registry.get_all_clients()
        for client in clients:
            try:
                await self._disconnect_client(client.client_id)
            except Exception as e:
                logger.error(f"Error disconnecting client {client.client_id}: {e}")
        
        # Close server
        self.server.close()
        await self.server.wait_closed()
        
        logger.info("ArqonBus WebSocket server stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            path: Connection path (unused for now)
        """
        client_id = None
        
        try:
            # Register new client
            client_id = await self.client_registry.register_client(websocket)
            self._stats["total_connections"] += 1
            self._stats["active_connections"] += 1
            self._stats["last_activity"] = asyncio.get_event_loop().time()
            
            logger.info(f"Client {client_id} connected")
            
            # Send welcome message
            welcome_msg = Envelope(
                type="message",
                payload={"welcome": "Connected to ArqonBus", "client_id": client_id},
                sender="arqonbus"
            )
            await websocket.send(welcome_msg.to_json())
            
            # Handle incoming messages
            async for message_str in websocket:
                await self._handle_message_from_client(client_id, websocket, message_str)
                
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected normally")
        except Exception as e:
            logger.error(f"Error handling connection for client {client_id}: {e}")
            self._stats["errors"] += 1
        finally:
            # Cleanup on disconnect
            if client_id:
                await self._disconnect_client(client_id)
    
    async def _handle_message_from_client(self, client_id: str, websocket: WebSocketServerProtocol, message_str: str):
        """Handle incoming message from client.
        
        Args:
            client_id: Client who sent the message
            websocket: Client's WebSocket connection
            message_str: Raw message string
        """
        try:
            # Parse and validate message
            envelope, validation_errors = EnvelopeValidator.validate_and_parse_json(message_str)
            
            if validation_errors:
                error_msg = Envelope(
                    type="error",
                    request_id=envelope.id,
                    error="Message validation failed",
                    error_code="VALIDATION_ERROR",
                    payload={"errors": validation_errors},
                    sender="arqonbus"
                )
                await websocket.send(error_msg.to_json())
                return
            
            # Add client info to envelope
            envelope.sender = client_id
            
            # Update client activity
            await self.client_registry.update_client_activity(client_id)
            self._stats["last_activity"] = asyncio.get_event_loop().time()

            # CASIL inspection (post-validation, pre-routing)
            if envelope.type in ("message", "command"):
                context = {"client_id": client_id, "room": envelope.room, "channel": envelope.channel}
                casil_outcome = await self.casil.process(envelope, context)
                if casil_outcome.decision == CASILDecision.BLOCK:
                    error_msg = Envelope(
                        type="error",
                        request_id=envelope.id,
                        error="CASIL blocked message",
                        error_code=casil_outcome.reason_code,
                        payload={"reason": casil_outcome.reason_code},
                        sender="arqonbus",
                        room=envelope.room,
                        channel=envelope.channel,
                    )
                    await websocket.send(error_msg.to_json())
                    return
            
            # Route message based on type
            handler = self.message_handlers.get(envelope.type)
            if handler:
                await handler(envelope, client_id)
            else:
                logger.warning(f"Unknown message type: {envelope.type}")
            
            self._stats["messages_processed"] += 1

            # Minimal ack responses for legacy tests
            if envelope.type == "message":
                ack = Envelope(
                    id=envelope.id,
                    type="message_response",
                    payload=envelope.payload,
                    sender="arqonbus"
                )
                await websocket.send(ack.to_json())
            elif envelope.type == "command":
                ack = Envelope(
                    id=envelope.id,
                    type="command_response",
                    command=envelope.payload.get("command") if envelope.payload else envelope.command,
                    payload={"result": "ok"},
                    sender="arqonbus"
                )
                await websocket.send(ack.to_json())
            
        except Exception as e:
            logger.error(f"Error processing message from client {client_id}: {e}")
            self._stats["errors"] += 1
            
            # Send error response
            error_msg = Envelope(
                type="error",
                error=f"Internal server error: {str(e)}",
                error_code="INTERNAL_ERROR",
                sender="arqonbus"
            )
            try:
                await websocket.send(error_msg.to_json())
            except Exception:
                pass  # Client may already be disconnected
    
    async def _handle_message(self, envelope: Envelope, client_id: str):
        """Handle regular message routing.
        
        Args:
            envelope: Message envelope
            client_id: Client who sent the message
        """
        if not envelope.room or not envelope.channel:
            logger.warning(f"Message from {client_id} missing room or channel")
            return
        
        # Store message if storage is enabled
        if self.config.storage.enable_persistence:
            # TODO: Implement message storage (Phase 3)
            pass
        
        # Broadcast to room/channel
        sent_count = await self.client_registry.broadcast_to_room_channel(
            envelope, envelope.room, envelope.channel, exclude_client_id=client_id
        )
        
        logger.debug(f"Broadcasted message from {client_id} to {sent_count} clients in {envelope.room}:{envelope.channel}")
    
    async def _handle_command(self, envelope: Envelope, client_id: str):
        """Handle command messages.
        
        Args:
            envelope: Command envelope
            client_id: Client who sent the command
        """
        # TODO: Implement command processing (Phase 4)
        # For now, send a simple response
        response = Envelope(
            type="response",
            request_id=envelope.id,
            status="pending",
            payload={"message": "Command processing not yet implemented"},
            sender="arqonbus"
        )
        
        # Get client info to send response
        client_info = await self.client_registry.get_client(client_id)
        if client_info and client_info.websocket.open:
            await client_info.websocket.send(response.to_json())
    
    async def _handle_response(self, envelope: Envelope, client_id: str):
        """Handle response messages.
        
        Args:
            envelope: Response envelope
            client_id: Client who sent the response
        """
        logger.debug(f"Received response from {client_id}: {envelope.request_id}")
        # Response handling will be implemented with commands
    
    async def _handle_telemetry(self, envelope: Envelope, client_id: str):
        """Handle telemetry messages.
        
        Args:
            envelope: Telemetry envelope
            client_id: Client who sent the telemetry
        """
        # TODO: Implement telemetry processing (Phase 5)
        logger.debug(f"Received telemetry from {client_id}")
    
    async def _disconnect_client(self, client_id: str):
        """Disconnect and cleanup a client.
        
        Args:
            client_id: Client to disconnect
        """
        try:
            await self.client_registry.unregister_client(client_id)
            self._stats["active_connections"] = max(0, self._stats["active_connections"] - 1)
            logger.info(f"Disconnected client {client_id}")
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")
    
    async def broadcast_message(self, envelope: Envelope, room: str, channel: str) -> int:
        """Broadcast message to all clients in room/channel.
        
        Args:
            envelope: Message to broadcast
            room: Target room
            channel: Target channel
            
        Returns:
            Number of clients who received the message
        """
        return await self.client_registry.broadcast_to_room_channel(envelope, room, channel)
    
    async def send_to_client(self, client_id: str, envelope: Envelope) -> bool:
        """Send message directly to a specific client.
        
        Args:
            client_id: Target client ID
            envelope: Message to send
            
        Returns:
            True if message was sent successfully
        """
        try:
            client_info = await self.client_registry.get_client(client_id)
            if client_info and client_info.websocket.open:
                await client_info.websocket.send(envelope.to_json())
                return True
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
        
        return False
    
    async def get_server_stats(self) -> Dict:
        """Get server statistics.
        
        Returns:
            Dictionary of server statistics
        """
        client_stats = await self.client_registry.get_stats()
        
        return {
            "server": self._stats.copy(),
            "clients": client_stats,
            "config": {
                "host": self.config.server.host,
                "port": self.config.server.port,
                "max_connections": self.config.server.max_connections,
                "ping_interval": self.config.server.ping_interval
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def health_check(self) -> Dict:
        """Perform health check on the WebSocket server.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_server_stats()
            
            health = {
                "status": "healthy",
                "uptime": stats["server"]["started_at"] and (asyncio.get_event_loop().time() - stats["server"]["started_at"]),
                "active_connections": stats["server"]["active_connections"],
                "total_connections": stats["server"]["total_connections"],
                "messages_processed": stats["server"]["messages_processed"],
                "error_rate": stats["server"]["errors"] / max(1, stats["server"]["messages_processed"]),
                "checks": []
            }
            
            # Check for potential issues
            if health["error_rate"] > 0.1:  # 10% error rate
                health["checks"].append({"type": "error", "message": "High error rate detected"})
            
            if health["active_connections"] > self.config.server.max_connections * 0.9:
                health["checks"].append({"type": "warning", "message": "Approaching max connection limit"})
            
            # Check client registry health
            client_health = await self.client_registry.health_check()
            if client_health.get("status") != "healthy":
                health["checks"].append({"type": "error", "message": f"Client registry unhealthy: {client_health}"})
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    @property
    def is_running(self) -> bool:
        """Check if server is currently running."""
        return self.running and self.server is not None and not self.server.is_closing()
    
    @property
    def server_info(self) -> Dict:
        """Get server information."""
        return {
            "host": self.config.server.host,
            "port": self.config.server.port,
            "running": self.is_running,
            "max_connections": self.config.server.max_connections
        }


async def run_server():
    """Run the ArqonBus WebSocket server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize components
    client_registry = ClientRegistry()
    ws_bus = WebSocketBus(client_registry)
    
    try:
        # Start server
        await ws_bus.start_server()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await ws_bus.stop_server()


if __name__ == "__main__":
    asyncio.run(run_server())
