"""Message routing logic for ArqonBus."""
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from ..protocol.envelope import Envelope
from .client_registry import ClientRegistry
from .rooms import RoomManager
from .channels import ChannelManager


logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Raised when message routing fails."""
    pass


class MessageRouter:
    """Central message routing coordinator for ArqonBus.
    
    Coordinates between:
    - Client registry (connection management)
    - Room manager (room-level routing)
    - Channel manager (channel-level routing)
    - Message validation and processing
    
    Handles routing decisions based on message envelope properties.
    """
    
    def __init__(
        self,
        client_registry: ClientRegistry,
        room_manager: RoomManager,
        channel_manager: ChannelManager
    ):
        """Initialize message router.
        
        Args:
            client_registry: Client connection management
            room_manager: Room-level routing
            channel_manager: Channel-level routing
        """
        self.client_registry = client_registry
        self.room_manager = room_manager
        self.channel_manager = channel_manager
        
        # Routing statistics
        self._stats = {
            "total_messages_routed": 0,
            "messages_by_type": {},
            "messages_by_destination": {},
            "routing_errors": 0,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    async def route_message(self, envelope: Envelope, sender_client_id: str) -> int:
        """Route a message to its destination(s).
        
        Args:
            envelope: Message to route
            sender_client_id: ID of client who sent the message
            
        Returns:
            Number of clients who received the message
            
        Raises:
            RoutingError: If routing fails
        """
        try:
            # Validate envelope
            if not envelope.type:
                raise RoutingError("Message type is required")
            
            # Route based on message type and destination
            if envelope.room and envelope.channel:
                # Direct room:channel routing
                return await self._route_to_room_channel(envelope, sender_client_id, envelope.room, envelope.channel)
            elif envelope.room:
                # Room-level broadcast
                return await self._route_to_room(envelope, sender_client_id, envelope.room)
            else:
                # Global broadcast or direct routing
                return await self._route_global(envelope, sender_client_id)
            
        except Exception as e:
            logger.error(f"Routing error for message {envelope.id}: {e}")
            self._stats["routing_errors"] += 1
            raise RoutingError(f"Failed to route message: {e}")
        finally:
            # Update statistics
            self._stats["total_messages_routed"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            # Track message type statistics
            msg_type = envelope.type
            if msg_type not in self._stats["messages_by_type"]:
                self._stats["messages_by_type"][msg_type] = 0
            self._stats["messages_by_type"][msg_type] += 1
    
    async def _route_to_room_channel(
        self, 
        envelope: Envelope, 
        sender_client_id: str, 
        room_id: str, 
        channel_id: str
    ) -> int:
        """Route message to specific room:channel.
        
        Args:
            envelope: Message to route
            sender_client_id: Sender client ID
            room_id: Target room ID
            channel_id: Target channel ID
            
        Returns:
            Number of clients who received the message
        """
        # Verify room and channel exist
        room = await self.room_manager.get_room(room_id)
        if not room:
            raise RoutingError(f"Room {room_id} does not exist")
        
        channel = await self.channel_manager.get_channel(channel_id)
        if not channel:
            raise RoutingError(f"Channel {channel_id} does not exist")
        
        # Verify channel belongs to room
        if channel.room and channel.room.room_id != room_id:
            raise RoutingError(f"Channel {channel_id} does not belong to room {room_id}")
        
        # Route to channel
        sent_count = await self.channel_manager.broadcast_to_channel(
            envelope, channel_id, exclude_client_id=sender_client_id
        )
        
        logger.debug(f"Routed message to room '{room_id}', channel '{channel_id}': {sent_count} clients")
        
        # Track destination statistics
        dest_key = f"{room_id}:{channel_id}"
        if dest_key not in self._stats["messages_by_destination"]:
            self._stats["messages_by_destination"][dest_key] = 0
        self._stats["messages_by_destination"][dest_key] += 1
        
        return sent_count
    
    async def _route_to_room(
        self, 
        envelope: Envelope, 
        sender_client_id: str, 
        room_id: str
    ) -> int:
        """Route message to all channels in a room.
        
        Args:
            envelope: Message to route
            sender_client_id: Sender client ID
            room_id: Target room ID
            
        Returns:
            Number of clients who received the message
        """
        # Verify room exists
        room = await self.room_manager.get_room(room_id)
        if not room:
            raise RoutingError(f"Room {room_id} does not exist")
        
        # Get all channels in room
        channels = await self.channel_manager.get_room_channels(room_id)
        
        # Route to each channel
        total_sent = 0
        for channel in channels:
            sent = await self.channel_manager.broadcast_to_channel(
                envelope, channel.channel_id, exclude_client_id=sender_client_id
            )
            total_sent += sent
        
        logger.debug(f"Routed message to room '{room_id}' (all channels): {total_sent} clients")
        return total_sent
    
    async def _route_global(
        self, 
        envelope: Envelope, 
        sender_client_id: str
    ) -> int:
        """Route message globally (all connected clients).
        
        Args:
            envelope: Message to route
            sender_client_id: Sender client ID
            
        Returns:
            Number of clients who received the message
        """
        # Get all connected clients
        all_clients = await self.client_registry.get_all_clients()
        
        # Send to all clients except sender
        sent_count = 0
        for client_info in all_clients:
            if client_info.client_id == sender_client_id:
                continue
            
            if client_info.websocket and client_info.websocket.open:
                try:
                    await client_info.websocket.send(envelope.to_json())
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending to client {client_info.client_id}: {e}")
        
        logger.debug(f"Routed message globally: {sent_count} clients")
        return sent_count
    
    async def route_direct_message(
        self, 
        envelope: Envelope, 
        sender_client_id: str, 
        target_client_id: str
    ) -> bool:
        """Route message directly to a specific client.
        
        Args:
            envelope: Message to route
            sender_client_id: Sender client ID
            target_client_id: Target client ID
            
        Returns:
            True if message was sent successfully
        """
        try:
            # Get target client
            target_client = await self.client_registry.get_client(target_client_id)
            if not target_client or not target_client.websocket.open:
                raise RoutingError(f"Target client {target_client_id} is not available")
            
            # Add sender info to envelope
            envelope.sender = sender_client_id
            
            # Send message
            await target_client.websocket.send(envelope.to_json())
            
            logger.debug(f"Direct message from {sender_client_id} to {target_client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Direct message routing failed: {e}")
            return False
    
    async def route_error_message(
        self, 
        original_envelope: Envelope, 
        error_message: str, 
        error_code: str = "ROUTING_ERROR"
    ) -> bool:
        """Route error message back to the sender.
        
        Args:
            original_envelope: Original message that caused the error
            error_message: Error message to send
            error_code: Machine-readable error code
            
        Returns:
            True if error was sent successfully
        """
        try:
            if not original_envelope.sender:
                return False
            
            error_envelope = Envelope(
                type="error",
                request_id=original_envelope.id,
                error=error_message,
                error_code=error_code,
                sender="arqonbus",
                metadata={"original_message_type": original_envelope.type}
            )
            
            return await self.route_direct_message(error_envelope, "arqonbus", original_envelope.sender)
            
        except Exception as e:
            logger.error(f"Failed to route error message: {e}")
            return False
    
    async def join_client_to_room_channel(
        self, 
        client_id: str, 
        room_id: str, 
        channel_id: str
    ) -> bool:
        """Join client to room and channel.
        
        Args:
            client_id: Client to join
            room_id: Room to join
            channel_id: Channel to join
            
        Returns:
            True if join was successful
        """
        try:
            # Verify room exists
            room = await self.room_manager.get_room(room_id)
            if not room:
                logger.error(f"Room {room_id} does not exist")
                return False
            
            # Verify channel exists and belongs to room
            channel = await self.channel_manager.get_channel(channel_id)
            if not channel or not channel.room or channel.room.room_id != room_id:
                logger.error(f"Channel {channel_id} does not exist in room {room_id}")
                return False
            
            # Join room
            room_joined = await self.room_manager.join_room(client_id, room_id)
            
            # Join channel
            channel_joined = await self.channel_manager.join_channel(client_id, channel_id)
            
            # Update client registry with room/channel info
            client_info = await self.client_registry.get_client(client_id)
            if client_info:
                await self.client_registry.join_room_channel(client_id, room_id, channel_id)
            
            success = room_joined and channel_joined
            if success:
                logger.info(f"Client {client_id} joined room '{room_id}', channel '{channel_id}'")
            else:
                logger.error(f"Failed to join client {client_id} to room '{room_id}', channel '{channel_id}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error joining client to room/channel: {e}")
            return False
    
    async def leave_client_from_room_channel(
        self, 
        client_id: str, 
        room_id: str, 
        channel_id: str
    ) -> bool:
        """Remove client from room and channel.
        
        Args:
            client_id: Client to remove
            room_id: Room to leave
            channel_id: Channel to leave
            
        Returns:
            True if leave was successful
        """
        try:
            # Leave channel
            channel_left = await self.channel_manager.leave_channel(client_id, channel_id)
            
            # Leave room
            room_left = await self.room_manager.leave_room(client_id, room_id)
            
            # Update client registry
            await self.client_registry.leave_room_channel(client_id, room_id, channel_id)
            
            success = room_left and channel_left
            if success:
                logger.info(f"Client {client_id} left room '{room_id}', channel '{channel_id}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing client from room/channel: {e}")
            return False
    
    async def get_routing_stats(self) -> Dict:
        """Get comprehensive routing statistics.
        
        Returns:
            Dictionary of routing statistics
        """
        try:
            client_stats = await self.client_registry.get_stats()
            room_stats = await self.room_manager.get_all_stats()
            channel_stats = await self.channel_manager.get_all_stats()
            
            return {
                "routing": self._stats.copy(),
                "clients": client_stats,
                "rooms": room_stats,
                "channels": channel_stats,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting routing stats: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow()}
    
    async def health_check(self) -> Dict:
        """Perform health check on message router.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_routing_stats()
            
            health = {
                "status": "healthy",
                "total_messages_routed": self._stats["total_messages_routed"],
                "routing_errors": self._stats["routing_errors"],
                "error_rate": self._stats["routing_errors"] / max(1, self._stats["total_messages_routed"]),
                "checks": []
            }
            
            # Check for potential issues
            if health["error_rate"] > 0.05:  # 5% error rate
                health["checks"].append({"type": "error", "message": "High routing error rate"})
            
            # Check component health
            client_health = await self.client_registry.health_check()
            room_health = await self.room_manager.health_check()
            channel_health = await self.channel_manager.health_check()
            
            if client_health.get("status") != "healthy":
                health["checks"].append({"type": "error", "message": "Client registry unhealthy"})
            
            if room_health.get("status") != "healthy":
                health["checks"].append({"type": "error", "message": "Room manager unhealthy"})
            
            if channel_health.get("status") != "healthy":
                health["checks"].append({"type": "error", "message": "Channel manager unhealthy"})
            
            # Overall status
            if health["checks"]:
                health["status"] = "degraded" if health["error_rate"] < 0.1 else "unhealthy"
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }


class RoutingCoordinator:
    """High-level routing coordinator that manages all routing components."""
    
    def __init__(self):
        """Initialize routing coordinator."""
        self._client_registry = ClientRegistry()
        self._room_manager = RoomManager()
        self._channel_manager = ChannelManager()
        self._router = MessageRouter(
            self._client_registry,
            self._room_manager,
            self._channel_manager
        )
    
    async def initialize(self):
        """Initialize routing system components."""
        # Create default room and channel
        try:
            default_room_id = await self._room_manager.create_room(
                name="general",
                description="Default general discussion room"
            )
            
            await self._channel_manager.create_channel(
                room_id=default_room_id,
                name="general",
                description="Default general channel"
            )
            
            logger.info("Initialized default room and channel")
            
        except Exception as e:
            logger.error(f"Error initializing routing system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown routing system components."""
        try:
            # Cleanup resources
            await self._client_registry.cleanup_disconnected_clients()
            
            logger.info("Routing system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during routing system shutdown: {e}")
    
    @property
    def message_router(self) -> MessageRouter:
        """Get the message router."""
        return self._router
    
    @property
    def router(self) -> MessageRouter:
        """Alias for message_router used by some callers."""
        return self._router
    
    @property
    def client_registry(self) -> ClientRegistry:
        """Get the client registry."""
        return self._client_registry

    @client_registry.setter
    def client_registry(self, value: ClientRegistry):
        """Set the client registry (used for testing/integration)."""
        self._client_registry = value
    
    @property
    def room_manager(self) -> RoomManager:
        """Get the room manager."""
        return self._room_manager

    @room_manager.setter
    def room_manager(self, value: RoomManager):
        """Set the room manager (used for testing/integration)."""
        self._room_manager = value
    
    @property
    def channel_manager(self) -> ChannelManager:
        """Get the channel manager."""
        return self._channel_manager

    @channel_manager.setter
    def channel_manager(self, value: ChannelManager):
        """Set the channel manager (used for testing/integration)."""
        self._channel_manager = value
