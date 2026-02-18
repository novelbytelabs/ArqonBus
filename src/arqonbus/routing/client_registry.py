"""Client registry for managing connected clients in ArqonBus."""
import asyncio
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
import weakref
import json

from ..protocol.envelope import Envelope
from ..protocol.ids import generate_client_id


logger = logging.getLogger(__name__)


class ClientInfo:
    """Information about a connected client."""
    
    def __init__(self, client_id: str, websocket, room: Optional[str] = None, channel: Optional[str] = None):
        """Initialize client info.
        
        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection object
            room: Current room the client is in
            channel: Current channel the client is in
        """
        self.client_id = client_id
        self.websocket = websocket
        self.room = room
        self.channel = channel
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.subscriptions: Set[str] = set()  # room:channel combinations
        self.metadata: Dict[str, any] = {}
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def subscribe_to_room_channel(self, room: str, channel: str):
        """Subscribe client to room:channel combination."""
        subscription = f"{room}:{channel}"
        self.subscriptions.add(subscription)
    
    def unsubscribe_from_room_channel(self, room: str, channel: str):
        """Unsubscribe client from room:channel combination."""
        subscription = f"{room}:{channel}"
        self.subscriptions.discard(subscription)
    
    def is_subscribed_to(self, room: str, channel: str) -> bool:
        """Check if client is subscribed to room:channel."""
        subscription = f"{room}:{channel}"
        return subscription in self.subscriptions
    
    def to_dict(self) -> dict:
        """Convert client info to dictionary."""
        return {
            "client_id": self.client_id,
            "room": self.room,
            "channel": self.channel,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "subscriptions": list(self.subscriptions),
            "metadata": self.metadata
        }


class ClientRegistry:
    """Registry for managing all connected clients.
    
    Thread-safe client registry that tracks:
    - Active WebSocket connections
    - Client room/channel subscriptions
    - Client metadata and activity
    """
    
    def __init__(self):
        """Initialize client registry."""
        self._lock = asyncio.Lock()
        
        # Active clients by ID
        # {client_id: ClientInfo}
        self._clients: Dict[str, ClientInfo] = {}
        
        # Reverse mapping for WebSocket to client_id
        # {websocket: client_id}
        self._ws_to_client: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        
        # Room membership tracking
        # {room: {channel: {client_id}}}
        self._room_membership: Dict[str, Dict[str, Set[str]]] = {}
        
        # Statistics
        self._stats = {
            "total_clients": 0,
            "clients_by_room": {},
            "clients_by_channel": {},
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }

    @staticmethod
    def _websocket_is_open(websocket) -> bool:
        """Best-effort compatibility check across websocket implementations."""
        if websocket is None:
            return False
        if hasattr(websocket, "open"):
            try:
                return bool(websocket.open)
            except Exception:
                return False
        if hasattr(websocket, "closed"):
            try:
                return not bool(websocket.closed)
            except Exception:
                return False
        if hasattr(websocket, "state"):
            # websockets>=14 uses connection state values; treat OPEN as sendable.
            state = getattr(websocket, "state", None)
            if state is None:
                return False
            state_name = getattr(state, "name", str(state))
            return str(state_name).upper() == "OPEN"
        return True
    
    async def register_client(self, websocket, room: Optional[str] = None, channel: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        """Register a new client connection.
        
        Args:
            websocket: WebSocket connection object
            room: Initial room for the client
            channel: Initial channel for the client
            metadata: Additional client metadata
            
        Returns:
            client_id: Unique identifier for the client
        """
        async with self._lock:
            client_id = generate_client_id()
            
            # Create client info
            client_info = ClientInfo(client_id, websocket, room, channel)
            if metadata:
                client_info.metadata.update(metadata)
            
            # Register client
            self._clients[client_id] = client_info
            self._ws_to_client[websocket] = client_id
            
            # Add to room membership if room/channel specified
            if room and channel:
                await self._add_to_room_membership(client_id, room, channel)
                client_info.subscribe_to_room_channel(room, channel)
            
            # Update statistics
            self._stats["total_clients"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Registered client {client_id} in room '{room}', channel '{channel}'")
            return client_id
    
    async def unregister_client(self, client_id: str):
        """Unregister a client connection.
        
        Args:
            client_id: ID of client to unregister
        """
        async with self._lock:
            if client_id not in self._clients:
                return
            
            client_info = self._clients[client_id]
            
            # Remove from room memberships
            for subscription in client_info.subscriptions:
                room, channel = subscription.split(":", 1)
                await self._remove_from_room_membership(client_id, room, channel)
            
            # Remove from registry
            del self._clients[client_id]
            
            # Remove from WebSocket mapping
            if client_info.websocket in self._ws_to_client:
                del self._ws_to_client[client_info.websocket]
            
            # Update statistics
            self._stats["total_clients"] -= 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Unregistered client {client_id}")
    
    async def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """Get client information by ID.
        
        Args:
            client_id: Client ID to lookup
            
        Returns:
            ClientInfo or None if not found
        """
        async with self._lock:
            return self._clients.get(client_id)
    
    async def get_client_by_websocket(self, websocket) -> Optional[ClientInfo]:
        """Get client information by WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            ClientInfo or None if not found
        """
        async with self._lock:
            client_id = self._ws_to_client.get(websocket)
            if client_id:
                return self._clients.get(client_id)
            return None
    
    async def join_room_channel(self, client_id: str, room: str, channel: str):
        """Add client to a room/channel.
        
        Args:
            client_id: Client to add
            room: Room to join
            channel: Channel to join
        """
        async with self._lock:
            if client_id not in self._clients:
                raise ValueError(f"Client {client_id} not found")
            
            client_info = self._clients[client_id]
            
            # Update client info
            client_info.room = room
            client_info.channel = channel
            client_info.subscribe_to_room_channel(room, channel)
            
            # Add to room membership
            await self._add_to_room_membership(client_id, room, channel)
            
            logger.info(f"Client {client_id} joined room '{room}', channel '{channel}'")
    
    async def leave_room_channel(self, client_id: str, room: str, channel: str):
        """Remove client from a room/channel.
        
        Args:
            client_id: Client to remove
            room: Room to leave
            channel: Channel to leave
        """
        async with self._lock:
            if client_id not in self._clients:
                return
            
            client_info = self._clients[client_id]
            
            # Update client info
            client_info.unsubscribe_from_room_channel(room, channel)
            
            # Remove from room membership
            await self._remove_from_room_membership(client_id, room, channel)
            
            # Clear current room/channel if this was the active one
            if client_info.room == room and client_info.channel == channel:
                client_info.room = None
                client_info.channel = None
            
            logger.info(f"Client {client_id} left room '{room}', channel '{channel}'")
    
    async def get_clients_in_room_channel(self, room: str, channel: str) -> List[ClientInfo]:
        """Get all clients in a specific room/channel.
        
        Args:
            room: Room to query
            channel: Channel to query
            
        Returns:
            List of ClientInfo objects
        """
        async with self._lock:
            clients = []
            client_ids = self._room_membership.get(room, {}).get(channel, set())
            
            for client_id in client_ids:
                client_info = self._clients.get(client_id)
                if client_info:
                    clients.append(client_info)
            
            return clients
    
    async def get_all_clients(self) -> List[ClientInfo]:
        """Get all registered clients.
        
        Returns:
            List of all ClientInfo objects
        """
        async with self._lock:
            return list(self._clients.values())
    
    async def get_clients_by_room(self, room: str) -> List[ClientInfo]:
        """Get all clients in a specific room (all channels).
        
        Args:
            room: Room to query
            
        Returns:
            List of ClientInfo objects
        """
        async with self._lock:
            clients = []
            room_channels = self._room_membership.get(room, {})
            
            for channel_clients in room_channels.values():
                for client_id in channel_clients:
                    client_info = self._clients.get(client_id)
                    if client_info:
                        clients.append(client_info)
            
            return clients
    
    async def broadcast_to_room_channel(
        self,
        message: Envelope,
        room: str,
        channel: str,
        exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all clients in room/channel.
        
        Args:
            message: Message to broadcast
            room: Target room
            channel: Target channel
            exclude_client_id: Client ID to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        clients = await self.get_clients_in_room_channel(room, channel)
        message_json = message.to_json()
        sent_count = 0
        
        for client_info in clients:
            if client_info.client_id == exclude_client_id:
                continue
            
            try:
                if hasattr(client_info.websocket, 'send') and self._websocket_is_open(client_info.websocket):
                    await client_info.websocket.send(message_json)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send message to client {client_info.client_id}: {e}")
        
        logger.debug(f"Broadcasted message to {sent_count} clients in room '{room}', channel '{channel}'")
        return sent_count
    
    async def _add_to_room_membership(self, client_id: str, room: str, channel: str):
        """Add client to room membership tracking.
        
        Args:
            client_id: Client to add
            room: Room to add to
            channel: Channel to add to
        """
        if room not in self._room_membership:
            self._room_membership[room] = {}
        
        if channel not in self._room_membership[room]:
            self._room_membership[room][channel] = set()
        
        self._room_membership[room][channel].add(client_id)
    
    async def _remove_from_room_membership(self, client_id: str, room: str, channel: str):
        """Remove client from room membership tracking.
        
        Args:
            client_id: Client to remove
            room: Room to remove from
            channel: Channel to remove from
        """
        if room in self._room_membership and channel in self._room_membership[room]:
            self._room_membership[room][channel].discard(client_id)
            
            # Clean up empty channels/rooms
            if not self._room_membership[room][channel]:
                del self._room_membership[room][channel]
            
            if not self._room_membership[room]:
                del self._room_membership[room]
    
    async def update_client_activity(self, client_id: str):
        """Update client's last activity timestamp.
        
        Args:
            client_id: Client to update
        """
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].update_activity()
    
    async def cleanup_disconnected_clients(self) -> int:
        """Clean up clients with closed WebSocket connections.
        
        Returns:
            Number of clients cleaned up
        """
        async with self._lock:
            disconnected = []
            
            for client_id, client_info in self._clients.items():
                # Check if WebSocket is still open
                if not self._websocket_is_open(client_info.websocket):
                    disconnected.append(client_id)
            
            # Remove disconnected clients
            for client_id in disconnected:
                await self.unregister_client(client_id)
            
            if disconnected:
                logger.info(f"Cleaned up {len(disconnected)} disconnected clients")
            
            return len(disconnected)
    
    async def get_stats(self) -> Dict:
        """Get client registry statistics.
        
        Returns:
            Dictionary of statistics
        """
        async with self._lock:
            stats = self._stats.copy()
            stats["current_clients"] = len(self._clients)
            stats["active_rooms"] = len(self._room_membership)
            
            # Calculate clients by room/channel
            clients_by_room = {}
            for room, channels in self._room_membership.items():
                total_clients = sum(len(clients) for clients in channels.values())
                clients_by_room[room] = {
                    "total_clients": total_clients,
                    "channels": {ch: len(clients) for ch, clients in channels.items()}
                }
            
            stats["room_stats"] = clients_by_room
            stats["last_updated"] = datetime.utcnow()
            
            return stats
    
    async def health_check(self) -> Dict[str, any]:
        """Perform health check on the client registry.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_stats()
            
            health = {
                "status": "healthy",
                "total_clients": stats["current_clients"],
                "active_rooms": stats["active_rooms"],
                "checks": []
            }
            
            # Check for potential issues
            if stats["current_clients"] > 10000:
                health["checks"].append({"type": "warning", "message": "High number of connected clients"})
            
            if stats["active_rooms"] > 1000:
                health["checks"].append({"type": "warning", "message": "Large number of active rooms"})
            
            # Check for stale clients
            stale_count = 0
            cutoff_time = datetime.utcnow().timestamp() - 3600  # 1 hour ago
            for client_info in self._clients.values():
                if client_info.last_activity.timestamp() < cutoff_time:
                    stale_count += 1
            
            if stale_count > 0:
                health["checks"].append({"type": "warning", "message": f"{stale_count} clients may be stale"})
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
