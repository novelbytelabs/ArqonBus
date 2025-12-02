"""Configuration management for ArqonBus."""
import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "127.0.0.1"
    port: int = 8765
    max_connections: int = 1000
    connection_timeout: float = 30.0
    ping_interval: float = 20.0
    ping_timeout: float = 10.0


@dataclass 
class WebSocketConfig:
    """WebSocket connection configuration."""
    max_message_size: int = 1024 * 1024  # 1MB
    compression: bool = True
    ssl_context: Optional[Dict[str, Any]] = None
    allowed_origins: List[str] = field(default_factory=list)


@dataclass
class RedisConfig:
    """Redis configuration for persistence and streams."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    connection_pool_size: int = 10
    timeout: float = 5.0


@dataclass
class StorageConfig:
    """Storage backend configuration."""
    backend: str = "memory"  # memory, redis
    max_history_size: int = 10000
    retention_hours: int = 24
    enable_persistence: bool = False


@dataclass
class TelemetryConfig:
    """Telemetry and monitoring configuration."""
    enable_telemetry: bool = True
    telemetry_room: str = "arqonbus.telemetry"
    metrics_interval: float = 60.0
    log_level: str = "INFO"


@dataclass
class SecurityConfig:
    """Security and authentication configuration."""
    enable_authentication: bool = False
    allowed_commands: List[str] = field(default_factory=lambda: [
        "status", "ping", "history", "list_channels", "channel_info",
        "create_channel", "delete_channel", "join_channel", "leave_channel"
    ])
    rate_limit_per_minute: int = 60


@dataclass
class CASILLimits:
    """Boundaries for CASIL inspection."""
    max_inspect_bytes: int = 65536
    max_patterns: int = 32


@dataclass
class CASILScope:
    """Scope selection for CASIL inspection."""
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)


@dataclass
class CASILRedactionConfig:
    """Redaction settings for CASIL."""
    paths: List[str] = field(default_factory=lambda: ["password", "token", "secret"])
    patterns: List[str] = field(default_factory=list)
    transport_redaction: bool = False
    never_log_payload_for: List[str] = field(default_factory=list)


@dataclass
class CASILMetadataExposure:
    """Where CASIL metadata can appear."""
    to_logs: bool = True
    to_telemetry: bool = True
    to_envelope: bool = False


@dataclass
class CASILPolicies:
    """Policy definitions for CASIL."""
    max_payload_bytes: int = 262144
    block_on_probable_secret: bool = False
    redaction: CASILRedactionConfig = field(default_factory=CASILRedactionConfig)


@dataclass
class CASILConfig:
    """Main CASIL configuration."""
    enabled: bool = False
    mode: str = "monitor"  # monitor|enforce
    default_decision: str = "allow"  # allow|block
    scope: CASILScope = field(default_factory=CASILScope)
    limits: CASILLimits = field(default_factory=CASILLimits)
    policies: CASILPolicies = field(default_factory=CASILPolicies)
    metadata: CASILMetadataExposure = field(default_factory=CASILMetadataExposure)


@dataclass
class ArqonBusConfig:
    """Main configuration for ArqonBus."""
    server: ServerConfig = field(default_factory=ServerConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    casil: CASILConfig = field(default_factory=CASILConfig)
    
    # Environment-specific overrides
    environment: str = "development"
    debug: bool = False
    
    @classmethod
    def from_environment(cls) -> "ArqonBusConfig":
        """Create configuration from environment variables.
        
        Environment variable prefix: ARQONBUS_
        
        Examples:
            ARQONBUS_SERVER_HOST=0.0.0.0
            ARQONBUS_SERVER_PORT=8080
            ARQONBUS_STORAGE_BACKEND=redis
            ARQONBUS_REDIS_HOST=redis.example.com
        """
        config = cls()
        
        # Server configuration
        config.server.host = os.getenv("ARQONBUS_SERVER_HOST", config.server.host)
        config.server.port = int(os.getenv("ARQONBUS_SERVER_PORT", config.server.port))
        config.server.max_connections = int(os.getenv("ARQONBUS_MAX_CONNECTIONS", config.server.max_connections))
        
        # WebSocket configuration  
        config.websocket.max_message_size = int(os.getenv("ARQONBUS_MAX_MESSAGE_SIZE", config.websocket.max_message_size))
        config.websocket.compression = os.getenv("ARQONBUS_COMPRESSION", "true").lower() == "true"
        
        # Redis configuration
        config.redis.host = os.getenv("ARQONBUS_REDIS_HOST", config.redis.host)
        config.redis.port = int(os.getenv("ARQONBUS_REDIS_PORT", config.redis.port))
        config.redis.password = os.getenv("ARQONBUS_REDIS_PASSWORD")
        config.redis.ssl = os.getenv("ARQONBUS_REDIS_SSL", "false").lower() == "true"
        
        # Storage configuration
        config.storage.backend = os.getenv("ARQONBUS_STORAGE_BACKEND", config.storage.backend)
        config.storage.max_history_size = int(os.getenv("ARQONBUS_MAX_HISTORY_SIZE", config.storage.max_history_size))
        config.storage.enable_persistence = os.getenv("ARQONBUS_ENABLE_PERSISTENCE", "false").lower() == "true"
        
        # Telemetry configuration
        config.telemetry.enable_telemetry = os.getenv("ARQONBUS_ENABLE_TELEMETRY", "true").lower() == "true"
        config.telemetry.telemetry_room = os.getenv("ARQONBUS_TELEMETRY_ROOM", config.telemetry.telemetry_room)
        
        # Security configuration
        config.security.enable_authentication = os.getenv("ARQONBUS_ENABLE_AUTH", "false").lower() == "true"

        # CASIL configuration
        config.casil.enabled = os.getenv("ARQONBUS_CASIL_ENABLED", str(config.casil.enabled)).lower() == "true"
        config.casil.mode = os.getenv("ARQONBUS_CASIL_MODE", config.casil.mode)
        config.casil.default_decision = os.getenv("ARQONBUS_CASIL_DEFAULT_DECISION", config.casil.default_decision)
        include_scope = os.getenv("ARQONBUS_CASIL_SCOPE_INCLUDE")
        if include_scope:
            config.casil.scope.include = [s.strip() for s in include_scope.split(",") if s.strip()]
        exclude_scope = os.getenv("ARQONBUS_CASIL_SCOPE_EXCLUDE")
        if exclude_scope:
            config.casil.scope.exclude = [s.strip() for s in exclude_scope.split(",") if s.strip()]
        config.casil.limits.max_inspect_bytes = int(os.getenv("ARQONBUS_CASIL_MAX_INSPECT_BYTES", config.casil.limits.max_inspect_bytes))
        config.casil.limits.max_patterns = int(os.getenv("ARQONBUS_CASIL_MAX_PATTERNS", config.casil.limits.max_patterns))
        config.casil.policies.max_payload_bytes = int(os.getenv("ARQONBUS_CASIL_MAX_PAYLOAD_BYTES", config.casil.policies.max_payload_bytes))
        config.casil.policies.block_on_probable_secret = os.getenv("ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET", str(config.casil.policies.block_on_probable_secret)).lower() == "true"
        redaction_paths = os.getenv("ARQONBUS_CASIL_REDACTION_PATHS")
        if redaction_paths:
            config.casil.policies.redaction.paths = [p.strip() for p in redaction_paths.split(",") if p.strip()]
        redaction_patterns = os.getenv("ARQONBUS_CASIL_REDACTION_PATTERNS")
        if redaction_patterns:
            config.casil.policies.redaction.patterns = [p.strip() for p in redaction_patterns.split(",") if p.strip()]
        config.casil.policies.redaction.transport_redaction = os.getenv("ARQONBUS_CASIL_TRANSPORT_REDACTION", str(config.casil.policies.redaction.transport_redaction)).lower() == "true"
        never_log_payload_for = os.getenv("ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR")
        if never_log_payload_for:
            config.casil.policies.redaction.never_log_payload_for = [p.strip() for p in never_log_payload_for.split(",") if p.strip()]
        config.casil.metadata.to_logs = os.getenv("ARQONBUS_CASIL_METADATA_TO_LOGS", str(config.casil.metadata.to_logs)).lower() == "true"
        config.casil.metadata.to_telemetry = os.getenv("ARQONBUS_CASIL_METADATA_TO_TELEMETRY", str(config.casil.metadata.to_telemetry)).lower() == "true"
        config.casil.metadata.to_envelope = os.getenv("ARQONBUS_CASIL_METADATA_TO_ENVELOPE", str(config.casil.metadata.to_envelope)).lower() == "true"
        
        # Global configuration
        config.environment = os.getenv("ARQONBUS_ENVIRONMENT", config.environment)
        config.debug = os.getenv("ARQONBUS_DEBUG", "false").lower() == "true"
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Server validation
        if self.server.port < 1 or self.server.port > 65535:
            errors.append(f"Invalid server port: {self.server.port}")
            
        if self.server.max_connections < 1:
            errors.append(f"Invalid max connections: {self.server.max_connections}")
            
        # WebSocket validation
        if self.websocket.max_message_size < 1024:
            errors.append(f"Message size too small: {self.websocket.max_message_size}")
            
        # Redis validation (only if Redis backend is used)
        if self.storage.backend == "redis":
            if not self.redis.host:
                errors.append("Redis host is required when using Redis backend")
            if self.redis.port < 1 or self.redis.port > 65535:
                errors.append(f"Invalid Redis port: {self.redis.port}")
                
        # Storage validation
        if self.storage.max_history_size < 1:
            errors.append(f"Invalid history size: {self.storage.max_history_size}")
            
        # Telemetry validation
        if self.telemetry.metrics_interval < 1:
            errors.append(f"Invalid metrics interval: {self.telemetry.metrics_interval}")
            
        # Security validation
        if self.security.rate_limit_per_minute < 1:
            errors.append(f"Invalid rate limit: {self.security.rate_limit_per_minute}")

        # CASIL validation
        if self.casil.mode not in ("monitor", "enforce"):
            errors.append(f"Invalid CASIL mode: {self.casil.mode}")
        if self.casil.default_decision not in ("allow", "block"):
            errors.append(f"Invalid CASIL default_decision: {self.casil.default_decision}")
        if self.casil.limits.max_inspect_bytes < 0:
            errors.append("CASIL max_inspect_bytes must be non-negative")
        if self.casil.limits.max_patterns < 0:
            errors.append("CASIL max_patterns must be non-negative")
        if self.casil.policies.max_payload_bytes < 0:
            errors.append("CASIL max_payload_bytes must be non-negative")
            
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "max_connections": self.server.max_connections,
                "connection_timeout": self.server.connection_timeout
            },
            "websocket": {
                "max_message_size": self.websocket.max_message_size,
                "compression": self.websocket.compression,
                "allowed_origins": self.websocket.allowed_origins
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db,
                "ssl": self.redis.ssl,
                "connection_pool_size": self.redis.connection_pool_size
            },
            "storage": {
                "backend": self.storage.backend,
                "max_history_size": self.storage.max_history_size,
                "enable_persistence": self.storage.enable_persistence
            },
            "telemetry": {
                "enable_telemetry": self.telemetry.enable_telemetry,
                "telemetry_room": self.telemetry.telemetry_room,
                "metrics_interval": self.telemetry.metrics_interval
            },
            "security": {
                "enable_authentication": self.security.enable_authentication,
                "allowed_commands": self.security.allowed_commands,
                "rate_limit_per_minute": self.security.rate_limit_per_minute
            },
            "casil": {
                "enabled": self.casil.enabled,
                "mode": self.casil.mode,
                "default_decision": self.casil.default_decision,
                "scope": {
                    "include": self.casil.scope.include,
                    "exclude": self.casil.scope.exclude,
                },
                "limits": {
                    "max_inspect_bytes": self.casil.limits.max_inspect_bytes,
                    "max_patterns": self.casil.limits.max_patterns,
                },
                "policies": {
                    "max_payload_bytes": self.casil.policies.max_payload_bytes,
                    "block_on_probable_secret": self.casil.policies.block_on_probable_secret,
                    "redaction": {
                        "paths": self.casil.policies.redaction.paths,
                        "patterns": self.casil.policies.redaction.patterns,
                        "transport_redaction": self.casil.policies.redaction.transport_redaction,
                        "never_log_payload_for": self.casil.policies.redaction.never_log_payload_for,
                    },
                },
                "metadata": {
                    "to_logs": self.casil.metadata.to_logs,
                    "to_telemetry": self.casil.metadata.to_telemetry,
                    "to_envelope": self.casil.metadata.to_envelope,
                },
            },
            "environment": self.environment,
            "debug": self.debug
        }


# Global configuration instance
_config: Optional[ArqonBusConfig] = None


def get_config() -> ArqonBusConfig:
    """Get the global configuration instance.
    
    Creates and loads configuration if not already loaded.
    
    Returns:
        Loaded configuration
    """
    global _config
    if _config is None:
        _config = ArqonBusConfig.from_environment()
        
        # Validate configuration
        errors = _config.validate()
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
            
    return _config


def load_config(environment: str = "development") -> ArqonBusConfig:
    """Load configuration for the given environment.
    
    Args:
        environment: Environment name (development, production, test)
        
    Returns:
        Loaded configuration
    """
    global _config
    _config = ArqonBusConfig.from_environment()
    _config.environment = environment
    return _config


def reload_config() -> ArqonBusConfig:
    """Reload configuration from environment variables.
    
    Returns:
        Reloaded configuration
    """
    global _config
    _config = ArqonBusConfig.from_environment()
    return _config


def validate_config() -> List[str]:
    """Validate current configuration.
    
    Returns:
        List of validation errors
    """
    config = get_config()
    return config.validate()

# Backward compatibility alias for older tests/config consumers
Config = ArqonBusConfig
