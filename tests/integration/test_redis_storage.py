"""Integration tests for Redis Streams storage backend."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import json

from arqonbus.storage.redis_streams import RedisStreamsStorage
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id


class TestRedisStreamsStorage:
    """Test Redis Streams storage backend integration."""
    
    @pytest.fixture
    def redis_config(self):
        """Redis configuration for testing."""
        return {
            "redis_url": "redis://localhost:6379/0",
            "stream_prefix": "arqonbus",
            "history_limit": 1000,
            "key_ttl": 3600
        }
    
    @pytest.fixture
    def test_envelope(self):
        """Create a test envelope."""
        return Envelope(
            id=generate_message_id(),
            type="message",
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_client="arq_client_123",
            to_client="arq_client_456",
            payload={"content": "test message"}
        )
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_degrades_to_memory(self, redis_config, caplog):
        """Test that Redis connection failures degrade gracefully to memory storage."""
        with patch('redis.asyncio.from_url') as mock_redis:
            # Mock Redis connection failure
            mock_redis.side_effect = Exception("Connection refused")
            
            # Should create memory storage fallback
            storage = await RedisStreamsStorage.create(redis_config)
            
            # Verify it falls back to memory storage
            assert storage.fallback_storage is not None
            assert "Redis connection failed, falling back to memory storage" in caplog.text
    
    @pytest.mark.asyncio
    async def test_append_to_redis_stream(self, redis_config, test_envelope):
        """Test appending messages to Redis Streams."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            storage = await RedisStreamsStorage.create(redis_config)
            result = await storage.append(test_envelope)
            
            # Verify Redis XADD was called with correct parameters
            mock_redis_client.xadd.assert_called_once()
            call_args = mock_redis_client.xadd.call_args
            
            # Check stream name
            expected_stream = f"{redis_config['stream_prefix']}:messages"
            assert call_args[0][0] == expected_stream
            
            # Check message data
            message_data = call_args[0][1]
            assert "id" in message_data
            assert "type" in message_data
            assert "from_client" in message_data
            assert "to_client" in message_data
            assert "payload" in message_data
            assert "timestamp" in message_data
            
            # Verify result
            assert result == "stream_success"
    
    @pytest.mark.asyncio
    async def test_get_message_history_from_redis(self, redis_config):
        """Test retrieving message history from Redis Streams."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # Mock Redis XRANGE response
            mock_messages = [
                {
                    "id": "1234567890-0",
                    "message": json.dumps({
                        "id": "arq_msg_123",
                        "type": "message",
                        "timestamp": "2025-11-30T21:00:00Z",
                        "from_client": "arq_client_123",
                        "to_client": "arq_client_456",
                        "payload": {"content": "test message"}
                    })
                }
            ]
            mock_redis_client.xrange.return_value = mock_messages
            
            storage = await RedisStreamsStorage.create(redis_config)
            history = await storage.get_history("arq_client_123", limit=50)
            
            # Verify Redis XRANGE was called
            mock_redis_client.xrange.assert_called_once()
            call_args = mock_redis_client.xrange.call_args
            
            # Check stream name and parameters
            expected_stream = f"{redis_config['stream_prefix']}:client_arq_client_123"
            assert call_args[0][0] == expected_stream
            assert call_args[1]["count"] == 50
            
            # Check result
            assert len(history) == 1
            envelope = history[0]
            assert envelope.id == "arq_msg_123"
            assert envelope.from_client == "arq_client_123"
            assert envelope.to_client == "arq_client_456"
            assert envelope.payload == {"content": "test message"}
    
    @pytest.mark.asyncio
    async def test_empty_history_when_redis_unavailable(self, redis_config):
        """Test that empty history is returned when Redis is unavailable."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection refused")
            
            storage = await RedisStreamsStorage.create(redis_config)
            history = await storage.get_history("arq_client_123", limit=50)
            
            # Should return empty list when Redis fails
            assert history == []
    
    @pytest.mark.asyncio
    async def test_stream_cleanup_and_maintenance(self, redis_config):
        """Test Redis Streams cleanup and maintenance operations."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            storage = await RedisStreamsStorage.create(redis_config)
            
            # Test stream cleanup
            await storage.cleanup_streams(max_age=3600)
            
            # Verify Redis commands for cleanup
            mock_redis_client.xtrim.assert_called()
            mock_redis_client.eval.assert_called()
    
    @pytest.mark.asyncio
    async def test_redis_storage_with_config_validation(self, redis_config):
        """Test Redis storage creation with configuration validation."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            storage = await RedisStreamsStorage.create(redis_config)
            
            # Verify storage configuration
            assert storage.redis_url == redis_config["redis_url"]
            assert storage.stream_prefix == redis_config["stream_prefix"]
            assert storage.history_limit == redis_config["history_limit"]
            assert storage.key_ttl == redis_config["key_ttl"]
    
    @pytest.mark.asyncio
    async def test_concurrent_append_operations(self, redis_config, test_envelope):
        """Test concurrent message append operations to Redis Streams."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            storage = await RedisStreamsStorage.create(redis_config)
            
            # Create multiple test envelopes
            envelopes = []
            for i in range(5):
                envelope = Envelope(
                    id=f"arq_msg_{i}",
                    type="message",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    from_client=f"arq_client_{i}",
                    to_client="arq_client_target",
                    payload={"content": f"message {i}"}
                )
                envelopes.append(envelope)
            
            # Perform concurrent appends
            tasks = [storage.append(envelope) for envelope in envelopes]
            results = await asyncio.gather(*tasks)
            
            # Verify all operations succeeded
            assert len(results) == 5
            assert all(result == "stream_success" for result in results)
            
            # Verify Redis was called for each message
            assert mock_redis_client.xadd.call_count == 5
    
    @pytest.mark.asyncio
    async def test_redis_connection_pool_management(self, redis_config):
        """Test Redis connection pool management and reuse."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            storage = await RedisStreamsStorage.create(redis_config)
            
            # Perform multiple operations to test connection reuse
            test_envelope = Envelope(
                id=generate_message_id(),
                type="message",
                timestamp=datetime.now(timezone.utc).isoformat(),
                from_client="arq_client_123",
                to_client="arq_client_456",
                payload={"content": "test message"}
            )
            
            await storage.append(test_envelope)
            await storage.get_history("arq_client_123")
            await storage.cleanup_streams()
            
            # Verify Redis client methods were called
            assert mock_redis_client.xadd.called
            assert mock_redis_client.xrange.called
            assert mock_redis_client.xtrim.called