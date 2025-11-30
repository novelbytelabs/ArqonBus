"""Command executor for ArqonBus command system."""
import asyncio
import logging
from typing import Dict, Optional, List, Type, Any
from datetime import datetime

from ..protocol.envelope import Envelope
from ..routing.router import MessageRouter
from ..routing.client_registry import ClientRegistry
from ..routing.rooms import RoomManager
from ..routing.channels import ChannelManager
from ..storage.interface import MessageStorage
from .base import (
    BaseCommand, SystemCommand, RoomCommand, ChannelCommand,
    CommandContext, CommandResult, CommandError
)


logger = logging.getLogger(__name__)


class CommandRegistry:
    """Registry for available commands."""
    
    def __init__(self):
        """Initialize command registry."""
        self._commands: Dict[str, BaseCommand] = {}
        self._command_classes: Dict[str, Type[BaseCommand]] = {}
    
    def register_command(self, command: BaseCommand):
        """Register a command instance.
        
        Args:
            command: Command instance to register
        """
        self._commands[command.name] = command
        logger.info(f"Registered command: {command.name}")
    
    def register_command_class(self, command_class: Type[BaseCommand]):
        """Register a command class for dynamic instantiation.
        
        Args:
            command_class: Command class to register
        """
        # Create a temporary instance to get the name
        temp_command = command_class("temp", "temp")
        self._command_classes[temp_command.name] = command_class
        logger.info(f"Registered command class: {temp_command.name}")
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """Get a registered command by name.
        
        Args:
            name: Command name
            
        Returns:
            Command instance or None if not found
        """
        return self._commands.get(name)
    
    def create_command(self, name: str, **kwargs) -> Optional[BaseCommand]:
        """Create a command instance from registered class.
        
        Args:
            name: Command name
            **kwargs: Arguments to pass to command constructor
            
        Returns:
            Command instance or None if not found
        """
        command_class = self._command_classes.get(name)
        if command_class:
            return command_class(**kwargs)
        return None
    
    def list_commands(self) -> List[str]:
        """Get list of all registered command names.
        
        Returns:
            List of command names
        """
        return list(self._commands.keys())
    
    def get_command_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a command.
        
        Args:
            name: Command name
            
        Returns:
            Command information dictionary or None
        """
        command = self.get_command(name)
        if command:
            return command.get_help()
        return None


class CommandExecutor:
    """Main command executor for ArqonBus."""
    
    def __init__(
        self,
        message_router: MessageRouter,
        client_registry: ClientRegistry,
        room_manager: RoomManager,
        channel_manager: ChannelManager,
        storage: Optional[MessageStorage] = None
    ):
        """Initialize command executor.
        
        Args:
            message_router: Message routing system
            client_registry: Client management
            room_manager: Room management
            channel_manager: Channel management
            storage: Message storage (optional)
        """
        self.message_router = message_router
        self.client_registry = client_registry
        self.room_manager = room_manager
        self.channel_manager = channel_manager
        self.storage = storage
        
        self.registry = CommandRegistry()
        self._setup_default_commands()
        
        # Statistics
        self._stats = {
            "total_commands_executed": 0,
            "commands_by_type": {},
            "execution_errors": 0,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    def _setup_default_commands(self):
        """Setup default built-in commands."""
        # Import built-in commands
        from .builtin import (
            StatusCommand, PingCommand, CreateChannelCommand, DeleteChannelCommand,
            JoinChannelCommand, LeaveChannelCommand, ListChannelsCommand,
            ChannelInfoCommand, HistoryCommand, HelpCommand
        )
        
        # Register all built-in commands
        built_in_commands = [
            StatusCommand(),
            PingCommand(),
            CreateChannelCommand(),
            DeleteChannelCommand(),
            JoinChannelCommand(),
            LeaveChannelCommand(),
            ListChannelsCommand(),
            ChannelInfoCommand(),
            HistoryCommand(),
            HelpCommand()
        ]
        
        for command in built_in_commands:
            self.registry.register_command(command)
    
    async def execute_command(self, envelope: Envelope) -> bool:
        """Execute a command from an envelope.
        
        Args:
            envelope: Command envelope
            
        Returns:
            True if command was executed successfully
        """
        try:
            if not envelope.command:
                logger.error("Command envelope missing command name")
                await self._send_error_response(envelope, "Missing command name", "MISSING_COMMAND")
                return False
            
            # Get command
            command = self.registry.get_command(envelope.command)
            if not command:
                logger.warning(f"Unknown command: {envelope.command}")
                await self._send_error_response(envelope, f"Unknown command: {envelope.command}", "UNKNOWN_COMMAND")
                return False
            
            # Create context
            context = CommandContext(
                client_id=envelope.sender or "unknown",
                envelope=envelope,
                message_router=self.message_router,
                client_registry=self.client_registry,
                room_manager=self.room_manager,
                channel_manager=self.channel_manager,
                storage=self.storage
            )
            
            # Execute command
            logger.info(f"Executing command '{envelope.command}' for client {context.client_id}")
            result = await command.validate_and_execute(context)
            
            # Send response
            await context.send_response(result)
            
            # Update statistics
            self._stats["total_commands_executed"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            cmd_type = type(command).__name__
            if cmd_type not in self._stats["commands_by_type"]:
                self._stats["commands_by_type"][cmd_type] = 0
            self._stats["commands_by_type"][cmd_type] += 1
            
            logger.info(f"Command '{envelope.command}' executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing command '{envelope.command}': {e}")
            self._stats["execution_errors"] += 1
            
            # Send error response
            await self._send_error_response(envelope, f"Internal error: {str(e)}", "INTERNAL_ERROR")
            return False
    
    async def _send_error_response(
        self,
        envelope: Envelope,
        error_message: str,
        error_code: str
    ):
        """Send error response to client.
        
        Args:
            envelope: Original command envelope
            error_message: Error message
            error_code: Error code
        """
        try:
            error_response = CommandResult.error(error_message, error_code)
            response_envelope = error_response.to_envelope(envelope.id)
            
            if envelope.sender:
                await self.message_router.route_direct_message(
                    response_envelope, "arqonbus", envelope.sender
                )
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    async def get_command_help(self, command_name: Optional[str] = None) -> Dict[str, Any]:
        """Get help information for commands.
        
        Args:
            command_name: Specific command name (None for all commands)
            
        Returns:
            Help information dictionary
        """
        if command_name:
            # Get help for specific command
            info = self.registry.get_command_info(command_name)
            if info:
                return {
                    "command": command_name,
                    "help": info,
                    "available": True
                }
            else:
                return {
                    "command": command_name,
                    "help": None,
                    "available": False,
                    "error": f"Command '{command_name}' not found"
                }
        else:
            # Get help for all commands
            commands = {}
            for cmd_name in self.registry.list_commands():
                info = self.registry.get_command_info(cmd_name)
                if info:
                    commands[cmd_name] = info
            
            return {
                "commands": commands,
                "total_available": len(commands),
                "command_categories": {
                    "system": [name for name in commands.keys() if "Command" in type(self.registry.get_command(name)).__name__ and "System" in type(self.registry.get_command(name)).__bases__[0].__name__],
                    "room": [name for name in commands.keys() if "Room" in type(self.registry.get_command(name)).__bases__[0].__name__],
                    "channel": [name for name in commands.keys() if "Channel" in type(self.registry.get_command(name)).__bases__[0].__name__]
                }
            }
    
    async def list_available_commands(self) -> List[str]:
        """Get list of all available command names.
        
        Returns:
            List of command names
        """
        return self.registry.list_commands()
    
    async def validate_command(self, envelope: Envelope) -> Dict[str, Any]:
        """Validate a command without executing it.
        
        Args:
            envelope: Command envelope to validate
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "command_info": None
        }
        
        try:
            # Check if command exists
            if not envelope.command:
                validation_result["valid"] = False
                validation_result["errors"].append("Command name is required")
                return validation_result
            
            command = self.registry.get_command(envelope.command)
            if not command:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Unknown command: {envelope.command}")
                return validation_result
            
            # Get command info
            validation_result["command_info"] = command.get_help()
            
            # Validate arguments if command requires them
            if hasattr(command, 'get_required_args'):
                required_args = command.get_required_args()
                args = envelope.args or {}
                
                missing_args = [arg for arg in required_args if arg not in args]
                if missing_args:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Missing required arguments: {missing_args}")
            
            # Check argument types
            if envelope.args:
                for arg_name, arg_value in envelope.args.items():
                    if not isinstance(arg_value, (str, int, float, bool, list, dict)):
                        validation_result["warnings"].append(
                            f"Argument '{arg_name}' has non-standard type: {type(arg_value).__name__}"
                        )
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    async def get_executor_stats(self) -> Dict[str, Any]:
        """Get command executor statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            # Get router stats for context
            router_stats = await self.message_router.get_routing_stats()
            
            return {
                "executor": self._stats.copy(),
                "available_commands": len(self.registry.list_commands()),
                "command_list": self.registry.list_commands(),
                "router_context": {
                    "total_messages_routed": router_stats.get("routing", {}).get("total_messages_routed", 0),
                    "active_clients": router_stats.get("clients", {}).get("current_clients", 0),
                    "active_rooms": router_stats.get("rooms", {}).get("total_rooms", 0)
                },
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting executor stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on command executor.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_executor_stats()
            
            health = {
                "status": "healthy",
                "available_commands": stats["available_commands"],
                "total_executed": self._stats["total_commands_executed"],
                "error_rate": self._stats["execution_errors"] / max(1, self._stats["total_commands_executed"]),
                "checks": []
            }
            
            # Check for potential issues
            if health["error_rate"] > 0.1:  # 10% error rate
                health["checks"].append({"type": "error", "message": "High command error rate"})
            
            if stats["available_commands"] == 0:
                health["checks"].append({"type": "error", "message": "No commands registered"})
            
            # Check router health
            router_health = await self.message_router.health_check()
            if router_health.get("status") != "healthy":
                health["checks"].append({"type": "warning", "message": "Router health degraded"})
            
            # Overall status
            if health["checks"]:
                health["status"] = "degraded" if health["error_rate"] < 0.2 else "unhealthy"
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }


class CommandDispatcher:
    """High-level command dispatcher for integration with WebSocket server."""
    
    def __init__(self, executor: CommandExecutor):
        """Initialize command dispatcher.
        
        Args:
            executor: Command executor to use
        """
        self.executor = executor
    
    async def handle_command_envelope(self, envelope: Envelope) -> bool:
        """Handle a command envelope from WebSocket server.
        
        Args:
            envelope: Command envelope to handle
            
        Returns:
            True if command was handled successfully
        """
        return await self.executor.execute_command(envelope)
    
    async def get_help(self, command_name: Optional[str] = None) -> Dict[str, Any]:
        """Get command help information.
        
        Args:
            command_name: Specific command name (None for all commands)
            
        Returns:
            Help information dictionary
        """
        return await self.executor.get_command_help(command_name)
    
    async def validate_command(self, envelope: Envelope) -> Dict[str, Any]:
        """Validate a command without executing it.
        
        Args:
            envelope: Command envelope to validate
            
        Returns:
            Validation result dictionary
        """
        return await self.executor.validate_command(envelope)