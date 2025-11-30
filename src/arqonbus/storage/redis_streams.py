"""Redis Streams storage backend for ArqonBus.

This module provides a Redis-based storage backend using Redis Streams
for scalable message persistence and history retrieval.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import time

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from ..protocol.envelope import Envelope
from ..utils.logging import get_logger
from .interface import StorageBackend
from .memory import MemoryStorage

logger = get_logger(__name__)


class RedisStreamsStorage(StorageBackend):
    """Redis Streams-based storage backend for ArqonBus.
    
    Provides scalable message persistence with Redis Streams for efficient
    history retrieval and message ordering. Gracefully degrades to memory
    storage when Redis is unavailable.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: str = "redis://localhost:6379/0",
        stream_prefix: str = "arqonbus",
        history_limit: int = 1000,
        key_ttl: int = 3600,
        fallback_storage: Optional[MemoryStorage] = None
    ):
        """Initialize Redis Streams storage backend.
        
        Args:
            redis_client: Optional pre-configured Redis client
            redis_url: Redis connection URL
            stream_prefix: Prefix for Redis Stream keys
            history_limit: Maximum number of messages to keep in history
            key_ttl: Time-to-live for stream keys in seconds
            fallback_storage: Fallback memory storage for Redis failures
        """
        self.redis_client = redis_client
        self.redis_url = redis_url
        self.stream_prefix = stream_prefix
        self.history_limit = history_limit
        self.key_ttl = key_ttl
        self.fallback_storage = fallback_storage
        
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
            "last_redis_error": None
        }
    
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
        stream_prefix = config.get("stream_prefix", "arqonbus")
        history_limit = config.get("history_limit", 1000)
        key_ttl = config.get("key_ttl", 3600)
        
        # Create fallback memory storage
        fallback_storage = MemoryStorage()
        
        # Attempt to create Redis client
        redis_client = None
        try:
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, falling back to memory storage")
                return cls(
                    redis_client=None,
                    redis_url=redis_url,
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
            logger.info("Falling back to memory storage")
            
            # Return with failed connection, use fallback
            return cls(
                redis_client=None,
                redis_url=redis_url,
                stream_prefix=stream_prefix,
                history_limit=history_limit,
                key_ttl=key_ttl,
                fallback_storage=fallback_storage
            )
        
        return cls(
            redis_client=redis_client,
            redis_url=redis_url,
            stream_prefix=stream_prefix,
            history_limit=history_limit,
            key_ttl=key_ttl,
            fallback_storage=fallback_storage
        )
    
    async def append(self, envelope: Envelope) -> str:
        """Append message to Redis Streams.
        
        Args:
            envelope: Message envelope to store
            
        Returns:
            Operation result identifier
        """
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope)
        
        try:
            self._stats["redis_operations"] += 1
            
            # Prepare message data for Redis Streams
            message_data = {
                "id": envelope.id,
                "type": envelope.type,
                "timestamp": envelope.timestamp,
                "from_client": envelope.from_client,
                "to_client": envelope.to_client or "",
                "room": envelope.room or "",
                "channel": envelope.channel or "",
                "payload": json.dumps(envelope.payload) if envelope.payload else "{}"
            }
            
            # Main message stream
            main_stream = f"{self.stream_prefix}:messages"
            await self.redis_client.xadd(main_stream, message_data)
            
            # Client-specific streams for history
            from_client_stream = f"{self.stream_prefix}:client_{envelope.from_client}"
            await self.redis_client.xadd(from_client_stream, message_data)
            
            if envelope.to_client:
                to_client_stream = f"{self.stream_prefix}:client_{envelope.to_client}"
                await self.redis_client.xadd(to_client_stream, message_data)
            
            # Room/channel streams if applicable
            if envelope.room:
                room_stream = f"{self.stream_prefix}:room_{envelope.room}"
                await self.redis_client.xadd(room_stream, message_data)
            
            if envelope.channel:
                channel_stream = f"{self.stream_prefix}:channel_{envelope.channel}"
                await self.redis_client.xadd(channel_stream, message_data)
            
            # Set TTL on streams for cleanup
            await self.redis_client.expire(main_stream, self.key_ttl)
            await self.redis_client.expire(from_client_stream, self.key_ttl)
            if envelope.to_client:
                await self.redis_client.expire(to_client_stream, self.key_ttl)
            if envelope.room:
                await self.redis_client.expire(room_stream, self.key_ttl)
            if envelope.channel:
                await self.redis_client.expire(channel_stream, self.key_ttl)
            
            logger.debug(f"Stored message {envelope.id} in Redis Streams")
            return "stream_success"
            
        except Exception as e:
            logger.error(f"Redis storage error: {e}")
            self._stats["connection_failures"] += 1
            self._stats["last_redis_error"] = str(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope)
    
    async def get_history(
        self,
        client_id: Optional[str] = None,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 50
    ) -> List[Envelope]:
        """Retrieve message history from Redis Streams.
        
        Args:
            client_id: Client ID to get history for
            room: Room ID to get history for
            channel: Channel ID to get history for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message envelopes in chronological order
        """
        # Use fallback storage if Redis unavailable
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(client_id, room, channel, limit)
        
        try:
            self._stats["redis_operations"] += 1
            
            # Determine which stream to query
            if client_id:
                stream_name = f"{self.stream_prefix}:client_{client_id}"
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
            
            # Convert Redis Stream messages to Envelope objects
            envelopes = []
            for msg_id, msg_data in messages:
                try:
                    envelope = Envelope(
                        id=msg_data.get("id", ""),
                        type=msg_data.get("type", ""),
                        timestamp=msg_data.get("timestamp", ""),
                        from_client=msg_data.get("from_client", ""),
                        to_client=msg_data.get("to_client") or None,
                        room=msg_data.get("room") or None,
                        channel=msg_data.get("channel") or None,
                        payload=json.loads(msg_data.get("payload", "{}"))
                    )
                    envelopes.append(envelope)
                except Exception as e:
                    logger.warning(f"Failed to parse message {msg_id}: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(envelopes)} messages from {stream_name}")
            return envelopes
            
        except Exception as e:
            logger.error(f"Redis history retrieval error: {e}")
            self._stats["connection_failures"] += 1
            self._stats["last_redis_error"] = str(e)
            
            # Fallback to memory storage
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(client_id, room, channel, limit)
    
    async def cleanup_streams(self, max_age: Optional[int] = None) -> Dict[str, int]:
        """Clean up old messages from Redis Streams.
        
        Args:
            max_age: Maximum age in seconds for messages (uses instance default if None)
            
        Returns:
            Dictionary with cleanup statistics
        """
        if not self.redis_client:
            self._stats["fallback_operations"] += 1
            return {"cleanup_operations": 0}
        
        max_age = max_age or self.key_ttl
        cutoff_time = int(time.time()) - max_age
        
        try:
            self._stats["redis_operations"] += 1
            
            # Clean up main message stream
            main_stream = f"{self.stream_prefix}:messages"
            await self.redis_client.xtrim(main_stream, min_id=cutoff_time)
            
            # Get all stream keys with our prefix
            pattern = f"{self.stream_prefix}:*"
            stream_keys = await self.redis_client.keys(pattern)
            
            cleaned_streams = 0
            total_trimmed = 0
            
            for stream_key in stream_keys:
                # Trim each stream
                trimmed = await self.redis_client.xtrim(stream_key, min_id=cutoff_time)
                if trimmed > 0:
                    cleaned_streams += 1
                    total_trimmed += trimmed
            
            # Remove empty streams
            for stream_key in stream_keys:
                length = await self.redis_client.xlen(stream_key)
                if length == 0:
                    await self.redis_client.delete(stream_key)
            
            result = {
                "cleaned_streams": cleaned_streams,
                "total_messages_trimmed": total_trimmed,
                "cutoff_time": cutoff_time
            }
            
            logger.info(f"Cleaned up {cleaned_streams} streams, trimmed {total_trimmed} messages")
            return result
            
        except Exception as e:
            logger.error(f"Redis cleanup error: {e}")
            self._stats["connection_failures"] += 1
            self._stats["last_redis_error"] = str(e)
            
            # Fallback does nothing for cleanup
            self._stats["fallback_operations"] += 1
            return {"cleanup_operations": 0}
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage backend statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        base_stats = {
            "backend_type": "redis_streams",
            "redis_available": self.redis_client is not None,
            "configuration": {
                "redis_url": self.redis_url,
                "stream_prefix": self.stream_prefix,
                "history_limit": self.history_limit,
                "key_ttl": self.key_ttl
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
    
    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage backend.
        
        Returns:
            Dictionary with health check results
        """
        health = {
            "status": "healthy",
            "backend": "redis_streams",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Check Redis connection
        if self.redis_client:
            try:
                start_time = time.time()
                await self.redis_client.ping()
                response_time = time.time() - start_time
                
                health["checks"]["redis_connection"] = {
                    "status": "healthy",
                    "response_time_ms": round(response_time * 1000, 2)
                }
                
            except Exception as e:
                health["checks"]["redis_connection"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health["status"] = "degraded"
        else:
            health["checks"]["redis_connection"] = {
                "status": "unavailable",
                "reason": "Redis client not configured"
            }
            health["status"] = "degraded"
        
        # Check fallback storage
        try:
            fallback_health = await self.fallback_storage.health_check()
            health["checks"]["fallback_storage"] = fallback_health
        except Exception as e:
            health["checks"]["fallback_storage"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "unhealthy"
        
        # Overall status determination
        if self.redis_client:
            health["status"] = "healthy"
        elif health["checks"]["fallback_storage"]["status"] == "healthy":
            health["status"] = "degraded"
        else:
            health["status"] = "unhealthy"
        
        return health


# Export factory function for backward compatibility
async def create_redis_storage(config: Dict[str, Any]) -> StorageBackend:
    """Create Redis storage backend from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        StorageBackend instance (Redis or fallback)
    """
    return await RedisStreamsStorage.create(config)