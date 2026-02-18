"""WebSocket server for ArqonBus real-time messaging."""
import asyncio
import logging
from typing import Dict, Optional, Set, Callable, Any
from websockets import serve
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
    
    def __init__(self, client_registry: ClientRegistry, routing_coordinator: Optional[Any] = None, storage: Optional[Any] = None, config: Optional[Any] = None):
        """Initialize WebSocket bus.
        
        Args:
            client_registry: Client registry for managing connections
            routing_coordinator: Optional routing coordinator for operator management
            storage: Optional MessageStorage backend
            config: Optional configuration object
        """
        self.client_registry = client_registry
        self.routing_coordinator = routing_coordinator
        self.storage = storage
        self.config = config or get_config()
        self.server = None
        self.running = False
        self._server_task = None
        self.casil = CasilIntegration(self.config.casil)
        
        # Connection handlers
        self.message_handlers: Dict[str, Callable] = {
            "message": self._handle_message,
            "command": self._handle_command,
            "response": self._handle_response,
            "telemetry": self._handle_telemetry,
            "operator.join": self._handle_operator_join
        }
        
        # Task delivery loops {client_id: asyncio.Task}
        self._operator_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "events_emitted": 0,
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
        port = port or self.config.websocket.port
        
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
            
            # Connect storage backend
            if self.storage:
                if hasattr(self.storage, "connect"):
                    await self.storage.connect()

                # Verify storage connection
                if not await self.storage.health_check():
                    logger.error("Storage health check failed. Server will not start.")
                    await self.stop_server()
                    raise RuntimeError("Storage health check failed")
            else:
                 logger.warning("Starting WebSocket server without storage backend.")
            
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
    
    async def _handle_connection(self, websocket: Any):
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
            # Track connection event for telemetry-style stats
            self._stats["events_emitted"] += 1
            
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
    
    async def _handle_message_from_client(self, client_id: str, websocket: Any, message_str: str):
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

            # Count messages as soon as they're accepted for processing
            self._stats["messages_processed"] += 1
            if envelope.type == "command":
                self._stats["events_emitted"] += 1

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
            if self.storage:
                try:
                    result = await self.storage.store_message(envelope)
                    if not result.success:
                        logger.warning(
                            "Failed to persist message %s from %s: %s",
                            envelope.id,
                            client_id,
                            result.error,
                        )
                except Exception as e:
                    logger.error("Message persistence error for %s: %s", envelope.id, e)
        
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
        if envelope.command == "truth.verify":
            # Bridge to distributed task queue (Phase 2 completion)
            if self.routing_coordinator and self.routing_coordinator.operator_registry:
                storage = self.routing_coordinator.operator_registry.storage
                if storage:
                    # Enqueue to the truth group stream
                    # Enqueue to the truth group stream or channel
                    group = getattr(self.config.casil, "truth_worker_group", "truth_workers")
                    stream = f"arqonbus:group:{group}"
                    
                    # Store data from args or payload
                    job_data = envelope.args or envelope.payload
                    
                    # We use the generic storage.backend.redis_client if possible, 
                    # or just use MessageStorage.store_message with a custom stream name
                    # But store_message uses room/channel. We want a custom stream.
                    if hasattr(storage.backend, "redis_client") and storage.backend.redis_client:
                        # Serialize envelope to dict for stream
                        # Actually we just want the payload/args for the worker
                        await storage.backend.redis_client.xadd(stream, job_data, maxlen=10000)
                        logger.info(f"Routed command {envelope.command} from {client_id} to stream {stream}")
                        
                        # Send ACK to client
                        ack = Envelope(
                            type="response",
                            request_id=envelope.id,
                            status="success",
                            payload={"message": "Task enqueued"},
                            sender="arqonbus"
                        )
                        await self.send_to_client(client_id, ack)
                        return

        # Fallback/Default implementation
        response = Envelope(
            type="message",
            request_id=envelope.id,
            status="pending",
            payload={"message": f"Command {envelope.command} processing not fully implemented"},
            sender="arqonbus"
        )
        await self.send_to_client(client_id, response)
    
    async def _handle_response(self, envelope: Envelope, client_id: str):
        """Handle response messages.
        
        Args:
            envelope: Response envelope
            client_id: Client who sent the response
        """
        logger.debug(f"Received response from {client_id}: {envelope.request_id}")
        
        # Forward to ResultCollector for RSI competing tasks
        if self.routing_coordinator and hasattr(self.routing_coordinator, "collector"):
            if envelope.request_id:
                await self.routing_coordinator.collector.add_result(envelope.request_id, envelope)
        
        # Response handling will be implemented with commands
    
    async def _handle_telemetry(self, envelope: Envelope, client_id: str):
        """Handle telemetry messages.
        
        Args:
            envelope: Telemetry envelope
            client_id: Client who sent the telemetry
        """
        self._stats["events_emitted"] += 1

        # Persist telemetry when storage is enabled.
        if self.config.storage.enable_persistence and self.storage:
            try:
                await self.storage.store_message(
                    envelope,
                    room=envelope.room or "integriguard",
                    channel=envelope.channel or "telemetry-stream",
                )
            except Exception as e:
                logger.error("Telemetry persistence error for %s: %s", envelope.id, e)

        # Broadcast telemetry only when routing hints are present.
        if envelope.room and envelope.channel:
            await self.client_registry.broadcast_to_room_channel(
                envelope,
                envelope.room,
                envelope.channel,
                exclude_client_id=client_id,
            )
        logger.debug(f"Processed telemetry from {client_id}")

    async def _handle_operator_join(self, envelope: Envelope, client_id: str):
        """Handle operator registration for a work group."""
        if not self.routing_coordinator or not self.routing_coordinator.operator_registry:
            logger.error("Operator registry not available")
            return

        payload = envelope.payload or {}
        group = payload.get("group")
        if not group:
            logger.warning(f"Operator {client_id} tried to join without group")
            return
        

        auth_token = payload.get("auth_token", "")
        registered = await self.routing_coordinator.operator_registry.register_operator(
            client_id, group, auth_token=auth_token
        )
        if not registered:
            response = Envelope(
                type="error",
                request_id=envelope.id,
                error="Operator registration denied",
                error_code="OPERATOR_AUTH_FAILED",
                sender="arqonbus",
            )
            await self.send_to_client(client_id, response)
            return
        
        # Start a dedicated push loop for this operator
        task = asyncio.create_task(self._operator_push_loop(client_id, group))
        self._operator_tasks[client_id] = task
        
        logger.info(f"Operator {client_id} registered for group {group}")

    async def _operator_push_loop(self, client_id: str, group: str):
        """Periodically poll Redis for new tasks and push to the operator via WebSocket."""
        if not self.routing_coordinator or not self.routing_coordinator.operator_registry:
            return

        storage = self.routing_coordinator.operator_registry.storage
        if not storage:
            logger.warning("Storage not available for operator push loop")
            return

        stream = f"arqonbus:group:{group}"
        
        try:

            while self.running and client_id in self._operator_tasks:
                # Read 1 job from the group
                # Using client_id as consumer_id ensures exactly-once within the group
                res = await storage.read_group(stream, group, client_id, count=1, block_ms=5000)
                
                if not res:
                    continue

                for _, messages in res:
                    for msg_id, data in messages:
                        # Wrap job in Envelope for delivery
                        task_envelope = Envelope(
                            id=msg_id,
                            type="command",
                            command="truth.verify",
                            payload=data,
                            sender="arqonbus"
                        )
                        
                        await self.send_to_client(client_id, task_envelope)
                        # Note: We don't ACK here; worker must send an ACK command back
                        # Or if we want AUTO-ACK (not recommended for truthloop)
                        
                await asyncio.sleep(0.1) # Breather
                
        except Exception as e:
            logger.error(f"Error in operator push loop for {client_id}: {e}")
        finally:
            self._operator_tasks.pop(client_id, None)

    async def _disconnect_client(self, client_id: str):
        """Disconnect and cleanup a client.
        
        Args:
            client_id: Client to disconnect
        """
        try:
            # Cleanup operator tasks
            task = self._operator_tasks.pop(client_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Unregister from operator registry
            if self.routing_coordinator and self.routing_coordinator.operator_registry:
                await self.routing_coordinator.operator_registry.unregister_operator(client_id)

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
        from websockets.exceptions import ConnectionClosed
        try:
            client_info = await self.client_registry.get_client(client_id)
            if client_info:
                await client_info.websocket.send(envelope.to_json())
                return True
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected during send")
            await self._disconnect_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self._disconnect_client(client_id)
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
                "total_messages_routed": self._stats.get("total_messages_routed", 0),
                "routing_errors": self._stats.get("routing_errors", 0),
                "error_rate": float(self._stats.get("routing_errors", 0)) / max(1, int(self._stats.get("total_messages_routed", 0))),
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
        return self.running and self.server is not None and not getattr(self.server, 'is_closing', lambda: False)()
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
