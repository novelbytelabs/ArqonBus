"""Configuration management for ArqonBus."""
import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

_ENV_ALIASES = {
    "development": "dev",
    "dev": "dev",
    "staging": "staging",
    "production": "prod",
    "prod": "prod",
}

_STORAGE_BACKEND_ALIASES = {
    "memory": "memory",
    "memory_storage": "memory_storage",
    "redis": "redis",
    "redis_streams": "redis_streams",
    "valkey": "valkey",
    "valkey_streams": "valkey_streams",
    "postgres": "postgres",
    "postgresql": "postgres",
}


def normalize_environment_name(environment: str) -> str:
    """Normalize runtime profile names to dev|staging|prod."""
    normalized = _ENV_ALIASES.get(environment.strip().lower())
    if normalized is None:
        raise ValueError(
            f"Unsupported environment profile: {environment}. "
            "Expected one of: dev, staging, prod."
        )
    return normalized


def normalize_storage_backend_name(backend: str) -> str:
    """Normalize storage backend aliases."""
    normalized = _STORAGE_BACKEND_ALIASES.get(backend.strip().lower())
    if normalized is None:
        raise ValueError(
            f"Unsupported storage backend: {backend}. "
            "Expected one of: memory, redis, redis_streams, valkey, valkey_streams, postgres."
        )
    return normalized


@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "127.0.0.1"
    port: int = 9100
    max_connections: int = 1000
    connection_timeout: float = 30.0
    ping_interval: float = 20.0
    ping_timeout: float = 10.0


@dataclass 
class WebSocketConfig:
    """WebSocket connection configuration."""
    max_message_size: int = 1024 * 1024  # 1MB
    compression: Optional[str] = None
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
class PostgresConfig:
    """Postgres configuration for durable state."""
    host: str = "localhost"
    port: int = 5432
    database: str = "arqonbus"
    user: str = "arqonbus"
    password: Optional[str] = None
    ssl: bool = False
    connect_timeout: float = 5.0


@dataclass
class StorageConfig:
    """Storage backend configuration."""
    backend: str = "memory"  # memory, redis
    mode: str = "degraded"  # degraded, strict
    redis_url: Optional[str] = None
    postgres_url: Optional[str] = None
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
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
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
class TierOmegaConfig:
    """Experimental Tier-Omega lane configuration."""
    enabled: bool = False
    lab_room: str = "omega-lab"
    lab_channel: str = "signals"
    max_events: int = 1000
    max_substrates: int = 128
    runtime: str = "memory"  # memory|firecracker
    firecracker_bin: str = "firecracker"
    jailer_bin: str = "jailer"
    kernel_image: Optional[str] = None
    rootfs_image: Optional[str] = None
    workspace_dir: str = "/tmp/arqonbus-omega"
    vm_timeout_seconds: float = 30.0
    max_vms: int = 8


@dataclass
class ArqonBusConfig:
    """Main configuration for ArqonBus."""
    server: ServerConfig = field(default_factory=ServerConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    postgres: PostgresConfig = field(default_factory=PostgresConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    casil: CASILConfig = field(default_factory=CASILConfig)
    tier_omega: TierOmegaConfig = field(default_factory=TierOmegaConfig)
    
    # Feature Flags
    holonomy_enabled: bool = False
    infra_protocol: str = "protobuf"  # protobuf|json
    allow_json_infra: bool = True
    
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

        def _env_first(*names: str, default: Optional[str] = None) -> Optional[str]:
            for name in names:
                value = os.getenv(name)
                if value is not None:
                    return value
            return default
        
        # Server configuration
        config.server.host = os.getenv("ARQONBUS_SERVER_HOST", config.server.host)
        config.server.port = int(os.getenv("ARQONBUS_SERVER_PORT", config.server.port))
        config.server.max_connections = int(os.getenv("ARQONBUS_MAX_CONNECTIONS", config.server.max_connections))
        
        # WebSocket configuration  
        config.websocket.max_message_size = int(os.getenv("ARQONBUS_MAX_MESSAGE_SIZE", config.websocket.max_message_size))
        compression_val = os.getenv("ARQONBUS_COMPRESSION", "false").lower()
        config.websocket.compression = "deflate" if compression_val == "true" else None
        
        # Redis configuration
        config.redis.host = _env_first(
            "ARQONBUS_VALKEY_HOST",
            "ARQONBUS_REDIS_HOST",
            default=config.redis.host,
        )
        config.redis.port = int(
            _env_first("ARQONBUS_VALKEY_PORT", "ARQONBUS_REDIS_PORT", default=str(config.redis.port))
        )
        config.redis.password = _env_first("ARQONBUS_VALKEY_PASSWORD", "ARQONBUS_REDIS_PASSWORD")
        config.redis.ssl = _env_first(
            "ARQONBUS_VALKEY_SSL",
            "ARQONBUS_REDIS_SSL",
            default="false",
        ).lower() == "true"

        # Postgres configuration
        config.postgres.host = os.getenv("ARQONBUS_POSTGRES_HOST", config.postgres.host)
        config.postgres.port = int(os.getenv("ARQONBUS_POSTGRES_PORT", config.postgres.port))
        config.postgres.database = os.getenv("ARQONBUS_POSTGRES_DATABASE", config.postgres.database)
        config.postgres.user = os.getenv("ARQONBUS_POSTGRES_USER", config.postgres.user)
        config.postgres.password = os.getenv("ARQONBUS_POSTGRES_PASSWORD")
        config.postgres.ssl = os.getenv("ARQONBUS_POSTGRES_SSL", "false").lower() == "true"
        
        # Storage configuration
        raw_backend = os.getenv("ARQONBUS_STORAGE_BACKEND", config.storage.backend)
        config.storage.backend = normalize_storage_backend_name(raw_backend)
        config.storage.mode = os.getenv("ARQONBUS_STORAGE_MODE", config.storage.mode).lower()
        config.storage.redis_url = _env_first(
            "ARQONBUS_VALKEY_URL",
            "ARQONBUS_REDIS_URL",
            default=config.storage.redis_url,
        )
        config.storage.postgres_url = os.getenv("ARQONBUS_POSTGRES_URL", config.storage.postgres_url)
        config.storage.max_history_size = int(os.getenv("ARQONBUS_MAX_HISTORY_SIZE", config.storage.max_history_size))
        config.storage.enable_persistence = os.getenv("ARQONBUS_ENABLE_PERSISTENCE", "false").lower() == "true"
        
        # Telemetry configuration
        config.telemetry.enable_telemetry = os.getenv("ARQONBUS_ENABLE_TELEMETRY", "true").lower() == "true"
        config.telemetry.telemetry_room = os.getenv("ARQONBUS_TELEMETRY_ROOM", config.telemetry.telemetry_room)
        
        # Security configuration
        config.security.enable_authentication = os.getenv("ARQONBUS_ENABLE_AUTH", "false").lower() == "true"
        config.security.jwt_secret = os.getenv("ARQONBUS_AUTH_JWT_SECRET", config.security.jwt_secret)
        config.security.jwt_algorithm = os.getenv("ARQONBUS_AUTH_JWT_ALGORITHM", config.security.jwt_algorithm).upper()

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

        # Tier-Omega experimental lane
        config.tier_omega.enabled = os.getenv(
            "ARQONBUS_OMEGA_ENABLED",
            str(config.tier_omega.enabled),
        ).lower() == "true"
        config.tier_omega.lab_room = os.getenv(
            "ARQONBUS_OMEGA_LAB_ROOM",
            config.tier_omega.lab_room,
        )
        config.tier_omega.lab_channel = os.getenv(
            "ARQONBUS_OMEGA_LAB_CHANNEL",
            config.tier_omega.lab_channel,
        )
        config.tier_omega.max_events = int(
            os.getenv("ARQONBUS_OMEGA_MAX_EVENTS", config.tier_omega.max_events)
        )
        config.tier_omega.max_substrates = int(
            os.getenv("ARQONBUS_OMEGA_MAX_SUBSTRATES", config.tier_omega.max_substrates)
        )
        config.tier_omega.runtime = os.getenv(
            "ARQONBUS_OMEGA_RUNTIME",
            config.tier_omega.runtime,
        ).strip().lower()
        config.tier_omega.firecracker_bin = os.getenv(
            "ARQONBUS_OMEGA_FIRECRACKER_BIN",
            config.tier_omega.firecracker_bin,
        )
        config.tier_omega.jailer_bin = os.getenv(
            "ARQONBUS_OMEGA_JAILER_BIN",
            config.tier_omega.jailer_bin,
        )
        config.tier_omega.kernel_image = os.getenv(
            "ARQONBUS_OMEGA_KERNEL_IMAGE",
            config.tier_omega.kernel_image or "",
        ) or None
        config.tier_omega.rootfs_image = os.getenv(
            "ARQONBUS_OMEGA_ROOTFS_IMAGE",
            config.tier_omega.rootfs_image or "",
        ) or None
        config.tier_omega.workspace_dir = os.getenv(
            "ARQONBUS_OMEGA_WORKSPACE_DIR",
            config.tier_omega.workspace_dir,
        )
        config.tier_omega.vm_timeout_seconds = float(
            os.getenv("ARQONBUS_OMEGA_VM_TIMEOUT_SECONDS", config.tier_omega.vm_timeout_seconds)
        )
        config.tier_omega.max_vms = int(
            os.getenv("ARQONBUS_OMEGA_MAX_VMS", config.tier_omega.max_vms)
        )
        
        # Feature Flags
        config.holonomy_enabled = os.getenv("ARQONBUS_HOLONOMY_ENABLED", "false").lower() == "true"
        
        # Global configuration
        raw_environment = os.getenv("ARQONBUS_ENVIRONMENT", config.environment)
        config.environment = normalize_environment_name(raw_environment)
        config.debug = os.getenv("ARQONBUS_DEBUG", "false").lower() == "true"
        config.infra_protocol = os.getenv("ARQONBUS_INFRA_PROTOCOL", config.infra_protocol).strip().lower()
        allow_json_raw = os.getenv("ARQONBUS_ALLOW_JSON_INFRA")
        if allow_json_raw is None:
            config.allow_json_infra = config.environment == "dev"
        else:
            config.allow_json_infra = allow_json_raw.strip().lower() == "true"
        
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
        if self.storage.backend in ("redis", "redis_streams", "valkey", "valkey_streams"):
            if not self.redis.host:
                errors.append("Redis host is required when using Redis backend")
            if self.redis.port < 1 or self.redis.port > 65535:
                errors.append(f"Invalid Redis port: {self.redis.port}")

        if self.storage.backend == "postgres":
            if not self.postgres.host:
                errors.append("Postgres host is required when using Postgres backend")
            if self.postgres.port < 1 or self.postgres.port > 65535:
                errors.append(f"Invalid Postgres port: {self.postgres.port}")
                
        # Storage validation
        if self.storage.mode not in ("degraded", "strict"):
            errors.append(f"Invalid storage mode: {self.storage.mode}")
        if self.storage.backend not in (
            "memory",
            "memory_storage",
            "redis",
            "redis_streams",
            "valkey",
            "valkey_streams",
            "postgres",
        ):
            errors.append(f"Unsupported storage backend: {self.storage.backend}")
        if self.storage.max_history_size < 1:
            errors.append(f"Invalid history size: {self.storage.max_history_size}")
            
        # Telemetry validation
        if self.telemetry.metrics_interval < 1:
            errors.append(f"Invalid metrics interval: {self.telemetry.metrics_interval}")
            
        # Security validation
        if self.security.rate_limit_per_minute < 1:
            errors.append(f"Invalid rate limit: {self.security.rate_limit_per_minute}")
        if self.security.enable_authentication and not self.security.jwt_secret:
            errors.append("JWT secret is required when authentication is enabled")
        if self.security.jwt_algorithm not in ("HS256",):
            errors.append(f"Unsupported JWT algorithm: {self.security.jwt_algorithm}")
        if self.environment not in ("dev", "staging", "prod"):
            errors.append(f"Unsupported environment profile: {self.environment}")
        if self.infra_protocol not in ("protobuf", "json"):
            errors.append(f"Unsupported infra protocol: {self.infra_protocol}")

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

        # Tier-Omega validation
        if not self.tier_omega.lab_room:
            errors.append("Tier-Omega lab_room must be non-empty")
        if not self.tier_omega.lab_channel:
            errors.append("Tier-Omega lab_channel must be non-empty")
        if self.tier_omega.max_events < 1:
            errors.append("Tier-Omega max_events must be >= 1")
        if self.tier_omega.max_substrates < 1:
            errors.append("Tier-Omega max_substrates must be >= 1")
        if self.tier_omega.runtime not in ("memory", "firecracker"):
            errors.append("Tier-Omega runtime must be one of: memory, firecracker")
        if self.tier_omega.vm_timeout_seconds <= 0:
            errors.append("Tier-Omega vm_timeout_seconds must be > 0")
        if self.tier_omega.max_vms < 1:
            errors.append("Tier-Omega max_vms must be >= 1")
        if self.tier_omega.runtime == "firecracker" and self.tier_omega.enabled:
            if not self.tier_omega.kernel_image:
                errors.append(
                    "Tier-Omega firecracker runtime requires ARQONBUS_OMEGA_KERNEL_IMAGE"
                )
            if not self.tier_omega.rootfs_image:
                errors.append(
                    "Tier-Omega firecracker runtime requires ARQONBUS_OMEGA_ROOTFS_IMAGE"
                )
            
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
            "postgres": {
                "host": self.postgres.host,
                "port": self.postgres.port,
                "database": self.postgres.database,
                "user": self.postgres.user,
                "ssl": self.postgres.ssl,
                "connect_timeout": self.postgres.connect_timeout,
            },
            "storage": {
                "backend": self.storage.backend,
                "mode": self.storage.mode,
                "redis_url": self.storage.redis_url,
                "postgres_url": self.storage.postgres_url,
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
                "jwt_algorithm": self.security.jwt_algorithm,
                "has_jwt_secret": bool(self.security.jwt_secret),
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
            "tier_omega": {
                "enabled": self.tier_omega.enabled,
                "lab_room": self.tier_omega.lab_room,
                "lab_channel": self.tier_omega.lab_channel,
                "max_events": self.tier_omega.max_events,
                "max_substrates": self.tier_omega.max_substrates,
                "runtime": self.tier_omega.runtime,
                "firecracker_bin": self.tier_omega.firecracker_bin,
                "jailer_bin": self.tier_omega.jailer_bin,
                "kernel_image": self.tier_omega.kernel_image,
                "rootfs_image": self.tier_omega.rootfs_image,
                "workspace_dir": self.tier_omega.workspace_dir,
                "vm_timeout_seconds": self.tier_omega.vm_timeout_seconds,
                "max_vms": self.tier_omega.max_vms,
            },
            "environment": self.environment,
            "debug": self.debug,
            "infra_protocol": self.infra_protocol,
            "allow_json_infra": self.allow_json_infra,
        }


# Alias for backward compatibility and test compatibility
Config = ArqonBusConfig

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


def load_config(environment: Optional[str] = None) -> ArqonBusConfig:
    """Load configuration for the given environment.
    
    Args:
        environment: Optional environment override (dev, staging, prod)
        
    Returns:
        Loaded configuration
    """
    global _config
    _config = ArqonBusConfig.from_environment()
    if environment is not None:
        _config.environment = normalize_environment_name(environment)
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


def startup_preflight_errors(config: Optional[ArqonBusConfig] = None) -> List[str]:
    """Return startup preflight errors for stricter production readiness checks.

    Preflight is strict when:
    - `ARQONBUS_PREFLIGHT_STRICT=true`, or
    - `environment=production`.
    """
    cfg = config or get_config()
    errors: List[str] = []

    strict_preflight = os.getenv("ARQONBUS_PREFLIGHT_STRICT", "false").lower() == "true"
    cfg_environment = normalize_environment_name(cfg.environment)
    if cfg_environment in ("staging", "prod"):
        strict_preflight = True

    if not strict_preflight:
        return errors

    required_vars = (
        "ARQONBUS_SERVER_HOST",
        "ARQONBUS_SERVER_PORT",
        "ARQONBUS_STORAGE_MODE",
    )
    for var_name in required_vars:
        if not os.getenv(var_name):
            errors.append(f"Missing required environment variable in strict preflight: {var_name}")

    if cfg.storage.mode == "strict":
        if cfg.storage.backend in ("redis", "redis_streams", "valkey", "valkey_streams"):
            if not (
                cfg.storage.redis_url
                or os.getenv("ARQONBUS_REDIS_URL")
                or os.getenv("ARQONBUS_VALKEY_URL")
            ):
                errors.append(
                    "Storage mode 'strict' with Redis/Valkey backend requires ARQONBUS_REDIS_URL or ARQONBUS_VALKEY_URL"
                )
        elif cfg.storage.backend == "postgres":
            if not (cfg.storage.postgres_url or os.getenv("ARQONBUS_POSTGRES_URL")):
                errors.append("Storage mode 'strict' with Postgres backend requires ARQONBUS_POSTGRES_URL")
        else:
            errors.append(
                "Storage mode 'strict' requires one of: redis, redis_streams, valkey, valkey_streams, postgres"
            )

    # Production policy: require both shared hot-state (Valkey/Redis URL)
    # and durable projection/state (Postgres URL), independent of selected
    # primary storage backend. Can be disabled only with explicit override.
    require_dual_data_stack_raw = os.getenv("ARQONBUS_REQUIRE_DUAL_DATA_STACK")
    if require_dual_data_stack_raw is None:
        require_dual_data_stack = cfg_environment == "prod"
    else:
        require_dual_data_stack = require_dual_data_stack_raw.strip().lower() == "true"

    if require_dual_data_stack:
        if not (
            cfg.storage.redis_url
            or os.getenv("ARQONBUS_REDIS_URL")
            or os.getenv("ARQONBUS_VALKEY_URL")
        ):
            errors.append(
                "Dual data stack requires ARQONBUS_VALKEY_URL (or ARQONBUS_REDIS_URL) for shared hot-state"
            )
        if not (cfg.storage.postgres_url or os.getenv("ARQONBUS_POSTGRES_URL")):
            errors.append(
                "Dual data stack requires ARQONBUS_POSTGRES_URL for durable shared state"
            )

    if cfg_environment == "prod" and os.getenv("JWT_SKIP_VALIDATION") is not None:
        errors.append(
            "JWT_SKIP_VALIDATION is forbidden in production preflight"
        )
    if cfg_environment in ("staging", "prod"):
        if cfg.infra_protocol != "protobuf":
            errors.append("Infrastructure protocol must be protobuf in staging/prod")
        if cfg.allow_json_infra:
            errors.append("ARQONBUS_ALLOW_JSON_INFRA must be false in staging/prod")

    return errors

# Backward compatibility alias for older tests/config consumers
Config = ArqonBusConfig
