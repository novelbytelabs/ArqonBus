"""Unique identifier generation for ArqonBus messages."""
import time
import uuid
import threading
from typing import Optional


class IDGenerator:
    """Thread-safe ID generator for ArqonBus messages.
    
    Generates unique message IDs with arq_ prefix for consistent
    identification across the system.
    """
    
    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()
        self._start_time = time.time_ns()  # nanosecond timestamp
        
    def generate_message_id(self) -> str:
        """Generate a unique message ID with arq_ prefix.
        
        ID format: arq_{timestamp}_{counter}_{uuid_short}
        - timestamp: nanoseconds since generator creation
        - counter: incrementing sequence number  
        - uuid_short: short UUID for additional uniqueness
        
        Returns:
            str: Unique message ID like "arq_1640995200000000_123_abc123"
        """
        with self._lock:
            self._counter += 1
            timestamp_part = self._start_time
            counter_part = self._counter
            uuid_part = str(uuid.uuid4()).replace('-', '')[:6]
            
        return f"arq_{timestamp_part}_{counter_part}_{uuid_part}"
    
    def generate_client_id(self) -> str:
        """Generate a unique client ID with arq_client_ prefix.
        
        Client IDs are longer and more persistent than message IDs.
        
        Returns:
            str: Unique client ID like "arq_client_abc123def456"
        """
        return f"arq_client_{str(uuid.uuid4()).replace('-', '')}"
    
    def generate_room_id(self) -> str:
        """Generate a unique room ID with arq_room_ prefix.
        
        Returns:
            str: Unique room ID like "arq_room_xyz789abc123"
        """
        return f"arq_room_{str(uuid.uuid4()).replace('-', '')}"
    
    def generate_channel_id(self) -> str:
        """Generate a unique channel ID with arq_channel_ prefix.
        
        Returns:
            str: Unique channel ID like "arq_channel_def456ghi789"
        """
        return f"arq_channel_{str(uuid.uuid4()).replace('-', '')}"


# Global generator instance
_generator = IDGenerator()


def generate_message_id() -> str:
    """Generate a message ID using the global generator.
    
    This is the main function used throughout ArqonBus for generating
    message IDs.
    
    Returns:
        str: Unique message ID
    """
    return _generator.generate_message_id()


def generate_client_id() -> str:
    """Generate a client ID using the global generator.
    
    Returns:
        str: Unique client ID
    """
    return _generator.generate_client_id()


def generate_room_id() -> str:
    """Generate a room ID using the global generator.
    
    Returns:
        str: Unique room ID
    """
    return _generator.generate_room_id()


def generate_channel_id() -> str:
    """Generate a channel ID using the global generator.
    
    Returns:
        str: Unique channel ID
    """
    return _generator.generate_channel_id()


def is_valid_message_id(message_id: str) -> bool:
    """Check if a message ID follows the expected format.
    
    Args:
        message_id: Message ID to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not message_id or not message_id.startswith("arq_"):
        return False
    
    parts = message_id.split("_")
    if len(parts) != 4:
        return False
        
    # Verify parts: arq, timestamp, counter, uuid_short
    try:
        # timestamp should be numeric
        int(parts[1])
        # counter should be numeric
        int(parts[2])
        # uuid_short should be 6 hex characters
        uuid_part = parts[3]
        if len(uuid_part) != 6:
            return False
        int(uuid_part, 16)  # verify it's valid hex
        return True
    except ValueError:
        return False