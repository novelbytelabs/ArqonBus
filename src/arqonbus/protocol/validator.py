"""Message envelope validation and parsing utilities."""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .envelope import Envelope
from .ids import is_valid_message_id


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when envelope validation fails."""
    pass


class EnvelopeValidator:
    """Validates ArqonBus message envelopes according to protocol rules."""
    
    # Supported message types
    SUPPORTED_MESSAGE_TYPES = {"message", "command", "response", "error", "telemetry", "operator.join"}
    
    # Supported protocol versions
    SUPPORTED_VERSIONS = {"1.0"}
    
    # Required fields by message type
    REQUIRED_FIELDS = {
        "message": ["id", "timestamp", "type", "version", "payload"],
        "command": ["id", "timestamp", "type", "version", "command"],
        "response": ["id", "timestamp", "type", "version", "request_id"],
        "error": ["id", "timestamp", "type", "version", "error"],
        "telemetry": ["id", "timestamp", "type", "version"],
        "operator.join": ["id", "timestamp", "type", "version", "payload"]
    }
    
    @classmethod
    def validate_envelope(cls, envelope: Envelope) -> List[str]:
        """Validate an envelope and return list of errors.
        
        Args:
            envelope: Envelope to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Basic field validation
        errors.extend(cls._validate_basic_fields(envelope))
        
        # Type-specific validation
        if envelope.type in cls.REQUIRED_FIELDS:
            errors.extend(cls._validate_required_fields(envelope))
            
        # Cross-field validation
        errors.extend(cls._validate_field_consistency(envelope))
        
        return errors
    
    @classmethod
    def _validate_basic_fields(cls, envelope: Envelope) -> List[str]:
        """Validate basic fields that apply to all message types."""
        errors = []
        
        # ID validation
        if not envelope.id:
            errors.append("Message ID is required")
        elif not is_valid_message_id(envelope.id):
            errors.append(f"Invalid message ID format: {envelope.id}")
            
        # Type validation
        if not envelope.type:
            errors.append("Message type is required")
        elif envelope.type not in cls.SUPPORTED_MESSAGE_TYPES:
            errors.append(f"Unsupported message type: {envelope.type}")
            
        # Version validation
        if not envelope.version:
            errors.append("Protocol version is required")
        elif envelope.version not in cls.SUPPORTED_VERSIONS:
            errors.append(f"Unsupported protocol version: {envelope.version}")
            
        # Timestamp validation
        if not envelope.timestamp:
            errors.append("Timestamp is required")
        elif not isinstance(envelope.timestamp, datetime):
            errors.append("Timestamp must be a datetime object")
            
        return errors
    
    @classmethod
    def _validate_required_fields(cls, envelope: Envelope) -> List[str]:
        """Validate fields required for specific message types."""
        errors = []
        required = cls.REQUIRED_FIELDS.get(envelope.type, [])
        
        for field in required:
            value = getattr(envelope, field, None)
            if value is None or value == "":
                errors.append(f"Field '{field}' is required for {envelope.type} messages")
                
        return errors
    
    @classmethod
    def _validate_field_consistency(cls, envelope: Envelope) -> List[str]:
        """Validate cross-field consistency rules."""
        errors = []
        
        # Command messages should have args
        if envelope.type == "command" and envelope.command and not envelope.args:
            logger.warning(f"Command {envelope.command} has no arguments")
            
        # Response messages should have status
        if envelope.type == "response" and envelope.request_id and not envelope.status:
            errors.append("Response messages must include status")
            
        # Error messages should have error details
        if envelope.type == "error" and envelope.error and not envelope.error_code:
            logger.warning(f"Error message missing error_code: {envelope.error}")
            
        # Messages with room/channel should have routing info
        if envelope.room and not envelope.channel:
            logger.warning(f"Message has room '{envelope.room}' but no channel")
            
        return errors
    
    @classmethod
    def validate_and_parse_json(cls, json_data: str) -> Tuple[Envelope, List[str]]:
        """Parse JSON data into envelope and validate it.
        
        Args:
            json_data: JSON string to parse
            
        Returns:
            Tuple of (envelope, validation_errors)
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
        """
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
            
        try:
            envelope = Envelope.from_dict(data)
        except Exception as e:
            raise ValidationError(f"Failed to create envelope from data: {e}")
            
        errors = cls.validate_envelope(envelope)
        return envelope, errors

    @classmethod
    def validate_and_parse_protobuf(cls, payload: bytes) -> Tuple[Envelope, List[str]]:
        """Parse protobuf payload into envelope and validate it."""
        try:
            envelope = Envelope.from_proto_bytes(payload)
        except Exception as e:
            raise ValidationError(f"Invalid protobuf envelope: {e}")

        errors = cls.validate_envelope(envelope)
        return envelope, errors

    @classmethod
    def validate_and_parse_wire(cls, wire_data: Any) -> Tuple[Envelope, List[str], str]:
        """Parse incoming wire data.

        Returns:
            (envelope, validation_errors, wire_format) where wire_format is `json` or `protobuf`.
        """
        if isinstance(wire_data, (bytes, bytearray)):
            envelope, errors = cls.validate_and_parse_protobuf(bytes(wire_data))
            return envelope, errors, "protobuf"
        if isinstance(wire_data, str):
            envelope, errors = cls.validate_and_parse_json(wire_data)
            return envelope, errors, "json"
        raise ValidationError(f"Unsupported wire payload type: {type(wire_data).__name__}")
    
    @classmethod
    def is_valid(cls, envelope: Envelope) -> bool:
        """Check if envelope is valid without returning error details.
        
        Args:
            envelope: Envelope to validate
            
        Returns:
            True if valid, False otherwise
        """
        return len(cls.validate_envelope(envelope)) == 0


def validate_envelope(envelope: Envelope) -> List[str]:
    """Validate an envelope.
    
    Args:
        envelope: Envelope to validate
        
    Returns:
        List of validation error messages
    """
    return EnvelopeValidator.validate_envelope(envelope)


def validate_and_parse_json(json_data: str) -> Tuple[Envelope, List[str]]:
    """Parse and validate JSON envelope data.
    
    Args:
        json_data: JSON string to parse and validate
        
    Returns:
        Tuple of (envelope, validation_errors)
    """
    return EnvelopeValidator.validate_and_parse_json(json_data)


def is_valid_envelope(envelope: Envelope) -> bool:
    """Check if envelope is valid.
    
    Args:
        envelope: Envelope to check
        
    Returns:
        True if valid, False otherwise
    """
    return EnvelopeValidator.is_valid(envelope)


# Utility functions for common validation scenarios
def validate_message_payload(payload: Dict[str, Any]) -> List[str]:
    """Validate message payload structure.
    
    Args:
        payload: Message payload to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not isinstance(payload, dict):
        errors.append("Message payload must be a dictionary")
        return errors
        
    # Check for common payload patterns
    if "text" in payload and not isinstance(payload["text"], str):
        errors.append("Payload text field must be a string")
        
    if "data" in payload and not isinstance(payload["data"], (dict, list)):
        errors.append("Payload data field must be a dictionary or list")
        
    return errors


def validate_command_args(args: Dict[str, Any]) -> List[str]:
    """Validate command arguments.
    
    Args:
        args: Command arguments to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not isinstance(args, dict):
        errors.append("Command arguments must be a dictionary")
        return errors
        
    # Common argument validation
    if "room" in args and not isinstance(args["room"], str):
        errors.append("Room argument must be a string")
        
    if "channel" in args and not isinstance(args["channel"], str):
        errors.append("Channel argument must be a string")
        
    return errors
