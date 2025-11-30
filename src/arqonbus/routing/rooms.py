"""Room management for ArqonBus message routing."""
import asyncio
import logging
from typing import Dict, Set, Optional, List, Any
from datetime import datetime
import threading

from ..protocol.envelope import Envelope
from ..protocol.ids import generate_room_id


logger = logging.getLogger(__name__)


class Room:
    """Represents a room for message routing.
    
    A room is a logical grouping of channels where messages can be routed.
    Clients can join rooms and broadcast to all channels within the room.
    """
    
    def __init__(self, room_id: str, name: Optional[str] = None, description: Optional[str] = None):
        """Initialize a room.
        
        Args:
            room_id: Unique room identifier
            name: Human-readable room name
            description: Room description
        """
        self.room_id = room_id
        self.name = name or room_id
        self.description = description or ""
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Channel tracking
        self.channels: Dict[str, "Channel"] = {}
        
        # Membership tracking
        self.member_count = 0
        self.metadata: Dict[str, Any] = {}
        
        # Statistics
        self._stats = {
            "total_messages": 0,
            "total_broadcasts": 0,
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }
    
    def add_channel(self, channel: "Channel"):
        """Add a channel to this room.
        
        Args:
            channel: Channel to add
        """
        self.channels[channel.channel_id] = channel
        channel.room = self
        logger.debug(f"Added channel {channel.channel_id} to room {self.room_id}")
    
    def remove_channel(self, channel_id: str) -> Optional["Channel"]:
        """Remove a channel from this room.
        
        Args:
            channel_id: ID of channel to remove
            
        Returns:
            Removed channel or None if not found
        """
        channel = self.channels.pop(channel_id, None)
        if channel:
            channel.room = None
            logger.debug(f"Removed channel {channel_id} from room {self.room_id}")
        return channel
    
    def get_channel(self, channel_id: str) -> Optional["Channel"]:
        """Get a channel by ID.
        
        Args:
            channel_id: Channel ID to lookup
            
        Returns:
            Channel or None if not found
        """
        return self.channels.get(channel_id)
    
    def has_channel(self, channel_id: str) -> bool:
        """Check if room has a specific channel.
        
        Args:
            channel_id: Channel ID to check
            
        Returns:
            True if channel exists
        """
        return channel_id in self.channels
    
    def get_all_channels(self) -> List["Channel"]:
        """Get all channels in this room.
        
        Returns:
            List of all channels
        """
        return list(self.channels.values())
    
    def update_activity(self):
        """Update room's last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def broadcast_to_room(self, message: Envelope, exclude_client_id: Optional[str] = None) -> int:
        """Broadcast message to all channels in the room.
        
        Args:
            message: Message to broadcast
            exclude_client_id: Client ID to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        total_sent = 0
        
        for channel in self.channels.values():
            sent = channel.broadcast_to_channel(message, exclude_client_id)
            total_sent += sent
        
        self._stats["total_broadcasts"] += 1
        self.update_activity()
        
        logger.debug(f"Broadcasted message to {total_sent} clients in room {self.room_id}")
        return total_sent
    
    def get_stats(self) -> Dict[str, Any]:
        """Get room statistics.
        
        Returns:
            Dictionary of room statistics
        """
        channel_stats = {}
        for channel_id, channel in self.channels.items():
            channel_stats[channel_id] = {
                "name": channel.name,
                "member_count": channel.member_count,
                "created_at": channel.created_at.isoformat()
            }
        
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "channels": channel_stats,
            "total_channels": len(self.channels),
            "total_members": self.member_count,
            "stats": self._stats.copy()
        }


class RoomManager:
    """Manages all rooms in ArqonBus.
    
    Thread-safe room management that tracks:
    - Room creation and deletion
    - Channel management within rooms
    - Client room membership
    - Room statistics and activity
    """
    
    def __init__(self):
        """Initialize room manager."""
        self._lock = asyncio.Lock()
        
        # Room storage
        # {room_id: Room}
        self._rooms: Dict[str, Room] = {}
        
        # Room name lookup
        # {room_name: room_id}
        self._room_names: Dict[str, str] = {}
        
        # Client room membership
        # {client_id: {room_id}}
        self._client_rooms: Dict[str, Set[str]] = {}
        
        # Statistics
        self._stats = {
            "total_rooms": 0,
            "total_channels": 0,
            "rooms_by_activity": {},
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    async def create_room(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        room_id: Optional[str] = None
    ) -> str:
        """Create a new room.
        
        Args:
            name: Room name (auto-generated if None)
            description: Room description
            room_id: Specific room ID (auto-generated if None)
            
        Returns:
            room_id: ID of created room
        """
        async with self._lock:
            # Generate IDs if not provided
            room_id = room_id or generate_room_id()
            name = name or f"room_{len(self._rooms)}"
            
            # Check for name conflicts
            if name in self._room_names:
                raise ValueError(f"Room name '{name}' already exists")
            
            # Create room
            room = Room(room_id, name, description)
            self._rooms[room_id] = room
            self._room_names[name] = room_id
            
            # Update statistics
            self._stats["total_rooms"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Created room '{name}' with ID {room_id}")
            return room_id
    
    async def delete_room(self, room_id: str) -> bool:
        """Delete a room.
        
        Args:
            room_id: ID of room to delete
            
        Returns:
            True if room was deleted
        """
        async with self._lock:
            if room_id not in self._rooms:
                return False
            
            room = self._rooms[room_id]
            
            # Remove room name mapping
            self._room_names.pop(room.name, None)
            
            # Remove from rooms
            del self._rooms[room_id]
            
            # Update statistics
            self._stats["total_rooms"] -= 1
            self._stats["total_channels"] -= len(room.channels)
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Deleted room '{room.name}' with ID {room_id}")
            return True
    
    async def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID.
        
        Args:
            room_id: Room ID to lookup
            
        Returns:
            Room or None if not found
        """
        async with self._lock:
            return self._rooms.get(room_id)
    
    async def get_room_by_name(self, name: str) -> Optional[Room]:
        """Get room by name.
        
        Args:
            name: Room name to lookup
            
        Returns:
            Room or None if not found
        """
        async with self._lock:
            room_id = self._room_names.get(name)
            if room_id:
                return self._rooms.get(room_id)
            return None
    
    async def list_rooms(self) -> List[Room]:
        """List all rooms.
        
        Returns:
            List of all rooms
        """
        async with self._lock:
            return list(self._rooms.values())
    
    async def room_exists(self, room_id: str) -> bool:
        """Check if room exists.
        
        Args:
            room_id: Room ID to check
            
        Returns:
            True if room exists
        """
        async with self._lock:
            return room_id in self._rooms
    
    async def join_room(self, client_id: str, room_id: str) -> bool:
        """Add client to a room.
        
        Args:
            client_id: Client to add
            room_id: Room to join
            
        Returns:
            True if client was added successfully
        """
        async with self._lock:
            if room_id not in self._rooms:
                return False
            
            # Add to room membership
            if client_id not in self._client_rooms:
                self._client_rooms[client_id] = set()
            
            self._client_rooms[client_id].add(room_id)
            
            # Update room stats
            self._rooms[room_id].member_count += 1
            self._rooms[room_id].update_activity()
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Client {client_id} joined room {room_id}")
            return True
    
    async def leave_room(self, client_id: str, room_id: str) -> bool:
        """Remove client from a room.
        
        Args:
            client_id: Client to remove
            room_id: Room to leave
            
        Returns:
            True if client was removed successfully
        """
        async with self._lock:
            # Remove from room membership
            if client_id in self._client_rooms:
                self._client_rooms[client_id].discard(room_id)
                
                # Clean up empty client entry
                if not self._client_rooms[client_id]:
                    del self._client_rooms[client_id]
            
            # Update room stats
            if room_id in self._rooms:
                self._rooms[room_id].member_count = max(0, self._rooms[room_id].member_count - 1)
                self._rooms[room_id].update_activity()
                self._stats["last_activity"] = datetime.utcnow()
                
                logger.info(f"Client {client_id} left room {room_id}")
                return True
            
            return False
    
    async def get_client_rooms(self, client_id: str) -> Set[str]:
        """Get all rooms a client is a member of.
        
        Args:
            client_id: Client ID to lookup
            
        Returns:
            Set of room IDs the client is in
        """
        async with self._lock:
            return self._client_rooms.get(client_id, set())
    
    async def broadcast_to_room(
        self,
        message: Envelope,
        room_id: str,
        exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all channels in a room.
        
        Args:
            message: Message to broadcast
            room_id: Target room ID
            exclude_client_id: Client ID to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        async with self._lock:
            room = self._rooms.get(room_id)
            if not room:
                return 0
            
            sent_count = room.broadcast_to_room(message, exclude_client_id)
            self._stats["last_activity"] = datetime.utcnow()
            return sent_count
    
    async def get_room_stats(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific room.
        
        Args:
            room_id: Room ID to get stats for
            
        Returns:
            Room statistics dictionary or None if room not found
        """
        async with self._lock:
            room = self._rooms.get(room_id)
            if room:
                return room.get_stats()
            return None
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive room manager statistics.
        
        Returns:
            Dictionary of all room manager statistics
        """
        async with self._lock:
            room_list = list(self._rooms.values())
            
            # Calculate activity statistics
            now = datetime.utcnow()
            active_rooms = sum(1 for room in room_list 
                             if (now - room.last_activity).total_seconds() < 3600)  # Active within 1 hour
            
            inactive_rooms = len(room_list) - active_rooms
            
            # Room statistics
            room_stats = {}
            total_members = 0
            total_channels = 0
            
            for room in room_list:
                stats = room.get_stats()
                room_stats[room.room_id] = {
                    "name": room.name,
                    "member_count": stats["total_members"],
                    "channel_count": stats["total_channels"],
                    "last_activity": room.last_activity.isoformat()
                }
                total_members += stats["total_members"]
                total_channels += stats["total_channels"]
            
            return {
                "total_rooms": self._stats["total_rooms"],
                "total_channels": total_channels,
                "total_members": total_members,
                "active_rooms": active_rooms,
                "inactive_rooms": inactive_rooms,
                "total_client_memberships": len(self._client_rooms),
                "created_at": self._stats["created_at"].isoformat(),
                "last_activity": self._stats["last_activity"].isoformat(),
                "rooms": room_stats,
                "timestamp": datetime.utcnow()
            }
    
    async def cleanup_inactive_rooms(self, hours: int = 24) -> int:
        """Clean up inactive rooms.
        
        Args:
            hours: Number of hours of inactivity before cleanup
            
        Returns:
            Number of rooms cleaned up
        """
        async with self._lock:
            cutoff_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_time = cutoff_time.timestamp() - (hours * 3600)
            
            rooms_to_remove = []
            for room_id, room in self._rooms.items():
                if room.last_activity.timestamp() < cutoff_time and room.member_count == 0:
                    rooms_to_remove.append(room_id)
            
            for room_id in rooms_to_remove:
                await self.delete_room(room_id)
            
            if rooms_to_remove:
                logger.info(f"Cleaned up {len(rooms_to_remove)} inactive rooms")
            
            return len(rooms_to_remove)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on room manager.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_all_stats()
            
            health = {
                "status": "healthy",
                "total_rooms": stats["total_rooms"],
                "total_channels": stats["total_channels"],
                "total_members": stats["total_members"],
                "active_rooms": stats["active_rooms"],
                "checks": []
            }
            
            # Check for potential issues
            if stats["total_rooms"] > 10000:
                health["checks"].append({"type": "warning", "message": "Large number of rooms"})
            
            if stats["inactive_rooms"] > stats["total_rooms"] * 0.8:
                health["checks"].append({"type": "warning", "message": "Many inactive rooms"})
            
            # Check room name conflicts
            if len(self._room_names) != len(self._rooms):
                health["checks"].append({"type": "error", "message": "Room name mapping inconsistent"})
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }