"""Redis Streams storage backend for ArqonBus.

This module provides a Redis-based storage backend using Redis Streams
for scalable message persistence and history retrieval.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    import types
    import sys

    redis = types.SimpleNamespace()
    redis.Redis = object
    redis.asyncio = types.SimpleNamespace(from_url=lambda *args, **kwargs: None)
    sys.modules.setdefault("redis", redis)
    sys.modules.setdefault("redis.asyncio", redis.asyncio)
    REDIS_AVAILABLE = False

from ..protocol.envelope import Envelope
from ..utils.logging import get_logger
from .interface import StorageBackend, StorageResult, HistoryEntry
from .memory import MemoryStorageBackend

logger = get_logger(__name__)


class RedisStreamsStorage(StorageBackend):
    """Redis Streams-based storage backend for ArqonBus.
    
    Provides scalable message persistence with Redis Streams for efficient
    history retrieval and message ordering. Gracefully degrades to memory
    storage when Redis is unavailable.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        redis_client: Optional[Any] = None,
        redis_url: str = "redis://localhost:6379/0",
        storage_mode: str = "degraded",
        stream_prefix: str = "arqonbus",
        history_limit: int = 1000,
        key_ttl: int = 3600,
        fallback_storage: Optional[MemoryStorageBackend] = None,
        **kwargs,
    ):
        """Initialize Redis Streams storage backend.
        
        Args:
            max_size: Maximum number of messages to keep (for compatibility)
            redis_client: Optional pre-configured Redis client
            redis_url: Redis connection URL
            storage_mode: degraded|strict storage behavior
            stream_prefix: Prefix for Redis Stream keys
            history_limit: Maximum number of messages to keep in history
            key_ttl: Time-to-live for stream keys in seconds
            fallback_storage: Fallback memory storage for Redis failures
        """
        self.max_size = max_size
        self.redis_client = redis_client if REDIS_AVAILABLE else None
        self.redis_url = redis_url
        self.storage_mode = storage_mode
        self.strict_mode = storage_mode == "strict"
        self.stream_prefix = stream_prefix
        self.history_limit = history_limit
        self.key_ttl = key_ttl
        fallback_max_size = kwargs.get("max_size", max_size)
        self.fallback_storage = fallback_storage or MemoryStorageBackend(max_size=fallback_max_size)
        
        # Connection pool settings
        self._connection_pool = None
        self._max_connections = 10
        self._retry_attempts = 3
        self._retry_delay = 1.0
        
        # Statistics
        self._stats = {
            "redis_operations": 0,
            "fallback_operations": 0,
            "connection_failures": 0,
            "last_redis_error": None,
            "degraded_mode_active": self.redis_client is None,
        }
    
    async def connect(self):
        """Connect to Redis."""
        if self.redis_client:
            return

        try:
            # Configure connection pool
            kwargs = {
                "encoding": "utf-8",
                "decode_responses": True, # For string handling
                "socket_timeout": 5.0,
                "socket_connect_timeout": 5.0,
                "retry_on_timeout": True,
                "health_check_interval": 30
            }
            
            # Create Redis client
            self.redis_client = redis.from_url(self.redis_url, **kwargs)
            
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis Streams at {self.redis_url}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis at {self.redis_url}: {e}")
            self._stats["connection_failures"] += 1
            self._stats["last_redis_error"] = str(e)
            # We remain in fallback mode (redis_client is None)

    @classmethod
    async def create(cls, config: Dict[str, Any]) -> "RedisStreamsStorage":
        """Create Redis Streams storage backend with configuration.
        
        Args:
            config: Configuration dictionary with Redis settings
            
        Returns:
            RedisStreamsStorage instance with fallback to memory storage
            
        Raises:
            Exception: If Redis connection fails and no fallback configured
        """
        redis_url = config.get("redis_url", "redis://localhost:6379/0")
        storage_mode = config.get("storage_mode", "degraded")
        stream_prefix = config.get("stream_prefix", "arqonbus")
        history_limit = config.get("history_limit", 1000)
        key_ttl = config.get("key_ttl", 3600)
        max_size = config.get("max_size", 1000)
        
        # Create fallback memory storage
        fallback_storage = MemoryStorageBackend(max_size=max_size)
        
        # Attempt to create Redis client
        redis_client = None
        try:
            if not REDIS_AVAILABLE:
                if storage_mode == "strict":
                    raise RuntimeError("Redis dependency is unavailable in strict storage mode")
                logger.warning("Redis not available, falling back to memory storage")
                return cls(
                    max_size=max_size,
                    redis_client=None,
                    redis_url=redis_url,
                    storage_mode=storage_mode,
                    stream_prefix=stream_prefix,
                    history_limit=history_limit,
                    key_ttl=key_ttl,
                    fallback_storage=fallback_storage
                )
            
            redis_client = redis.from_url(
                redis_url,
                max_connections=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await redis_client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            if storage_mode == "strict":
                raise RuntimeError(
                    f"Redis connection failed in strict storage mode: {e}"
                ) from e
            logger.info("Falling back to memory storage")
            
            # Return with failed connection, use fallback
            return cls(
                max_size=max_size,
                redis_client=None,
                redis_url=redis_url,
                storage_mode=storage_mode,
                stream_prefix=stream_prefix,
                history_limit=history_limit,
                key_ttl=key_ttl,
                fallback_storage=fallback_storage
            )
        
        return cls(
            max_size=max_size,
            redis_client=redis_client,
            redis_url=redis_url,
            storage_mode=storage_mode,
            stream_prefix=stream_prefix,
            history_limit=history_limit,
            key_ttl=key_ttl,
            fallback_storage=fallback_storage
        )

    async def _handle_redis_failure(self, error: Exception) -> None:
        self._stats["connection_failures"] += 1
        self._stats["last_redis_error"] = str(error)
        self._stats["degraded_mode_active"] = True
        if self.strict_mode:
            raise RuntimeError(
                f"Redis operation failed in strict storage mode: {error}"
            ) from error
    
    async def append(self, envelope: Envelope, **kwargs) -> StorageResult:
        """Append message to Redis Streams.
        
        Args:
            envelope: Message envelope to store
            **kwargs: Additional parameters (ignored for Redis)
            
        Returns:
            StorageResult indicating success/failure
        """
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope, **kwargs)
        
        try:
            self._stats["redis_operations"] += 1
            
            # Prepare message data for Redis Streams
            message_data = {
                "id": envelope.id,
                "type": envelope.type,
                "timestamp": envelope.timestamp.isoformat() if isinstance(envelope.timestamp, datetime) else str(envelope.timestamp),
                "sender": envelope.sender or "",
                "room": envelope.room or "",
                "channel": envelope.channel or "",
                "payload": json.dumps(envelope.payload) if envelope.payload else "{}"
            }
            
            # Main message stream
            main_stream = f"{self.stream_prefix}:messages"
            await self.redis_client.xadd(main_stream, message_data)
            
            # Sender-specific streams for history
            if envelope.sender:
                sender_stream = f"{self.stream_prefix}:sender_{envelope.sender}"
                await self.redis_client.xadd(sender_stream, message_data)
            
            # Room/channel streams if applicable
            if envelope.room:
                room_stream = f"{self.stream_prefix}:room_{envelope.room}"
                await self.redis_client.xadd(room_stream, message_data)
            
            if envelope.channel:
                channel_stream = f"{self.stream_prefix}:channel_{envelope.channel}"
                await self.redis_client.xadd(channel_stream, message_data)
            
            # Set TTL on streams for cleanup
            await self.redis_client.expire(main_stream, self.key_ttl)
            if envelope.sender:
                await self.redis_client.expire(sender_stream, self.key_ttl)
            if envelope.room:
                await self.redis_client.expire(room_stream, self.key_ttl)
            if envelope.channel:
                await self.redis_client.expire(channel_stream, self.key_ttl)
            
            logger.debug(f"Stored message {envelope.id} in Redis Streams")
            return StorageResult(
                success=True,
                message_id=envelope.id,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Redis storage error: {e}")
            await self._handle_redis_failure(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope, **kwargs)
    
    async def get_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[HistoryEntry]:
        """Retrieve message history from Redis Streams.
        
        Args:
            room: Room ID to get history for
            channel: Channel ID to get history for
            limit: Maximum number of messages to retrieve
            since: Only return messages after this time
            until: Only return messages before this time
            
        Returns:
            List of history entries in chronological order
        """
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(room, channel, limit, since, until)
        
        try:
            self._stats["redis_operations"] += 1
            
            # Determine which stream to query
            if room and channel:
                stream_name = f"{self.stream_prefix}:room_{room}_channel_{channel}"
            elif room:
                stream_name = f"{self.stream_prefix}:room_{room}"
            elif channel:
                stream_name = f"{self.stream_prefix}:channel_{channel}"
            else:
                stream_name = f"{self.stream_prefix}:messages"
            
            # Query Redis Streams with limit
            messages = await self.redis_client.xrange(
                stream_name,
                count=min(limit, self.history_limit)
            )
            
            # Convert Redis Stream messages to HistoryEntry objects
            history_entries = []
            for msg_id, msg_data in messages:
                try:
                    # Parse timestamp
                    timestamp_str = msg_data.get("timestamp", "")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except ValueError:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()
                    
                    # Skip if outside time range
                    if since and timestamp <= since:
                        continue
                    if until and timestamp >= until:
                        continue
                    
                    envelope = Envelope(
                        id=msg_data.get("id", ""),
                        type=msg_data.get("type", ""),
                        timestamp=timestamp,
                        sender=msg_data.get("sender") or None,
                        room=msg_data.get("room") or None,
                        channel=msg_data.get("channel") or None,
                        payload=json.loads(msg_data.get("payload", "{}"))
                    )
                    
                    history_entry = HistoryEntry(
                        envelope=envelope,
                        stored_at=timestamp,
                        storage_metadata={"backend": "redis_streams", "stream": stream_name}
                    )
                    history_entries.append(history_entry)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse message {msg_id}: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(history_entries)} messages from {stream_name}")
            return history_entries[:limit]
            
        except Exception as e:
            logger.error(f"Redis history retrieval error: {e}")
            await self._handle_redis_failure(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(room, channel, limit, since, until)
    
    async def delete_message(self, message_id: str) -> StorageResult:
        """Delete a specific message by ID.
        
        Args:
            message_id: ID of message to delete
            
        Returns:
            StorageResult indicating success/failure
        """
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.delete_message(message_id)
        
        try:
            self._stats["redis_operations"] += 1
            
            # Note: Redis Streams doesn't support direct deletion by message ID
            # We would need to use XDEL with specific stream IDs, but we don't have those
            # For now, fall back to memory storage for deletion operations
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.delete_message(message_id)
            
        except Exception as e:
            logger.error(f"Redis delete message error: {e}")
            await self._handle_redis_failure(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.delete_message(message_id)
    
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
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.clear_history(room, channel, before)
        
        try:
            self._stats["redis_operations"] += 1
            
            # For Redis Streams, we can't easily clear by time range
            # Fallback to memory storage for complex operations
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.clear_history(room, channel, before)
            
        except Exception as e:
            logger.error(f"Redis clear history error: {e}")
            await self._handle_redis_failure(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.clear_history(room, channel, before)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary of storage statistics
        """
        base_stats = {
            "backend_type": "redis_streams",
            "storage_mode": self.storage_mode,
            "redis_available": self.redis_client is not None,
            "configuration": {
                "redis_url": self.redis_url,
                "stream_prefix": self.stream_prefix,
                "history_limit": self.history_limit,
                "key_ttl": self.key_ttl,
                "max_size": self.max_size
            },
            "stats": self._stats.copy()
        }
        
        if self.redis_client:
            try:
                # Get Redis-specific stats
                info = await self.redis_client.info()
                base_stats["redis_info"] = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
                
                # Count active streams
                pattern = f"{self.stream_prefix}:*"
                stream_keys = await self.redis_client.keys(pattern)
                base_stats["stream_stats"] = {
                    "total_streams": len(stream_keys),
                    "stream_names": [key.decode() for key in stream_keys[:10]]  # First 10
                }
                
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
                base_stats["redis_info_error"] = str(e)
        
        return base_stats
    
    async def health_check(self) -> bool:
        """Check if storage backend is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.redis_client:
                # Check Redis connection
                await self.redis_client.ping()
                return True
            else:
                # Check fallback storage
                return await self.fallback_storage.health_check()
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
        
        # Close fallback storage
        if self.fallback_storage:
            await self.fallback_storage.close()

    # --- Extended Consumer Group API ---

    async def ensure_group(self, stream: str, group: str):
        """Ensure a consumer group exists for a stream."""
        if not self.redis_client:
            raise NotImplementedError("Consumer groups not supported in fallback mode")
        
        try:
            await self.redis_client.xgroup_create(stream, group, id='0', mkstream=True)
            logger.info(f"Created consumer group '{group}' for stream '{stream}'")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create consumer group: {e}")
                raise

    async def read_group(self, stream: str, group: str, consumer: str, count: int = 1, block_ms: int = 5000) -> List[Any]:
        """Read messages from a consumer group."""
        if not self.redis_client:
            raise NotImplementedError("Consumer groups not supported in fallback mode")
        
        # xreadgroup returns: [[stream, [ (id, data), ... ]]]
        # xreadgroup returns: [[stream, [ (id, data), ... ]]]
        res = await self.redis_client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: '>'},
            count=count,
            block=block_ms
        )
        
        if not res:
            return []

        # Decode results if they are bytes
        decoded_res = []
        for stream_name, messages in res:
            decoded_messages = []
            for msg_id, data in messages:
                # Decode ID
                if isinstance(msg_id, bytes):
                    msg_id = msg_id.decode()
                
                # Decode data dict
                decoded_data = {}
                for k, v in data.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    # Try to parse as JSON if it looks like it
                    if isinstance(v_str, str) and (v_str.startswith("{") or v_str.startswith("[")):
                        try:
                            v_str = json.loads(v_str)
                        except json.JSONDecodeError as exc:
                            logger.debug(
                                "Failed to decode Redis stream field '%s' as JSON: %s",
                                k_str,
                                exc,
                            )
                    decoded_data[k_str] = v_str
                
                decoded_messages.append((msg_id, decoded_data))
            
            s_name = stream_name.decode() if isinstance(stream_name, bytes) else stream_name
            decoded_res.append((s_name, decoded_messages))
            
        return decoded_res

    async def ack(self, stream: str, group: str, *message_ids: str):
        """Acknowledge messages in a consumer group."""
        if not self.redis_client:
            raise NotImplementedError("Consumer groups not supported in fallback mode")
        
        if message_ids:
            await self.redis_client.xack(stream, group, *message_ids)

    async def pending(self, stream: str, group: str) -> List[Any]:
        """Get pending messages in a consumer group."""
        if not self.redis_client:
            raise NotImplementedError("Consumer groups not supported in fallback mode")
        
        # Returns a summary and a list of pending entries
        return await self.redis_client.xpending_range(
            stream, group, min='-', max='+', count=100
        )

    async def claim(self, stream: str, group: str, consumer: str, min_idle_ms: int, *message_ids: str) -> List[Any]:
        """Claim stale messages in a consumer group."""
        if not self.redis_client:
            raise NotImplementedError("Consumer groups not supported in fallback mode")
        
        if not message_ids:
            return []
            
        return await self.redis_client.xclaim(
            stream, group, consumer, min_idle_ms, *message_ids
        )


# Export factory function for backward compatibility
async def create_redis_storage(config: Dict[str, Any]) -> StorageBackend:
    """Create Redis storage backend from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        StorageBackend instance (Redis or fallback)
    """
    return await RedisStreamsStorage.create(config)
