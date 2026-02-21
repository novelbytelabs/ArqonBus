"""In-memory storage backend for ArqonBus."""
import asyncio
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timedelta, timezone
import threading
import logging

from .interface import StorageBackend, StorageResult, HistoryEntry
from ..protocol.envelope import Envelope


logger = logging.getLogger(__name__)



class MemoryStorageBackend(StorageBackend):
    """In-memory storage backend using thread-safe collections.
    
    This backend stores all messages in memory using deques and dictionaries.
    Messages are kept in memory only and are lost when the server restarts.
    Perfect for development, testing, or when persistence is not required.
    """
    
    def __init__(self, max_size: int = 10000):
        """Initialize memory storage backend.
        
        Args:
            max_size: Maximum number of messages to keep in memory
        """
        self.max_size = max_size
        self._lock = threading.RLock()
        
        # Storage for messages by room/channel
        # {room: {channel: deque([HistoryEntry, ...])}}
        self._messages = defaultdict(lambda: defaultdict(deque))
        
        # Index for fast lookup by message ID
        # {message_id: (room, channel, HistoryEntry)}
        self._message_index = {}
        
        # Statistics
        now = datetime.now(timezone.utc)
        self._stats = {
            "total_messages": 0,
            "messages_by_room": defaultdict(int),
            "messages_by_channel": defaultdict(lambda: defaultdict(int)),
            "storage_backend": "memory",
            "max_size": max_size,
            "created_at": now,
            "last_accessed": now
        }

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    async def append(self, envelope: Envelope, **kwargs) -> StorageResult:
        """Append a message to memory storage.
        
        Args:
            envelope: Message envelope to store
            **kwargs: Additional parameters (ignored for memory storage)
            
        Returns:
            StorageResult indicating success/failure
        """
        try:
            with self._lock:
                room = envelope.room or "default"
                channel = envelope.channel or "default"
                
                # Create history entry
                entry = HistoryEntry(
                    envelope=envelope,
                    stored_at=datetime.now(timezone.utc),
                    storage_metadata={"backend": "memory", "size": self.max_size}
                )
                
                # Add to storage
                room_messages = self._messages[room][channel]
                room_messages.append(entry)
                
                # Maintain size limit
                while len(room_messages) > self.max_size:
                    old_entry = room_messages.popleft()
                    if old_entry.envelope.id in self._message_index:
                        del self._message_index[old_entry.envelope.id]
                
                # Update index
                self._message_index[envelope.id] = (room, channel, entry)
                
                # Update statistics
                self._stats["total_messages"] += 1
                self._stats["messages_by_room"][room] += 1
                self._stats["messages_by_channel"][room][channel] += 1
                self._stats["last_accessed"] = datetime.now(timezone.utc)
                
                logger.debug(f"Stored message {envelope.id} in room '{room}', channel '{channel}'")
                
                return StorageResult(
                    success=True,
                    message_id=envelope.id,
                    timestamp=entry.stored_at
                )
                
        except Exception as e:
            logger.error(f"Failed to store message {envelope.id}: {e}")
            return StorageResult(
                success=False,
                message_id=envelope.id,
                error_message=str(e)
            )
    
    async def get_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Get message history from memory storage.
        
        Args:
            room: Room to get history for (None for all rooms)
            channel: Channel to get history for (None for all channels)
            limit: Maximum number of messages to return
            since: Only return messages after this time
            until: Only return messages before this time
            
        Returns:
            List of history entries, most recent first
        """
        try:
            with self._lock:
                results = []
                
                if room is None:
                    # Get history from all rooms
                    rooms_to_search = list(self._messages.keys())
                else:
                    rooms_to_search = [room]
                
                since_utc = self._as_utc(since) if since else None
                until_utc = self._as_utc(until) if until else None

                for current_room in rooms_to_search:
                    if room is not None and current_room != room:
                        continue
                        
                    channels_to_search = list(self._messages[current_room].keys())
                    
                    for current_channel in channels_to_search:
                        if channel is not None and current_channel != channel:
                            continue
                            
                        # Get messages for this room/channel
                        messages = self._messages[current_room][current_channel]
                        
                        # Filter by time range if specified
                        for entry in reversed(messages):  # Most recent first
                            entry_time = self._as_utc(entry.stored_at)
                            # Check time range
                            if since_utc and entry_time <= since_utc:
                                continue
                            if until_utc and entry_time >= until_utc:
                                continue
                                
                            results.append(entry)
                            
                            if len(results) >= limit:
                                break
                                
                        if len(results) >= limit:
                            break
                            
                    if len(results) >= limit:
                        break
                        
                # Update statistics
                self._stats["last_accessed"] = datetime.now(timezone.utc)
                
                logger.debug(f"Retrieved {len(results)} messages (limit: {limit})")
                return results[:limit]
                
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")
            return []
    
    async def delete_message(self, message_id: str) -> StorageResult:
        """Delete a message from memory storage.
        
        Args:
            message_id: ID of message to delete
            
        Returns:
            StorageResult indicating success/failure
        """
        try:
            with self._lock:
                if message_id not in self._message_index:
                    return StorageResult(
                        success=False,
                        message_id=message_id,
                        error_message="Message not found"
                    )
                
                room, channel, entry = self._message_index[message_id]
                
                # Remove from deque
                room_messages = self._messages[room][channel]
                try:
                    room_messages.remove(entry)
                except ValueError:
                    pass  # Already removed
                
                # Remove from index
                del self._message_index[message_id]
                
                # Update statistics
                self._stats["total_messages"] -= 1
                self._stats["messages_by_room"][room] -= 1
                self._stats["messages_by_channel"][room][channel] -= 1
                self._stats["last_accessed"] = datetime.now(timezone.utc)
                
                logger.debug(f"Deleted message {message_id}")
                
                return StorageResult(
                    success=True,
                    message_id=message_id,
                    timestamp=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return StorageResult(
                success=False,
                message_id=message_id,
                error_message=str(e)
            )
    
    async def clear_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        before: Optional[datetime] = None
    ) -> StorageResult:
        """Clear message history from memory storage.
        
        Args:
            room: Room to clear (None for all rooms)
            channel: Channel to clear (None for all channels)
            before: Only clear messages before this time
            
        Returns:
            StorageResult indicating success/failure
        """
        try:
            with self._lock:
                cleared_count = 0
                current_time = datetime.now(timezone.utc)
                
                if room is None:
                    # Clear all rooms
                    rooms_to_clear = list(self._messages.keys())
                else:
                    rooms_to_clear = [room]
                
                for current_room in rooms_to_clear:
                    if room is not None and current_room != room:
                        continue
                        
                    if channel is None:
                        # Clear all channels in this room
                        channels_to_clear = list(self._messages[current_room].keys())
                    else:
                        channels_to_clear = [channel]
                    
                    for current_channel in channels_to_clear:
                        if channel is not None and current_channel != channel:
                            continue
                            
                        messages = self._messages[current_room][current_channel]
                        
                        # Filter messages to keep
                        kept_messages = deque()
                        if before:
                            before_utc = self._as_utc(before)
                            for entry in messages:
                                if self._as_utc(entry.stored_at) < before_utc:
                                    # Remove from index
                                    if entry.envelope.id in self._message_index:
                                        del self._message_index[entry.envelope.id]
                                    cleared_count += 1
                                else:
                                    kept_messages.append(entry)
                        else:
                            # Clear all messages
                            for entry in messages:
                                if entry.envelope.id in self._message_index:
                                    del self._message_index[entry.envelope.id]
                                cleared_count += 1
                        
                        # Replace with kept messages
                        self._messages[current_room][current_channel] = kept_messages
                        
                        # Update statistics
                        if not kept_messages:
                            # Remove empty channel
                            del self._messages[current_room][current_channel]
                
                # Update global statistics
                self._stats["total_messages"] -= cleared_count
                self._stats["last_accessed"] = current_time
                
                # Recalculate room/channel statistics
                self._stats["messages_by_room"].clear()
                self._stats["messages_by_channel"].clear()
                
                for room_name, channels in self._messages.items():
                    room_count = 0
                    for channel_name, messages in channels.items():
                        channel_count = len(messages)
                        room_count += channel_count
                        self._stats["messages_by_channel"][room_name][channel_name] = channel_count
                    self._stats["messages_by_room"][room_name] = room_count
                
                logger.info(f"Cleared {cleared_count} messages")
                
                return StorageResult(
                    success=True,
                    metadata={"cleared_count": cleared_count}
                )
                
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return StorageResult(
                success=False,
                error_message=str(e)
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary of storage statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats["current_memory_usage"] = {
                "total_messages": len(self._message_index),
                "rooms": len(self._messages),
                "channels": sum(len(channels) for channels in self._messages.values())
            }
            stats["memory_efficiency"] = {
                "utilization": len(self._message_index) / self.max_size if self.max_size > 0 else 0,
                "messages_per_room": {room: count for room, count in stats["messages_by_room"].items()},
                "messages_per_channel": {room: dict(channels) for room, channels in stats["messages_by_channel"].items()}
            }
            stats["last_updated"] = datetime.now(timezone.utc)
            return stats
    
    async def health_check(self) -> bool:
        """Check if memory storage is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            with self._lock:
                # Basic health checks
                if self._stats["total_messages"] < 0:
                    return False
                    
                # Check if we can still store messages
                return len(self._message_index) <= self.max_size
                
        except Exception:
            return False
    
    async def close(self):
        """Close memory storage (no-op for in-memory storage)."""
        try:
            with self._lock:
                # Clear all data
                self._messages.clear()
                self._message_index.clear()
                
                # Reset statistics
                now = datetime.now(timezone.utc)
                self._stats = {
                    "total_messages": 0,
                    "messages_by_room": defaultdict(int),
                    "messages_by_channel": defaultdict(lambda: defaultdict(int)),
                    "storage_backend": "memory",
                    "max_size": self.max_size,
                    "created_at": now,
                    "last_accessed": now,
                    "closed_at": now
                }
                
                logger.info("Memory storage backend closed")
                
        except Exception as e:
            logger.error(f"Error closing memory storage: {e}")
    
    async def compact(self) -> StorageResult:
        """Compact memory storage by removing old messages.
        
        Args:
            retention_hours: How many hours of messages to keep
            
        Returns:
            StorageResult indicating success/failure
        """
        try:
            with self._lock:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)  # Keep last 24 hours
                
                cleared_count = await self.clear_history(before=cutoff_time)
                
                return StorageResult(
                    success=cleared_count.success,
                    metadata={"compacted_messages": cleared_count.metadata.get("cleared_count", 0)}
                )
                
        except Exception as e:
            logger.error(f"Failed to compact memory storage: {e}")
            return StorageResult(
                success=False,
                error_message=str(e)
            )

# Backward compatibility alias expected by other modules/tests
MemoryStorage = MemoryStorageBackend
