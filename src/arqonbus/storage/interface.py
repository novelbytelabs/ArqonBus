"""Storage backend interface for ArqonBus."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from dataclasses import dataclass

from ..protocol.envelope import Envelope


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    message_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass 
class HistoryEntry:
    """Entry from message history."""
    envelope: Envelope
    stored_at: datetime
    storage_metadata: Dict[str, Any] = None


class StorageBackend(ABC):
    """Abstract base class for all storage backends."""
    
    @abstractmethod
    async def append(self, envelope: Envelope, **kwargs) -> StorageResult:
        """Append a message to storage.
        
        Args:
            envelope: Message envelope to store
            **kwargs: Additional storage-specific parameters
            
        Returns:
            StorageResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def get_history(
        self, 
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Get message history for room/channel.
        
        Args:
            room: Room to get history for (None for all rooms)
            channel: Channel to get history for (None for all channels)
            limit: Maximum number of messages to return
            since: Only return messages after this time
            until: Only return messages before this time
            
        Returns:
            List of history entries, most recent first
        """
        pass
    
    @abstractmethod
    async def delete_message(self, message_id: str) -> StorageResult:
        """Delete a specific message by ID.
        
        Args:
            message_id: ID of message to delete
            
        Returns:
            StorageResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def clear_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> StorageResult:
        """Clear message history.
        
        Args:
            room: Room to clear (None for all rooms)
            channel: Channel to clear (None for all channels)
            before: Only clear messages before this time
            
        Returns:
            StorageResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary of storage statistics
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage backend is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Close storage connection and cleanup resources."""
        pass


class MessageStorage:
    """High-level message storage interface."""
    
    def __init__(self, backend: StorageBackend):
        """Initialize message storage with backend.
        
        Args:
            backend: Storage backend to use
        """
        self.backend = backend
    
    async def store_message(
        self,
        envelope: Envelope,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        **kwargs
    ) -> StorageResult:
        """Store a message.
        
        Args:
            envelope: Message envelope to store
            room: Room for routing info (overrides envelope.room)
            channel: Channel for routing info (overrides envelope.channel)
            **kwargs: Additional storage parameters
            
        Returns:
            StorageResult indicating success/failure
        """
        # Update envelope with routing info if provided
        if room and not envelope.room:
            envelope.room = room
        if channel and not envelope.channel:
            envelope.channel = channel
            
        return await self.backend.append(envelope, **kwargs)
    
    async def get_room_history(
        self,
        room: str,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Get message history for a specific room.
        
        Args:
            room: Room to get history for
            channel: Specific channel within room (None for all channels)
            limit: Maximum number of messages
            since: Only return messages after this time
            
        Returns:
            List of history entries
        """
        return await self.backend.get_history(
            room=room,
            channel=channel,
            limit=limit,
            since=since
        )
    
    async def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Get message history for a specific channel.
        
        Args:
            channel: Channel to get history for
            limit: Maximum number of messages
            since: Only return messages after this time
            
        Returns:
            List of history entries
        """
        return await self.backend.get_history(
            channel=channel,
            limit=limit,
            since=since
        )
    
    async def get_global_history(
        self,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Get global message history across all rooms/channels.
        
        Args:
            limit: Maximum number of messages
            since: Only return messages after this time
            
        Returns:
            List of history entries
        """
        return await self.backend.get_history(limit=limit, since=since)
    
    async def search_messages(
        self,
        query: str,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100
    ) -> List[HistoryEntry]:
        """Search message history for specific content.
        
        Args:
            query: Search query (implementation dependent)
            room: Room to search in (None for all rooms)
            channel: Channel to search in (None for all channels)
            limit: Maximum number of results
            
        Returns:
            List of matching history entries
        """
        # Default implementation - subclasses may override with more sophisticated search
        history = await self.backend.get_history(
            room=room,
            channel=channel,
            limit=limit * 2  # Get more results to filter
        )
        
        # Simple text search in message payload
        results = []
        for entry in history:
            if self._message_matches_query(entry.envelope, query):
                results.append(entry)
            if len(results) >= limit:
                break
                
        return results
    
    def _message_matches_query(self, envelope: Envelope, query: str) -> bool:
        """Check if envelope matches search query.
        
        Args:
            envelope: Message envelope to check
            query: Search query
            
        Returns:
            True if message matches query
        """
        query = query.lower()
        
        # Search in payload
        if envelope.payload:
            payload_text = str(envelope.payload).lower()
            if query in payload_text:
                return True
        
        # Search in command/args
        if envelope.command and query in envelope.command.lower():
            return True
            
        if envelope.args:
            args_text = str(envelope.args).lower()
            if query in args_text:
                return True
        
        return False
    
    async def delete_message(self, message_id: str) -> StorageResult:
        """Delete a specific message.
        
        Args:
            message_id: ID of message to delete
            
        Returns:
            StorageResult indicating success/failure
        """
        return await self.backend.delete_message(message_id)
    
    async def clear_room_history(
        self,
        room: str,
        channel: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> StorageResult:
        """Clear history for a specific room.
        
        Args:
            room: Room to clear
            channel: Channel within room (None for all channels)
            before: Only clear messages before this time
            
        Returns:
            StorageResult indicating success/failure
        """
        return await self.backend.clear_history(room=room, channel=channel, before=before)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary of storage statistics
        """
        return await self.backend.get_stats()
    
    async def is_healthy(self) -> bool:
        """Check if storage backend is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return await self.backend.health_check()
    
    async def close(self):
        """Close storage connection."""
        await self.backend.close()


# Storage registry for different backends
class StorageRegistry:
    """Registry for available storage backends."""
    
    _backends: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, backend_class: type):
        """Register a storage backend class.
        
        Args:
            name: Backend name (e.g., 'memory', 'redis')
            backend_class: StorageBackend subclass
        """
        cls._backends[name] = backend_class
    
    @classmethod
    def get_backend_class(cls, name: str) -> Optional[type]:
        """Get registered backend class by name.
        
        Args:
            name: Backend name
            
        Returns:
            Backend class or None if not found
        """
        return cls._backends.get(name)
    
    @classmethod
    def list_backends(cls) -> List[str]:
        """List all registered backend names.
        
        Returns:
            List of backend names
        """
        return list(cls._backends.keys())
    
    @classmethod
    async def create_backend(cls, name: str, **kwargs) -> StorageBackend:
        """Create a storage backend instance.
        
        Args:
            name: Backend name
            **kwargs: Arguments to pass to backend constructor
            
        Returns:
            StorageBackend instance
            
        Raises:
            ValueError: If backend name not found
        """
        backend_class = cls.get_backend_class(name)
        if backend_class is None:
            available = ", ".join(cls.list_backends())
            raise ValueError(f"Unknown storage backend '{name}'. Available: {available}")
            
        return backend_class(**kwargs)


# Register built-in backends
# Import backends here to avoid circular imports
try:
    from .memory import MemoryStorageBackend
    from .redis_streams import RedisStreamsStorage
    
    # Register backends
    StorageRegistry.register('memory', MemoryStorageBackend)
    StorageRegistry.register('memory_storage', MemoryStorageBackend)
    StorageRegistry.register('redis', RedisStreamsStorage)
    StorageRegistry.register('redis_streams', RedisStreamsStorage)
    
except ImportError as e:
    # If backends can't be imported, registry will remain empty
    # This allows the interface to be imported without dependencies
    pass