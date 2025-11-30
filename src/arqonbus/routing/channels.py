"""Channel management for ArqonBus message routing."""
import asyncio
import logging
from typing import Dict, Set, Optional, List, Any
from datetime import datetime, timedelta

from ..protocol.envelope import Envelope
from ..protocol.ids import generate_channel_id


logger = logging.getLogger(__name__)


class Channel:
    """Represents a channel within a room for message routing.
    
    A channel is a specific communication stream within a room.
    Messages sent to a channel are only delivered to clients subscribed to that channel.
    """
    
    def __init__(
        self, 
        channel_id: str, 
        name: Optional[str] = None, 
        description: Optional[str] = None,
        room: Optional["Room"] = None
    ):
        """Initialize a channel.
        
        Args:
            channel_id: Unique channel identifier
            name: Human-readable channel name
            description: Channel description
            room: Room this channel belongs to
        """
        self.channel_id = channel_id
        self.name = name or channel_id
        self.description = description or ""
        self.room = room
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Member tracking
        self.member_count = 0
        self.members: Set[str] = set()  # Client IDs
        self.metadata: Dict[str, Any] = {}
        
        # Message statistics
        self._stats = {
            "total_messages": 0,
            "total_broadcasts": 0,
            "total_members": 0,
            "messages_per_hour": [],
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }
    
    def add_member(self, client_id: str):
        """Add a client to this channel.
        
        Args:
            client_id: Client to add
        """
        if client_id not in self.members:
            self.members.add(client_id)
            self.member_count += 1
            self._stats["total_members"] += 1
            self.update_activity()
            logger.debug(f"Added client {client_id} to channel {self.channel_id}")
    
    def remove_member(self, client_id: str) -> bool:
        """Remove a client from this channel.
        
        Args:
            client_id: Client to remove
            
        Returns:
            True if client was removed
        """
        if client_id in self.members:
            self.members.remove(client_id)
            self.member_count = max(0, self.member_count - 1)
            self.update_activity()
            logger.debug(f"Removed client {client_id} from channel {self.channel_id}")
            return True
        return False
    
    def has_member(self, client_id: str) -> bool:
        """Check if client is a member of this channel.
        
        Args:
            client_id: Client ID to check
            
        Returns:
            True if client is a member
        """
        return client_id in self.members
    
    def get_all_members(self) -> Set[str]:
        """Get all member client IDs.
        
        Returns:
            Set of member client IDs
        """
        return self.members.copy()
    
    def update_activity(self):
        """Update channel's last activity timestamp."""
        self.last_activity = datetime.utcnow()
        
        # Track message rate (rolling window)
        now = datetime.utcnow()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Keep only last 24 hours of data
        self._stats["messages_per_hour"] = [
            timestamp for timestamp in self._stats["messages_per_hour"]
            if current_hour - timestamp < timedelta(hours=24)
        ]
    
    def record_message(self):
        """Record a message being sent to this channel."""
        self._stats["total_messages"] += 1
        self._stats["messages_per_hour"].append(datetime.utcnow())
        self.update_activity()
    
    def broadcast_to_channel(
        self, 
        message: Envelope, 
        exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all channel members.
        
        Args:
            message: Message to broadcast
            exclude_client_id: Client ID to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        if not self.members:
            return 0
        
        # Record message statistics
        self.record_message()
        
        # Send message to each member
        sent_count = 0
        for client_id in self.members:
            if client_id == exclude_client_id:
                continue
            
            try:
                # This will be handled by the client registry
                # Just count how many would receive it
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
        
        self._stats["total_broadcasts"] += 1
        logger.debug(f"Broadcasted message to {sent_count} clients in channel {self.channel_id}")
        return sent_count
    
    def get_message_rate(self, hours: int = 1) -> float:
        """Get average messages per hour over specified period.
        
        Args:
            hours: Number of hours to calculate rate for
            
        Returns:
            Messages per hour
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_messages = [
            timestamp for timestamp in self._stats["messages_per_hour"]
            if timestamp > cutoff_time
        ]
        
        return len(recent_messages) / hours if hours > 0 else 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get channel statistics.
        
        Returns:
            Dictionary of channel statistics
        """
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "member_count": self.member_count,
            "total_members": self._stats["total_members"],
            "total_messages": self._stats["total_messages"],
            "total_broadcasts": self._stats["total_broadcasts"],
            "message_rate_1h": self.get_message_rate(1),
            "message_rate_24h": self.get_message_rate(24),
            "room_id": self.room.room_id if self.room else None,
            "metadata": self.metadata
        }


class ChannelManager:
    """Manages all channels in ArqonBus.
    
    Thread-safe channel management that tracks:
    - Channel creation and deletion within rooms
    - Client channel membership
    - Channel statistics and activity
    - Message routing within channels
    """
    
    def __init__(self):
        """Initialize channel manager."""
        self._lock = asyncio.Lock()
        
        # Channel storage
        # {channel_id: Channel}
        self._channels: Dict[str, Channel] = {}
        
        # Channel name lookup within rooms
        # {(room_id, channel_name): channel_id}
        self._channel_names: Dict[tuple, str] = {}
        
        # Client channel membership
        # {client_id: {channel_id}}
        self._client_channels: Dict[str, Set[str]] = {}
        
        # Statistics
        self._stats = {
            "total_channels": 0,
            "total_members": 0,
            "total_messages": 0,
            "channels_by_activity": {},
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    async def create_channel(
        self,
        room_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> str:
        """Create a new channel in a room.
        
        Args:
            room_id: Room ID to create channel in
            name: Channel name (auto-generated if None)
            description: Channel description
            channel_id: Specific channel ID (auto-generated if None)
            
        Returns:
            channel_id: ID of created channel
        """
        async with self._lock:
            # Generate IDs if not provided
            channel_id = channel_id or generate_channel_id()
            name = name or f"channel_{len(self._channels)}"
            
            # Check for name conflicts within room
            channel_key = (room_id, name)
            if channel_key in self._channel_names:
                raise ValueError(f"Channel name '{name}' already exists in room {room_id}")
            
            # Create channel
            channel = Channel(channel_id, name, description)
            self._channels[channel_id] = channel
            self._channel_names[channel_key] = channel_id
            
            # Update statistics
            self._stats["total_channels"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Created channel '{name}' in room {room_id} with ID {channel_id}")
            return channel_id
    
    async def delete_channel(self, channel_id: str) -> bool:
        """Delete a channel.
        
        Args:
            channel_id: ID of channel to delete
            
        Returns:
            True if channel was deleted
        """
        async with self._lock:
            if channel_id not in self._channels:
                return False
            
            channel = self._channels[channel_id]
            
            # Remove from room if available
            if channel.room:
                channel.room.remove_channel(channel_id)
            
            # Remove channel name mapping
            channel_key = (channel.room.room_id if channel.room else "", channel.name)
            self._channel_names.pop(channel_key, None)
            
            # Remove from channels
            del self._channels[channel_id]
            
            # Remove client memberships
            for client_id in list(channel.members):
                await self.leave_channel(client_id, channel_id)
            
            # Update statistics
            self._stats["total_channels"] -= 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Deleted channel '{channel.name}' with ID {channel_id}")
            return True
    
    async def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get channel by ID.
        
        Args:
            channel_id: Channel ID to lookup
            
        Returns:
            Channel or None if not found
        """
        async with self._lock:
            return self._channels.get(channel_id)
    
    async def get_channel_by_name(self, room_id: str, name: str) -> Optional[Channel]:
        """Get channel by name within a room.
        
        Args:
            room_id: Room ID
            name: Channel name to lookup
            
        Returns:
            Channel or None if not found
        """
        async with self._lock:
            channel_key = (room_id, name)
            channel_id = self._channel_names.get(channel_key)
            if channel_id:
                return self._channels.get(channel_id)
            return None
    
    async def list_channels(self, room_id: Optional[str] = None) -> List[Channel]:
        """List all channels, optionally filtered by room.
        
        Args:
            room_id: Room ID to filter by (None for all channels)
            
        Returns:
            List of channels
        """
        async with self._lock:
            channels = list(self._channels.values())
            
            if room_id:
                channels = [ch for ch in channels if ch.room and ch.room.room_id == room_id]
            
            return channels
    
    async def channel_exists(self, channel_id: str) -> bool:
        """Check if channel exists.
        
        Args:
            channel_id: Channel ID to check
            
        Returns:
            True if channel exists
        """
        async with self._lock:
            return channel_id in self._channels
    
    async def join_channel(self, client_id: str, channel_id: str) -> bool:
        """Add client to a channel.
        
        Args:
            client_id: Client to add
            channel_id: Channel to join
            
        Returns:
            True if client was added successfully
        """
        async with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return False
            
            # Add to client membership
            if client_id not in self._client_channels:
                self._client_channels[client_id] = set()
            
            self._client_channels[client_id].add(channel_id)
            
            # Add to channel
            channel.add_member(client_id)
            
            # Update statistics
            self._stats["total_members"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            logger.info(f"Client {client_id} joined channel {channel_id}")
            return True
    
    async def leave_channel(self, client_id: str, channel_id: str) -> bool:
        """Remove client from a channel.
        
        Args:
            client_id: Client to remove
            channel_id: Channel to leave
            
        Returns:
            True if client was removed successfully
        """
        async with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return False
            
            # Remove from client membership
            if client_id in self._client_channels:
                self._client_channels[client_id].discard(channel_id)
                
                # Clean up empty client entry
                if not self._client_channels[client_id]:
                    del self._client_channels[client_id]
            
            # Remove from channel
            removed = channel.remove_member(client_id)
            
            # Update statistics
            if removed:
                self._stats["total_members"] = max(0, self._stats["total_members"] - 1)
                self._stats["last_activity"] = datetime.utcnow()
                logger.info(f"Client {client_id} left channel {channel_id}")
            
            return removed
    
    async def get_client_channels(self, client_id: str) -> Set[str]:
        """Get all channels a client is a member of.
        
        Args:
            client_id: Client ID to lookup
            
        Returns:
            Set of channel IDs the client is in
        """
        async with self._lock:
            return self._client_channels.get(client_id, set())
    
    async def broadcast_to_channel(
        self,
        message: Envelope,
        channel_id: str,
        exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all members of a channel.
        
        Args:
            message: Message to broadcast
            channel_id: Target channel ID
            exclude_client_id: Client ID to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        async with self._lock:
            channel = self._channels.get(channel_id)
            if not channel:
                return 0
            
            sent_count = channel.broadcast_to_channel(message, exclude_client_id)
            self._stats["total_messages"] += sent_count
            self._stats["last_activity"] = datetime.utcnow()
            return sent_count
    
    async def get_channel_stats(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific channel.
        
        Args:
            channel_id: Channel ID to get stats for
            
        Returns:
            Channel statistics dictionary or None if channel not found
        """
        async with self._lock:
            channel = self._channels.get(channel_id)
            if channel:
                return channel.get_stats()
            return None
    
    async def get_room_channels(self, room_id: str) -> List[Channel]:
        """Get all channels in a specific room.
        
        Args:
            room_id: Room ID to get channels for
            
        Returns:
            List of channels in the room
        """
        async with self._lock:
            return [ch for ch in self._channels.values() 
                   if ch.room and ch.room.room_id == room_id]
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive channel manager statistics.
        
        Returns:
            Dictionary of all channel manager statistics
        """
        async with self._lock:
            channel_list = list(self._channels.values())
            
            # Calculate activity statistics
            now = datetime.utcnow()
            active_channels = sum(1 for channel in channel_list 
                                if (now - channel.last_activity).total_seconds() < 3600)  # Active within 1 hour
            
            inactive_channels = len(channel_list) - active_channels
            
            # Room-specific statistics
            rooms_stats = {}
            for channel in channel_list:
                if channel.room:
                    room_id = channel.room.room_id
                    if room_id not in rooms_stats:
                        rooms_stats[room_id] = {
                            "channels": 0,
                            "total_members": 0,
                            "total_messages": 0
                        }
                    
                    rooms_stats[room_id]["channels"] += 1
                    rooms_stats[room_id]["total_members"] += channel.member_count
                    rooms_stats[room_id]["total_messages"] += channel._stats["total_messages"]
            
            return {
                "total_channels": self._stats["total_channels"],
                "total_members": self._stats["total_members"],
                "total_messages": self._stats["total_messages"],
                "active_channels": active_channels,
                "inactive_channels": inactive_channels,
                "total_client_memberships": len(self._client_channels),
                "created_at": self._stats["created_at"].isoformat(),
                "last_activity": self._stats["last_activity"].isoformat(),
                "rooms": rooms_stats,
                "timestamp": datetime.utcnow()
            }
    
    async def cleanup_inactive_channels(self, hours: int = 24) -> int:
        """Clean up inactive channels with no members.
        
        Args:
            hours: Number of hours of inactivity before cleanup
            
        Returns:
            Number of channels cleaned up
        """
        async with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            channels_to_remove = []
            for channel_id, channel in self._channels.items():
                if (channel.last_activity < cutoff_time and 
                    channel.member_count == 0):
                    channels_to_remove.append(channel_id)
            
            for channel_id in channels_to_remove:
                await self.delete_channel(channel_id)
            
            if channels_to_remove:
                logger.info(f"Cleaned up {len(channels_to_remove)} inactive channels")
            
            return len(channels_to_remove)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on channel manager.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_all_stats()
            
            health = {
                "status": "healthy",
                "total_channels": stats["total_channels"],
                "total_members": stats["total_members"],
                "total_messages": stats["total_messages"],
                "active_channels": stats["active_channels"],
                "checks": []
            }
            
            # Check for potential issues
            if stats["total_channels"] > 100000:
                health["checks"].append({"type": "warning", "message": "Very large number of channels"})
            
            if stats["inactive_channels"] > stats["total_channels"] * 0.9:
                health["checks"].append({"type": "warning", "message": "Many inactive channels"})
            
            # Check channel name conflicts
            if len(self._channel_names) != len(self._channels):
                health["checks"].append({"type": "error", "message": "Channel name mapping inconsistent"})
            
            # Check member consistency
            for client_id, channels in self._client_channels.items():
                for channel_id in channels:
                    channel = self._channels.get(channel_id)
                    if channel and not channel.has_member(client_id):
                        health["checks"].append({
                            "type": "error", 
                            "message": f"Member inconsistency for client {client_id} in channel {channel_id}"
                        })
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }