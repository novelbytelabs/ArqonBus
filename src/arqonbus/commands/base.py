"""Base command classes for ArqonBus command system."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..protocol.envelope import Envelope
from ..routing.router import MessageRouter
from ..routing.client_registry import ClientRegistry
from ..routing.rooms import RoomManager
from ..routing.channels import ChannelManager
from ..storage.interface import MessageStorage
from ..config.config import get_config


logger = logging.getLogger(__name__)


class CommandError(Exception):
    """Base exception for command execution errors."""
    pass


class CommandValidationError(CommandError):
    """Raised when command arguments are invalid."""
    pass


class CommandAuthorizationError(CommandError):
    """Raised when client lacks permission for command."""
    pass


class CommandExecutionError(CommandError):
    """Raised when command execution fails."""
    pass


class CommandResult:
    """Result of command execution."""
    
    def __init__(
        self,
        success: bool,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize command result.
        
        Args:
            success: Whether command succeeded
            message: Human-readable result message
            data: Command result data
            error_code: Machine-readable error code
            metadata: Additional result metadata
        """
        self.success = success
        self.message = message
        self.data = data or {}
        self.error_code = error_code
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_envelope(self, request_id: str, sender: str = "arqonbus") -> Envelope:
        """Convert result to response envelope.
        
        Args:
            request_id: ID of original request
            sender: Sender identifier
            
        Returns:
            Response envelope
        """
        return Envelope(
            type="response",
            request_id=request_id,
            status="success" if self.success else "error",
            payload={
                "message": self.message,
                "data": self.data,
                "metadata": self.metadata
            },
            error_code=self.error_code,
            sender=sender
        )
    
    @classmethod
    def success(cls, message: str, data: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> "CommandResult":
        """Create success result.
        
        Args:
            message: Success message
            data: Result data
            metadata: Additional metadata
            
        Returns:
            Success command result
        """
        return cls(True, message, data, metadata=metadata)
    
    @classmethod
    def error(cls, message: str, error_code: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> "CommandResult":
        """Create error result.
        
        Args:
            message: Error message
            error_code: Machine-readable error code
            data: Error-related data
            
        Returns:
            Error command result
        """
        return cls(False, message, data, error_code)


class CommandContext:
    """Context provided to command executors."""
    
    def __init__(
        self,
        client_id: str,
        envelope: Envelope,
        message_router: MessageRouter,
        client_registry: ClientRegistry,
        room_manager: RoomManager,
        channel_manager: ChannelManager,
        storage: Optional[MessageStorage] = None
    ):
        """Initialize command context.
        
        Args:
            client_id: Client who issued the command
            envelope: Original command envelope
            message_router: Message routing system
            client_registry: Client management
            room_manager: Room management
            channel_manager: Channel management
            storage: Message storage (optional)
        """
        self.client_id = client_id
        self.envelope = envelope
        self.message_router = message_router
        self.client_registry = client_registry
        self.room_manager = room_manager
        self.channel_manager = channel_manager
        self.storage = storage
        self.config = get_config()
    
    async def get_client_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the client who issued the command.
        
        Returns:
            Client information dictionary
        """
        client_info = await self.client_registry.get_client(self.client_id)
        return client_info.to_dict() if client_info else None
    
    async def check_permission(self, permission: str) -> bool:
        """Check if client has specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if client has permission
        """
        client_info = await self.client_registry.get_client(self.client_id)
        if not client_info:
            return False

        metadata = client_info.metadata or {}
        role = str(metadata.get("role", "user")).lower()
        if role == "admin":
            return True

        # Backward-compatible default: if no explicit permissions are provided,
        # preserve existing permissive behavior for legacy clients.
        explicit_permissions = metadata.get("permissions")
        if explicit_permissions is None:
            return True

        if not isinstance(explicit_permissions, list):
            return False
        return permission in explicit_permissions
    
    async def require_permission(self, permission: str):
        """Require specific permission, raise error if not available.
        
        Args:
            permission: Required permission
            
        Raises:
            CommandAuthorizationError: If permission not available
        """
        if not await self.check_permission(permission):
            raise CommandAuthorizationError(f"Client {self.client_id} lacks permission: {permission}")
    
    def validate_args(self, required: Optional[List[str]] = None, optional: Optional[List[str]] = None):
        """Validate command arguments.
        
        Args:
            required: List of required argument names
            optional: List of optional argument names
            
        Raises:
            CommandValidationError: If validation fails
        """
        args = self.envelope.args or {}
        
        # Check required arguments
        if required:
            missing = [arg for arg in required if arg not in args]
            if missing:
                raise CommandValidationError(f"Missing required arguments: {missing}")
        
        # Validate argument types and values
        for arg_name, arg_value in args.items():
            if arg_name in required or (optional and arg_name in optional):
                self._validate_single_arg(arg_name, arg_value)
    
    def _validate_single_arg(self, name: str, value: Any):
        """Validate a single argument.
        
        Args:
            name: Argument name
            value: Argument value
            
        Raises:
            CommandValidationError: If validation fails
        """
        # Basic type validation
        if isinstance(value, (str, int, float, bool, list, dict)):
            return
        
        # Reject complex objects
        raise CommandValidationError(f"Invalid argument type for '{name}': {type(value).__name__}")
    
    async def send_response(self, result: CommandResult):
        """Send command response to client.
        
        Args:
            result: Command execution result
        """
        response_envelope = result.to_envelope(self.envelope.id)
        await self.message_router.route_direct_message(
            response_envelope, "arqonbus", self.client_id
        )
    
    async def broadcast_to_room_channel(
        self,
        envelope: Envelope,
        room: str,
        channel: str,
        exclude_client_id: Optional[str] = None
    ) -> int:
        """Broadcast message to room/channel.
        
        Args:
            envelope: Message to broadcast
            room: Target room
            channel: Target channel
            exclude_client_id: Client to exclude from broadcast
            
        Returns:
            Number of clients who received the message
        """
        return await self.message_router.route_message(envelope, self.client_id)


class BaseCommand(ABC):
    """Abstract base class for all ArqonBus commands."""
    
    def __init__(self, name: str, description: str, permissions: Optional[List[str]] = None):
        """Initialize base command.
        
        Args:
            name: Command name
            description: Command description
            permissions: List of required permissions
        """
        self.name = name
        self.description = description
        self.permissions = permissions or []
    
    @abstractmethod
    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        pass
    
    @abstractmethod
    def get_help(self) -> Dict[str, Any]:
        """Get command help information.
        
        Returns:
            Help information dictionary
        """
        pass
    
    async def validate_and_execute(self, context: CommandContext) -> CommandResult:
        """Validate permissions and arguments, then execute command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        try:
            # Check permissions
            for permission in self.permissions:
                await context.require_permission(permission)
            
            # Execute command
            return await self.execute(context)
            
        except CommandValidationError as e:
            logger.warning(f"Command validation failed for {self.name}: {e}")
            return CommandResult.error(f"Validation error: {e}", "VALIDATION_ERROR")
        except CommandAuthorizationError as e:
            logger.warning(f"Command authorization failed for {self.name}: {e}")
            return CommandResult.error(f"Authorization error: {e}", "AUTHORIZATION_ERROR")
        except Exception as e:
            logger.error(f"Command execution failed for {self.name}: {e}")
            return CommandResult.error(f"Execution error: {e}", "EXECUTION_ERROR")


class SystemCommand(BaseCommand):
    """Base class for system-level commands (always available)."""
    
    def __init__(self, name: str, description: str):
        """Initialize system command.
        
        Args:
            name: Command name
            description: Command description
        """
        super().__init__(name, description, permissions=[])
    
    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute system command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        return await self._execute_system_command(context)
    
    @abstractmethod
    async def _execute_system_command(self, context: CommandContext) -> CommandResult:
        """Execute the system-specific command logic.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        pass


class RoomCommand(BaseCommand):
    """Base class for room-related commands."""
    
    def __init__(self, name: str, description: str, required_permissions: Optional[List[str]] = None):
        """Initialize room command.
        
        Args:
            name: Command name
            description: Command description
            required_permissions: Required permissions
        """
        permissions = required_permissions or ["room_management"]
        super().__init__(name, description, permissions)
    
    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute room command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        try:
            # Validate room argument
            context.validate_args(required=["room"])
            room_id = context.envelope.args["room"]
            
            # Check if room exists
            room = await context.room_manager.get_room(room_id)
            if not room:
                return CommandResult.error(f"Room '{room_id}' does not exist", "ROOM_NOT_FOUND")
            
            return await self._execute_room_command(context, room_id, room)
            
        except CommandValidationError as e:
            return CommandResult.error(f"Validation error: {e}", "VALIDATION_ERROR")
    
    @abstractmethod
    async def _execute_room_command(self, context: CommandContext, room_id: str, room) -> CommandResult:
        """Execute the room-specific command logic.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            room: Room object
            
        Returns:
            Command execution result
        """
        pass


class ChannelCommand(BaseCommand):
    """Base class for channel-related commands."""
    
    def __init__(self, name: str, description: str, required_permissions: Optional[List[str]] = None):
        """Initialize channel command.
        
        Args:
            name: Command name
            description: Command description
            required_permissions: Required permissions
        """
        permissions = required_permissions or ["channel_management"]
        super().__init__(name, description, permissions)
    
    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute channel command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        try:
            # Validate channel arguments
            context.validate_args(required=["room", "channel"])
            room_id = context.envelope.args["room"]
            channel_id = context.envelope.args["channel"]
            
            # Check if room and channel exist
            room = await context.room_manager.get_room(room_id)
            if not room:
                return CommandResult.error(f"Room '{room_id}' does not exist", "ROOM_NOT_FOUND")
            
            channel = await context.channel_manager.get_channel(channel_id)
            if not channel:
                return CommandResult.error(f"Channel '{channel_id}' does not exist", "CHANNEL_NOT_FOUND")
            
            # Verify channel belongs to room
            if channel.room and channel.room.room_id != room_id:
                return CommandResult.error(f"Channel '{channel_id}' does not belong to room '{room_id}'", "CHANNEL_ROOM_MISMATCH")
            
            return await self._execute_channel_command(context, room_id, channel_id, room, channel)
            
        except CommandValidationError as e:
            return CommandResult.error(f"Validation error: {e}", "VALIDATION_ERROR")
    
    @abstractmethod
    async def _execute_channel_command(
        self, 
        context: CommandContext, 
        room_id: str, 
        channel_id: str, 
        room, 
        channel
    ) -> CommandResult:
        """Execute the channel-specific command logic.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Command execution result
        """
        pass
