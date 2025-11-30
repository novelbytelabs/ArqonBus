"""Message envelope for ArqonBus protocol."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class Envelope:
    """Structured message envelope for ArqonBus communication.
    
    All messages in ArqonBus follow this envelope structure to ensure
    consistent routing, validation, and processing.
    """
    
    # Required fields - all messages must have these
    id: str = field(default_factory=lambda: f"arq_{int(datetime.now().timestamp() * 1000000)}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    type: str = ""  # message, command, response, error, telemetry
    version: str = "1.0"
    
    # Routing fields
    room: Optional[str] = None  # Target room for routing
    channel: Optional[str] = None  # Target channel within room
    sender: Optional[str] = None  # Client ID who sent this message
    
    # Message content
    payload: Dict[str, Any] = field(default_factory=dict)  # Message data
    
    # Command-specific fields
    command: Optional[str] = None  # Built-in command name
    args: Dict[str, Any] = field(default_factory=dict)  # Command arguments
    
    # Response fields
    request_id: Optional[str] = None  # Reference to original request
    status: Optional[str] = None  # success, error, pending
    
    # Error information
    error: Optional[str] = None  # Error message if status is error
    error_code: Optional[str] = None  # Machine-readable error code
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to dictionary for JSON serialization."""
        data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "version": self.version,
            "payload": self.payload,
            "args": self.args,
            "metadata": self.metadata
        }
        
        # Optional fields only included if set
        if self.room is not None:
            data["room"] = self.room
        if self.channel is not None:
            data["channel"] = self.channel
        if self.sender is not None:
            data["sender"] = self.sender
        if self.command is not None:
            data["command"] = self.command
        if self.request_id is not None:
            data["request_id"] = self.request_id
        if self.status is not None:
            data["status"] = self.status
        if self.error is not None:
            data["error"] = self.error
        if self.error_code is not None:
            data["error_code"] = self.error_code
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Envelope":
        """Create envelope from dictionary (e.g., from JSON deserialization)."""
        # Handle datetime parsing
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert envelope to JSON string."""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "Envelope":
        """Create envelope from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> List[str]:
        """Validate envelope and return list of validation errors."""
        errors = []
        
        # Required field validation
        if not self.type:
            errors.append("Field 'type' is required")
        if not self.version:
            errors.append("Field 'version' is required")
            
        # Message type validation
        if self.type == "message":
            if not self.payload:
                errors.append("Messages must have payload")
        elif self.type == "command":
            if not self.command:
                errors.append("Commands must have command name")
        elif self.type == "response":
            if not self.request_id:
                errors.append("Responses must have request_id")
                
        # Version validation
        if self.version != "1.0":
            errors.append(f"Unsupported protocol version: {self.version}")
            
        return errors