#!/usr/bin/env python3
"""Simple test to verify basic functionality without server startup."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

# Test basic imports
def test_basic_imports():
    """Test that all core modules can be imported."""
    try:
        from arqonbus import __version__
        assert __version__ == "0.1.0"
        
        from arqonbus.config.config import ArqonBusConfig, get_config
        from arqonbus.protocol.envelope import Envelope
        from arqonbus.protocol.ids import generate_message_id
        
        print("All core imports successful")
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_configuration():
    """Test configuration loading."""
    try:
        from arqonbus.config.config import ArqonBusConfig, get_config
        
        config = get_config()
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9100
        assert config.storage.backend in ["memory", "redis", "valkey", "postgres"]
        
        print("Configuration loading successful")
    except Exception as e:
        pytest.fail(f"Configuration test failed: {e}")

def test_message_generation():
    """Test message ID generation."""
    try:
        from arqonbus.protocol.ids import generate_message_id
        
        msg_id = generate_message_id()
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0
        
        print(f"Message ID generation successful: {msg_id}")
    except Exception as e:
        pytest.fail(f"Message ID generation failed: {e}")

def test_envelope_creation():
    """Test envelope creation."""
    try:
        from arqonbus.protocol.envelope import Envelope
        
        envelope = Envelope(
            id="test-123",
            type="message",
            timestamp=datetime.now(timezone.utc),
            sender="client1",
            room="general",
            channel="general",
            payload={"content": "test message"}
        )
        
        assert envelope.id == "test-123"
        assert envelope.type == "message"
        assert envelope.sender == "client1"
        assert envelope.payload["content"] == "test message"
        
        print("Envelope creation successful")
    except Exception as e:
        pytest.fail(f"Envelope creation failed: {e}")

@pytest.mark.asyncio
async def test_storage_interface():
    """Test storage interface without actual server."""
    try:
        from arqonbus.protocol.envelope import Envelope
        from arqonbus.storage.interface import MessageStorage
        from arqonbus.storage.memory import MemoryStorageBackend
        
        # Create memory storage backend
        backend = MemoryStorageBackend(max_size=100)
        
        # Create message storage wrapper
        storage = MessageStorage(backend)
        
        # Create test envelope
        envelope = Envelope(
            id="test-msg-1",
            type="message",
            timestamp=datetime.now(timezone.utc),
            sender="client1",
            payload={"content": "test"}
        )
        
        # Test storage operation
        result = await storage.store_message(envelope)
        assert result.success
        assert result.message_id == "test-msg-1"
        
        print("Storage interface test successful")
    except Exception as e:
        pytest.fail(f"Storage interface test failed: {e}")

if __name__ == "__main__":
    # Run tests manually for debugging
    import sys
    import traceback
    
    tests = [
        test_basic_imports,
        test_configuration,
        test_message_generation,
        test_envelope_creation,
    ]
    
    for test in tests:
        try:
            print(f"\n=== Running {test.__name__} ===")
            test()
            print(f"✓ {test.__name__} PASSED")
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            traceback.print_exc()
    
    # Run async test separately
    try:
        print(f"\n=== Running test_storage_interface ===")
        asyncio.run(test_storage_interface())
        print("✓ test_storage_interface PASSED")
    except Exception as e:
        print(f"✗ test_storage_interface FAILED: {e}")
        traceback.print_exc()
