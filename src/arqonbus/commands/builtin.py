"""Built-in commands for ArqonBus."""
import asyncio
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .base import SystemCommand, RoomCommand, ChannelCommand, CommandResult, CommandContext
from ..protocol.envelope import Envelope


class StatusCommand(SystemCommand):
    """Get server status information."""
    
    def __init__(self):
        """Initialize status command."""
        super().__init__("status", "Get ArqonBus server status and statistics")
    
    async def _execute_system_command(self, context: CommandContext) -> CommandResult:
        """Execute status command.
        
        Args:
            context: Command execution context
            
        Returns:
            Status command result
        """
        try:
            # Get server statistics
            server_stats = await context.message_router.get_routing_stats()
            
            # Get command executor stats
            executor_stats = await context.message_router.health_check()
            
            # Get storage stats if available
            storage_stats = None
            if context.storage:
                storage_stats = await context.storage.get_storage_stats()
            
            # Compile status information
            status_info = {
                "server": {
                    "status": "running",
                    "uptime": time.time(),  # Simple uptime calculation
                    "version": "1.0.0"
                },
                "clients": server_stats.get("clients", {}),
                "routing": server_stats.get("routing", {}),
                "rooms": server_stats.get("rooms", {}),
                "channels": server_stats.get("channels", {}),
                "storage": storage_stats,
                "health": executor_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success("Server status retrieved", status_info)
            
        except Exception as e:
            return CommandResult.error(f"Failed to get status: {str(e)}", "STATUS_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for status command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "status",
            "permissions": [],
            "arguments": {},
            "examples": [
                {"command": "status", "description": "Get server status"}
            ]
        }


class PingCommand(SystemCommand):
    """Ping command to test connectivity."""
    
    def __init__(self):
        """Initialize ping command."""
        super().__init__("ping", "Test connectivity and latency")
    
    async def _execute_system_command(self, context: CommandContext) -> CommandResult:
        """Execute ping command.
        
        Args:
            context: Command execution context
            
        Returns:
            Ping command result
        """
        try:
            start_time = time.time()
            
            # Get client info to confirm connectivity
            client_info = await context.get_client_info()
            
            end_time = time.time()
            latency_ms = round((end_time - start_time) * 1000, 2)
            
            ping_data = {
                "latency_ms": latency_ms,
                "client_id": context.client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "client_info": client_info
            }
            
            return CommandResult.success(f"Pong! Latency: {latency_ms}ms", ping_data)
            
        except Exception as e:
            return CommandResult.error(f"Ping failed: {str(e)}", "PING_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for ping command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "ping",
            "permissions": [],
            "arguments": {},
            "examples": [
                {"command": "ping", "description": "Test connectivity"}
            ]
        }


class CreateChannelCommand(ChannelCommand):
    """Create a new channel in a room."""
    
    def __init__(self):
        """Initialize create channel command."""
        super().__init__(
            "create_channel",
            "Create a new channel in a room",
            permissions=["channel_management"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute create channel command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Create channel command result
        """
        # This shouldn't be called for create_channel since we're creating
        # This method is for existing channels only
        return CommandResult.error("Channel already exists", "CHANNEL_EXISTS")
    
    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute create channel command.
        
        Args:
            context: Command execution context
            
        Returns:
            Command execution result
        """
        try:
            # Validate arguments
            context.validate_args(required=["room"], optional=["channel", "name", "description"])
            
            room_id = context.envelope.args["room"]
            channel_name = context.envelope.args.get("channel") or context.envelope.args.get("name")
            description = context.envelope.args.get("description", "")
            
            # Check if room exists
            room = await context.room_manager.get_room(room_id)
            if not room:
                return CommandResult.error(f"Room '{room_id}' does not exist", "ROOM_NOT_FOUND")
            
            # Check if channel already exists
            existing_channel = await context.channel_manager.get_channel_by_name(room_id, channel_name)
            if existing_channel:
                return CommandResult.error(f"Channel '{channel_name}' already exists in room '{room_id}'", "CHANNEL_EXISTS")
            
            # Create channel
            created_channel_id = await context.channel_manager.create_channel(
                room_id=room_id,
                name=channel_name,
                description=description
            )
            
            creation_data = {
                "room_id": room_id,
                "channel_id": created_channel_id,
                "channel_name": channel_name,
                "description": description,
                "created_by": context.client_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success(f"Channel '{channel_name}' created successfully", creation_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to create channel: {str(e)}", "CREATE_CHANNEL_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for create channel command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "create_channel",
            "permissions": ["channel_management"],
            "arguments": {
                "room": "Room ID where to create the channel (required)",
                "channel": "Channel name (required, alternative to 'name')",
                "name": "Channel name (required, alternative to 'channel')",
                "description": "Channel description (optional)"
            },
            "examples": [
                {
                    "command": "create_channel",
                    "description": "Create a channel with default name",
                    "args": {"room": "general", "channel": "general", "description": "General discussion channel"}
                }
            ]
        }


class DeleteChannelCommand(ChannelCommand):
    """Delete a channel from a room."""
    
    def __init__(self):
        """Initialize delete channel command."""
        super().__init__(
            "delete_channel",
            "Delete a channel from a room",
            permissions=["channel_management"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute delete channel command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Delete channel command result
        """
        try:
            # Delete the channel
            success = await context.channel_manager.delete_channel(channel_id)
            
            if not success:
                return CommandResult.error(f"Failed to delete channel '{channel_id}'", "DELETE_CHANNEL_ERROR")
            
            deletion_data = {
                "room_id": room_id,
                "channel_id": channel_id,
                "channel_name": channel.name,
                "deleted_by": context.client_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success(f"Channel '{channel.name}' deleted successfully", deletion_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to delete channel: {str(e)}", "DELETE_CHANNEL_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for delete channel command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "delete_channel",
            "permissions": ["channel_management"],
            "arguments": {
                "room": "Room ID where the channel exists (required)",
                "channel": "Channel ID to delete (required)"
            },
            "examples": [
                {
                    "command": "delete_channel",
                    "description": "Delete a channel",
                    "args": {"room": "general", "channel": "arq_channel_123"}
                }
            ]
        }


class JoinChannelCommand(ChannelCommand):
    """Join a channel in a room."""
    
    def __init__(self):
        """Initialize join channel command."""
        super().__init__(
            "join_channel",
            "Join a channel in a room",
            permissions=["channel_access"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute join channel command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Join channel command result
        """
        try:
            # Join the channel
            success = await context.channel_manager.join_channel(context.client_id, channel_id)
            
            if not success:
                return CommandResult.error(f"Failed to join channel '{channel_id}'", "JOIN_CHANNEL_ERROR")
            
            # Join the room as well
            room_success = await context.room_manager.join_room(context.client_id, room_id)
            
            join_data = {
                "room_id": room_id,
                "channel_id": channel_id,
                "channel_name": channel.name,
                "joined_by": context.client_id,
                "joined_at": datetime.utcnow().isoformat(),
                "room_joined": room_success
            }
            
            return CommandResult.success(f"Joined channel '{channel.name}' successfully", join_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to join channel: {str(e)}", "JOIN_CHANNEL_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for join channel command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "join_channel",
            "permissions": ["channel_access"],
            "arguments": {
                "room": "Room ID where the channel exists (required)",
                "channel": "Channel ID to join (required)"
            },
            "examples": [
                {
                    "command": "join_channel",
                    "description": "Join a channel",
                    "args": {"room": "general", "channel": "arq_channel_123"}
                }
            ]
        }


class LeaveChannelCommand(ChannelCommand):
    """Leave a channel in a room."""
    
    def __init__(self):
        """Initialize leave channel command."""
        super().__init__(
            "leave_channel",
            "Leave a channel in a room",
            permissions=["channel_access"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute leave channel command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Leave channel command result
        """
        try:
            # Leave the channel
            channel_success = await context.channel_manager.leave_channel(context.client_id, channel_id)
            
            # Leave the room (check if client is still in other channels)
            room_success = await context.room_manager.leave_room(context.client_id, room_id)
            
            leave_data = {
                "room_id": room_id,
                "channel_id": channel_id,
                "channel_name": channel.name,
                "left_by": context.client_id,
                "left_at": datetime.utcnow().isoformat(),
                "room_left": room_success
            }
            
            return CommandResult.success(f"Left channel '{channel.name}' successfully", leave_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to leave channel: {str(e)}", "LEAVE_CHANNEL_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for leave channel command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "leave_channel",
            "permissions": ["channel_access"],
            "arguments": {
                "room": "Room ID where the channel exists (required)",
                "channel": "Channel ID to leave (required)"
            },
            "examples": [
                {
                    "command": "leave_channel",
                    "description": "Leave a channel",
                    "args": {"room": "general", "channel": "arq_channel_123"}
                }
            ]
        }


class ListChannelsCommand(RoomCommand):
    """List all channels in a room."""
    
    def __init__(self):
        """Initialize list channels command."""
        super().__init__(
            "list_channels",
            "List all channels in a room",
            permissions=["channel_view"]
        )
    
    async def _execute_room_command(self, context: CommandContext, room_id: str, room) -> CommandResult:
        """Execute list channels command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            room: Room object
            
        Returns:
            List channels command result
        """
        try:
            # Get all channels in the room
            channels = await context.channel_manager.get_room_channels(room_id)
            
            # Format channel information
            channel_list = []
            for channel in channels:
                channel_info = {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "description": channel.description,
                    "member_count": channel.member_count,
                    "created_at": channel.created_at.isoformat(),
                    "last_activity": channel.last_activity.isoformat()
                }
                channel_list.append(channel_info)
            
            channels_data = {
                "room_id": room_id,
                "room_name": room.name,
                "total_channels": len(channel_list),
                "channels": channel_list,
                "queried_by": context.client_id,
                "queried_at": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success(f"Found {len(channel_list)} channels in room '{room.name}'", channels_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to list channels: {str(e)}", "LIST_CHANNELS_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for list channels command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "list_channels",
            "permissions": ["channel_view"],
            "arguments": {
                "room": "Room ID to list channels for (required)"
            },
            "examples": [
                {
                    "command": "list_channels",
                    "description": "List all channels in a room",
                    "args": {"room": "general"}
                }
            ]
        }


class ChannelInfoCommand(ChannelCommand):
    """Get detailed information about a channel."""
    
    def __init__(self):
        """Initialize channel info command."""
        super().__init__(
            "channel_info",
            "Get detailed information about a channel",
            permissions=["channel_view"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute channel info command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            Channel info command result
        """
        try:
            # Get channel statistics
            channel_stats = await context.channel_manager.get_channel_stats(channel_id)
            
            # Get current members
            members = list(channel.members)
            
            # Compile detailed information
            channel_info = {
                "room_id": room_id,
                "room_name": room.name,
                "channel_id": channel_id,
                "name": channel.name,
                "description": channel.description,
                "member_count": channel.member_count,
                "members": members,
                "created_at": channel.created_at.isoformat(),
                "last_activity": channel.last_activity.isoformat(),
                "statistics": channel_stats,
                "queried_by": context.client_id,
                "queried_at": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success(f"Channel info retrieved for '{channel.name}'", channel_info)
            
        except Exception as e:
            return CommandResult.error(f"Failed to get channel info: {str(e)}", "CHANNEL_INFO_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for channel info command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "channel_info",
            "permissions": ["channel_view"],
            "arguments": {
                "room": "Room ID where the channel exists (required)",
                "channel": "Channel ID to get info for (required)"
            },
            "examples": [
                {
                    "command": "channel_info",
                    "description": "Get detailed channel information",
                    "args": {"room": "general", "channel": "arq_channel_123"}
                }
            ]
        }


class HistoryCommand(ChannelCommand):
    """Get message history for a channel."""
    
    def __init__(self):
        """Initialize history command."""
        super().__init__(
            "history",
            "Get message history for a channel",
            permissions=["channel_view"]
        )
    
    async def _execute_channel_command(
        self,
        context: CommandContext,
        room_id: str,
        channel_id: str,
        room,
        channel
    ) -> CommandResult:
        """Execute history command.
        
        Args:
            context: Command execution context
            room_id: Room identifier
            channel_id: Channel identifier
            room: Room object
            channel: Channel object
            
        Returns:
            History command result
        """
        try:
            # Get command arguments
            limit = context.envelope.args.get("limit", 50)
            since = context.envelope.args.get("since")
            
            # Parse since timestamp if provided
            since_time = None
            if since:
                try:
                    since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
                except ValueError:
                    return CommandResult.error("Invalid 'since' timestamp format", "INVALID_TIMESTAMP")
            
            # Get history from storage if available
            history_entries = []
            if context.storage:
                history_entries = await context.storage.get_channel_history(
                    channel_id=channel_id,
                    limit=limit,
                    since=since_time
                )
            
            # Format history entries
            history = []
            for entry in history_entries:
                history_item = {
                    "message_id": entry.envelope.id,
                    "type": entry.envelope.type,
                    "sender": entry.envelope.sender,
                    "payload": entry.envelope.payload,
                    "timestamp": entry.envelope.timestamp.isoformat(),
                    "stored_at": entry.stored_at.isoformat()
                }
                history.append(history_item)
            
            history_data = {
                "room_id": room_id,
                "room_name": room.name,
                "channel_id": channel_id,
                "channel_name": channel.name,
                "total_messages": len(history),
                "limit": limit,
                "since": since,
                "history": history,
                "queried_by": context.client_id,
                "queried_at": datetime.utcnow().isoformat()
            }
            
            return CommandResult.success(f"Retrieved {len(history)} messages from channel '{channel.name}'", history_data)
            
        except Exception as e:
            return CommandResult.error(f"Failed to get history: {str(e)}", "HISTORY_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for history command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "history",
            "permissions": ["channel_view"],
            "arguments": {
                "room": "Room ID where the channel exists (required)",
                "channel": "Channel ID to get history for (required)",
                "limit": "Maximum number of messages to return (optional, default: 50)",
                "since": "Only return messages after this timestamp (optional, ISO format)"
            },
            "examples": [
                {
                    "command": "history",
                    "description": "Get recent message history",
                    "args": {"room": "general", "channel": "arq_channel_123", "limit": 10}
                }
            ]
        }


class HelpCommand(SystemCommand):
    """Get help information about available commands."""
    
    def __init__(self):
        """Initialize help command."""
        super().__init__("help", "Get help information about available commands")
    
    async def _execute_system_command(self, context: CommandContext) -> CommandResult:
        """Execute help command.
        
        Args:
            context: Command execution context
            
        Returns:
            Help command result
        """
        try:
            # Get command-specific help if requested
            command_name = context.envelope.args.get("command")
            
            if command_name:
                # Get help for specific command
                help_info = await context.message_router.router.executor.get_command_help(command_name)
                if help_info and help_info.get("help"):
                    return CommandResult.success(f"Help for command '{command_name}'", help_info["help"])
                else:
                    return CommandResult.error(f"Command '{command_name}' not found", "COMMAND_NOT_FOUND")
            else:
                # Get help for all commands
                help_info = await context.message_router.router.executor.get_command_help()
                
                # Format help information
                formatted_help = {
                    "available_commands": help_info["total_available"],
                    "commands": help_info["commands"],
                    "categories": help_info["command_categories"],
                    "usage": {
                        "general": "Use 'help <command>' for specific command help",
                        "examples": [
                            "help status",
                            "help create_channel",
                            "help ping"
                        ]
                    },
                    "queried_by": context.client_id,
                    "queried_at": datetime.utcnow().isoformat()
                }
                
                return CommandResult.success(f"ArqonBus commands help ({help_info['total_available']} commands available)", formatted_help)
            
        except Exception as e:
            return CommandResult.error(f"Failed to get help: {str(e)}", "HELP_ERROR")
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for help command.
        
        Returns:
            Help information dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "usage": "help [command]",
            "permissions": [],
            "arguments": {
                "command": "Specific command to get help for (optional)"
            },
            "examples": [
                {"command": "help", "description": "List all available commands"},
                {"command": "help status", "description": "Get help for status command"}
            ]
        }