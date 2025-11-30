"""Command authorization and validation logic for ArqonBus."""
import asyncio
import logging
from typing import Dict, Set, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from .base import CommandAuthorizationError, CommandValidationError
from ..routing.client_registry import ClientRegistry
from ..config.config import get_config


logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permission levels for ArqonBus commands."""
    # System permissions (available to all clients)
    SYSTEM_INFO = "system_info"
    CONNECTIVITY_TEST = "connectivity_test"
    
    # Room management permissions
    ROOM_MANAGEMENT = "room_management"
    ROOM_VIEW = "room_view"
    
    # Channel management permissions
    CHANNEL_MANAGEMENT = "channel_management"
    CHANNEL_ACCESS = "channel_access"
    CHANNEL_VIEW = "channel_view"
    
    # Administrative permissions
    ADMIN_COMMANDS = "admin_commands"
    SERVER_CONTROL = "server_control"
    
    # Storage permissions
    MESSAGE_HISTORY = "message_history"


class Role(Enum):
    """Client roles with associated permissions."""
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SYSTEM = "system"


class AuthorizationManager:
    """Manages client permissions and authorization for commands."""
    
    def __init__(self, client_registry: ClientRegistry):
        """Initialize authorization manager.
        
        Args:
            client_registry: Client registry for managing client information
        """
        self.client_registry = client_registry
        self.config = get_config()
        
        # Role-based permissions
        self._role_permissions = {
            Role.GUEST: {
                Permission.SYSTEM_INFO,
                Permission.CONNECTIVITY_TEST,
                Permission.CHANNEL_VIEW,
                Permission.ROOM_VIEW
            },
            Role.USER: {
                Permission.SYSTEM_INFO,
                Permission.CONNECTIVITY_TEST,
                Permission.CHANNEL_ACCESS,
                Permission.CHANNEL_VIEW,
                Permission.ROOM_VIEW,
                Permission.MESSAGE_HISTORY
            },
            Role.MODERATOR: {
                Permission.SYSTEM_INFO,
                Permission.CONNECTIVITY_TEST,
                Permission.CHANNEL_ACCESS,
                Permission.CHANNEL_VIEW,
                Permission.ROOM_VIEW,
                Permission.MESSAGE_HISTORY,
                Permission.CHANNEL_MANAGEMENT,
                Permission.ROOM_MANAGEMENT
            },
            Role.ADMIN: {
                Permission.SYSTEM_INFO,
                Permission.CONNECTIVITY_TEST,
                Permission.CHANNEL_ACCESS,
                Permission.CHANNEL_VIEW,
                Permission.ROOM_VIEW,
                Permission.MESSAGE_HISTORY,
                Permission.CHANNEL_MANAGEMENT,
                Permission.ROOM_MANAGEMENT,
                Permission.ADMIN_COMMANDS,
                Permission.SERVER_CONTROL
            },
            Role.SYSTEM: set(Permission)  # System has all permissions
        }
        
        # Rate limiting
        self._rate_limits = {
            Permission.CONNECTIVITY_TEST: 10,  # 10 pings per minute
            Permission.SYSTEM_INFO: 5,         # 5 status requests per minute
            Permission.CHANNEL_MANAGEMENT: 20,  # 20 channel ops per minute
            Permission.ROOM_MANAGEMENT: 20,     # 20 room ops per minute
            Permission.MESSAGE_HISTORY: 30      # 30 history requests per minute
        }
        
        # Client activity tracking for rate limiting
        self._client_activity: Dict[str, Dict[str, List[datetime]]] = {}
        
        # Statistics
        self._stats = {
            "authorization_checks": 0,
            "permission_grants": 0,
            "permission_denials": 0,
            "rate_limit_hits": 0,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
    
    async def check_permission(
        self, 
        client_id: str, 
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if client has specific permission.
        
        Args:
            client_id: Client to check
            permission: Permission to check
            context: Additional context (room/channel info)
            
        Returns:
            True if client has permission
        """
        try:
            self._stats["authorization_checks"] += 1
            self._stats["last_activity"] = datetime.utcnow()
            
            # Get client role
            client_role = await self._get_client_role(client_id)
            if not client_role:
                logger.warning(f"Unknown client role for {client_id}")
                return False
            
            # Check role-based permissions
            role_permissions = self._role_permissions.get(client_role, set())
            has_permission = permission in role_permissions
            
            # Additional context-based checks
            if has_permission and context:
                has_permission = await self._check_contextual_permission(
                    client_id, permission, client_role, context
                )
            
            if has_permission:
                self._stats["permission_grants"] += 1
                logger.debug(f"Permission granted: {client_id} -> {permission.value}")
            else:
                self._stats["permission_denials"] += 1
                logger.debug(f"Permission denied: {client_id} -> {permission.value}")
            
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking permission for {client_id}: {e}")
            return False
    
    async def require_permission(
        self,
        client_id: str,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ):
        """Require specific permission, raise error if not available.
        
        Args:
            client_id: Client to check
            permission: Required permission
            context: Additional context
            
        Raises:
            CommandAuthorizationError: If permission not available
            CommandValidationError: If rate limited
        """
        # Check rate limits first
        await self._check_rate_limit(client_id, permission)
        
        # Check permission
        has_permission = await self.check_permission(client_id, permission, context)
        
        if not has_permission:
            raise CommandAuthorizationError(
                f"Client {client_id} lacks permission: {permission.value}"
            )
    
    async def _get_client_role(self, client_id: str) -> Optional[Role]:
        """Get client role from registry.
        
        Args:
            client_id: Client to get role for
            
        Returns:
            Client role or None if not found
        """
        try:
            client_info = await self.client_registry.get_client(client_id)
            if not client_info:
                return None
            
            # Get role from metadata or default to GUEST
            role_name = client_info.metadata.get("role", "guest")
            
            try:
                return Role(role_name)
            except ValueError:
                logger.warning(f"Unknown role '{role_name}' for client {client_id}, defaulting to GUEST")
                return Role.GUEST
                
        except Exception as e:
            logger.error(f"Error getting client role for {client_id}: {e}")
            return None
    
    async def _check_contextual_permission(
        self,
        client_id: str,
        permission: Permission,
        client_role: Role,
        context: Dict[str, Any]
    ) -> bool:
        """Check permission with additional context.
        
        Args:
            client_id: Client to check
            permission: Permission to check
            client_role: Client role
            context: Additional context
            
        Returns:
            True if contextual permission is granted
        """
        # Channel-specific access control
        if "channel_id" in context and permission in [Permission.CHANNEL_ACCESS, Permission.CHANNEL_VIEW]:
            return await self._check_channel_access(client_id, context["channel_id"], client_role)
        
        # Room-specific access control
        if "room_id" in context and permission in [Permission.ROOM_MANAGEMENT, Permission.ROOM_VIEW]:
            return await self._check_room_access(client_id, context["room_id"], client_role)
        
        return True
    
    async def _check_channel_access(
        self,
        client_id: str,
        channel_id: str,
        client_role: Role
    ) -> bool:
        """Check if client can access specific channel.
        
        Args:
            client_id: Client to check
            channel_id: Channel to check access for
            client_role: Client role
            
        Returns:
            True if client can access channel
        """
        # System clients can access all channels
        if client_role == Role.SYSTEM:
            return True
        
        # Admins and moderators can access all channels
        if client_role in [Role.ADMIN, Role.MODERATOR]:
            return True
        
        # Regular users need to be members of the channel
        # This would require checking channel membership
        # For now, allow access (implementation would check actual membership)
        return True
    
    async def _check_room_access(
        self,
        client_id: str,
        room_id: str,
        client_role: Role
    ) -> bool:
        """Check if client can access specific room.
        
        Args:
            client_id: Client to check
            room_id: Room to check access for
            client_role: Client role
            
        Returns:
            True if client can access room
        """
        # System clients can access all rooms
        if client_role == Role.SYSTEM:
            return True
        
        # Admins and moderators can access all rooms
        if client_role in [Role.ADMIN, Role.MODERATOR]:
            return True
        
        # Regular users need to be members of the room
        # This would require checking room membership
        # For now, allow access (implementation would check actual membership)
        return True
    
    async def _check_rate_limit(self, client_id: str, permission: Permission):
        """Check rate limits for client and permission.
        
        Args:
            client_id: Client to check
            permission: Permission being requested
            
        Raises:
            CommandValidationError: If rate limited
        """
        # Get rate limit for permission
        rate_limit = self._rate_limits.get(permission)
        if not rate_limit:
            return  # No rate limit for this permission
        
        # Initialize client activity tracking
        if client_id not in self._client_activity:
            self._client_activity[client_id] = {}
        
        if permission.value not in self._client_activity[client_id]:
            self._client_activity[client_id][permission.value] = []
        
        # Clean old activities (older than 1 minute)
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)
        recent_activities = [
            activity for activity in self._client_activity[client_id][permission.value]
            if activity > cutoff_time
        ]
        self._client_activity[client_id][permission.value] = recent_activities
        
        # Check if rate limit exceeded
        if len(recent_activities) >= rate_limit:
            self._stats["rate_limit_hits"] += 1
            raise CommandValidationError(
                f"Rate limit exceeded for {permission.value}: {rate_limit} requests per minute"
            )
        
        # Record this activity
        recent_activities.append(datetime.utcnow())
    
    async def grant_permission(
        self,
        client_id: str,
        permission: Permission,
        duration: Optional[timedelta] = None
    ) -> bool:
        """Grant temporary permission to client.
        
        Args:
            client_id: Client to grant permission to
            permission: Permission to grant
            duration: How long to grant permission for
            
        Returns:
            True if permission was granted
        """
        try:
            # Get or create client info
            client_info = await self.client_registry.get_client(client_id)
            if not client_info:
                return False
            
            # Grant permission (in a real implementation, this would store temporary permissions)
            # For now, just log the grant
            logger.info(f"Granted permission {permission.value} to client {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error granting permission to {client_id}: {e}")
            return False
    
    async def revoke_permission(
        self,
        client_id: str,
        permission: Permission
    ) -> bool:
        """Revoke permission from client.
        
        Args:
            client_id: Client to revoke permission from
            permission: Permission to revoke
            
        Returns:
            True if permission was revoked
        """
        try:
            # Get client info
            client_info = await self.client_registry.get_client(client_id)
            if not client_info:
                return False
            
            # Revoke permission (in a real implementation, this would remove temporary permissions)
            # For now, just log the revocation
            logger.info(f"Revoked permission {permission.value} from client {client_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error revoking permission from {client_id}: {e}")
            return False
    
    async def get_client_permissions(self, client_id: str) -> Set[Permission]:
        """Get all permissions for a client.
        
        Args:
            client_id: Client to get permissions for
            
        Returns:
            Set of permissions
        """
        try:
            client_role = await self._get_client_role(client_id)
            if not client_role:
                return set()
            
            return self._role_permissions.get(client_role, set()).copy()
            
        except Exception as e:
            logger.error(f"Error getting permissions for {client_id}: {e}")
            return set()
    
    async def get_authorization_stats(self) -> Dict[str, Any]:
        """Get authorization system statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "stats": self._stats.copy(),
            "roles": {
                role.value: len(permissions)
                for role, permissions in self._role_permissions.items()
            },
            "rate_limits": {
                permission.value: limit
                for permission, limit in self._rate_limits.items()
            },
            "active_clients": len(self._client_activity),
            "timestamp": datetime.utcnow()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on authorization system.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_authorization_stats()
            
            health = {
                "status": "healthy",
                "total_checks": stats["stats"]["authorization_checks"],
                "success_rate": stats["stats"]["permission_grants"] / max(1, stats["stats"]["authorization_checks"]),
                "rate_limit_hits": stats["stats"]["rate_limit_hits"],
                "checks": []
            }
            
            # Check for potential issues
            if health["success_rate"] < 0.8:  # Less than 80% success rate
                health["checks"].append({"type": "warning", "message": "Low authorization success rate"})
            
            if stats["stats"]["rate_limit_hits"] > 100:
                health["checks"].append({"type": "warning", "message": "High rate limit hit count"})
            
            # Overall status
            if health["checks"]:
                health["status"] = "degraded"
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }


class CommandValidator:
    """Enhanced command validation with authorization."""
    
    def __init__(self, auth_manager: AuthorizationManager):
        """Initialize command validator.
        
        Args:
            auth_manager: Authorization manager for permission checks
        """
        self.auth_manager = auth_manager
    
    async def validate_command_execution(
        self,
        client_id: str,
        command_name: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate command execution with authorization.
        
        Args:
            client_id: Client executing command
            command_name: Name of command
            args: Command arguments
            context: Additional context
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "authorization": {"granted": True, "permissions": []},
            "rate_limited": False
        }
        
        try:
            # Map command to required permissions
            command_permissions = self._get_command_permissions(command_name)
            
            # Check each required permission
            for permission in command_permissions:
                try:
                    await self.auth_manager.require_permission(client_id, permission, context)
                    validation_result["authorization"]["permissions"].append(permission.value)
                except CommandAuthorizationError as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(str(e))
                    validation_result["authorization"]["granted"] = False
                except CommandValidationError as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(str(e))
                    validation_result["rate_limited"] = True
            
            # Validate arguments
            if args:
                arg_errors = self._validate_command_arguments(command_name, args)
                validation_result["errors"].extend(arg_errors)
                if arg_errors:
                    validation_result["valid"] = False
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _get_command_permissions(self, command_name: str) -> List[Permission]:
        """Get required permissions for a command.
        
        Args:
            command_name: Command name
            
        Returns:
            List of required permissions
        """
        # Map commands to their required permissions
        command_permission_map = {
            "status": [Permission.SYSTEM_INFO],
            "ping": [Permission.CONNECTIVITY_TEST],
            "create_channel": [Permission.CHANNEL_MANAGEMENT],
            "delete_channel": [Permission.CHANNEL_MANAGEMENT],
            "join_channel": [Permission.CHANNEL_ACCESS],
            "leave_channel": [Permission.CHANNEL_ACCESS],
            "list_channels": [Permission.CHANNEL_VIEW],
            "channel_info": [Permission.CHANNEL_VIEW],
            "history": [Permission.MESSAGE_HISTORY],
            "help": [Permission.SYSTEM_INFO]
        }
        
        return command_permission_map.get(command_name, [])
    
    def _validate_command_arguments(self, command_name: str, args: Dict[str, Any]) -> List[str]:
        """Validate command arguments.
        
        Args:
            command_name: Command name
            args: Command arguments
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Basic argument validation
        if not isinstance(args, dict):
            errors.append("Arguments must be a dictionary")
            return errors
        
        # Command-specific validation
        if command_name in ["create_channel", "delete_channel", "join_channel", "leave_channel", "list_channels", "channel_info", "history"]:
            if "room" not in args:
                errors.append("'room' argument is required")
            elif not isinstance(args["room"], str):
                errors.append("'room' argument must be a string")
        
        if command_name in ["create_channel", "delete_channel", "join_channel", "leave_channel", "channel_info", "history"]:
            if "channel" not in args:
                errors.append("'channel' argument is required")
            elif not isinstance(args["channel"], str):
                errors.append("'channel' argument must be a string")
        
        if command_name == "create_channel":
            if "name" not in args and "channel" not in args:
                errors.append("'name' or 'channel' argument is required")
        
        if command_name == "history":
            if "limit" in args and not isinstance(args["limit"], int):
                errors.append("'limit' argument must be an integer")
            if "since" in args and not isinstance(args["since"], str):
                errors.append("'since' argument must be a string")
        
        return errors