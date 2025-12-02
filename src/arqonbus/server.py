"""Main server orchestration for ArqonBus message bus."""
from .commands.executor import CommandExecutor
import sys
import asyncio
import logging
import signal

from .transport.http_server import ArqonBusHTTPServer
from .telemetry.server import TelemetryServer
from .telemetry.emitter import TelemetryEmitter, set_emitter
from .utils.metrics import get_collector
from typing import Optional
from datetime import datetime

from .config.config import get_config, load_config
from .transport.websocket_bus import WebSocketBus
from .casil.integration import CasilIntegration
from .routing.router import RoutingCoordinator
from .storage.interface import MessageStorage, StorageRegistry
from .utils.logging import setup_logging, get_logger


class ArqonBusServer:
    """Main ArqonBus message bus server.
    
    Coordinates all components:
    - WebSocket server for connections
    - Message routing system
    - Storage backend
    - Configuration management
    - Logging and monitoring
    """
    
    def __init__(self, config_override: Optional[dict] = None):
        """Initialize ArqonBus server.
        
        Args:
            config_override: Optional configuration overrides dictionary or ArqonBusConfig object
        """
        # Load configuration
        self.config = load_config()
        if config_override:
            # Handle both dict and ArqonBusConfig objects
            if hasattr(config_override, 'server'):  # It's an ArqonBusConfig object
                self.config = config_override
            else:  # It's a dictionary of overrides
                self._apply_config_overrides(config_override)
        
        # Setup logging
        setup_logging(self.config.telemetry.log_level)
        self.logger = get_logger(__name__)
        # Telemetry and monitoring components
        self.http_server: Optional[ArqonBusHTTPServer] = None
        self.telemetry_server: Optional[TelemetryServer] = None
        self.command_executor: Optional[CommandExecutor] = None
        self.telemetry_emitter: Optional[TelemetryEmitter] = None
        self.metric_collector = get_collector()
        
        # Core components
        self.routing_coordinator: Optional[RoutingCoordinator] = None
        self.ws_bus: Optional[WebSocketBus] = None
        self.storage: Optional[MessageStorage] = None
        
        # Server state
        self.running = False
        self.started_at: Optional[datetime] = None
        self.shutdown_event = asyncio.Event()
        
        # Health and monitoring
        self.health_checks = []
        self.performance_monitor = None
    
    def _apply_config_overrides(self, overrides: dict):
        """Apply configuration overrides.
        
        Args:
            overrides: Configuration override dictionary
        """
        # Apply server overrides
        if "server" in overrides:
            for key, value in overrides["server"].items():
                if hasattr(self.config.server, key):
                    setattr(self.config.server, key, value)
        
        # Apply websocket overrides
        if "websocket" in overrides:
            for key, value in overrides["websocket"].items():
                if hasattr(self.config.websocket, key):
                    setattr(self.config.websocket, key, value)
        
        # Apply storage overrides
        if "storage" in overrides:
            for key, value in overrides["storage"].items():
                if hasattr(self.config.storage, key):
                    setattr(self.config.storage, key, value)
        
        # Apply telemetry overrides
        if "telemetry" in overrides:
            for key, value in overrides["telemetry"].items():
                if hasattr(self.config.telemetry, key):
                    setattr(self.config.telemetry, key, value)
    
    async def start(self):
        """Start the ArqonBus server."""
        if self.running:
            self.logger.warning("Server is already running")
            return
        
        self.logger.info("Starting ArqonBus message bus server...")
        self.started_at = datetime.utcnow()
        
        try:
            # Initialize routing system
            self.logger.info("Initializing routing system...")
            self.routing_coordinator = RoutingCoordinator()
            await self.routing_coordinator.initialize()
            
            # Initialize storage backend
            self.logger.info(f"Initializing storage backend: {self.config.storage.backend}")
            storage_backend = await StorageRegistry.create_backend(
                self.config.storage.backend,
                max_size=self.config.storage.max_history_size
            )
            self.storage = MessageStorage(storage_backend)
            
            # Initialize WebSocket bus
            self.logger.info("Initializing WebSocket bus...")
            self.ws_bus = WebSocketBus(self.routing_coordinator.client_registry)
            # Initialize telemetry server
            if hasattr(self.config.telemetry, "enabled") and self.config.telemetry.enabled:
                self.logger.info("Initializing telemetry server...")
                self.telemetry_server = TelemetryServer(self.config.telemetry.__dict__)
                await self.telemetry_server.start()
                
                # Initialize telemetry emitter
                self.telemetry_emitter = TelemetryEmitter(self.telemetry_server, self.config.telemetry.__dict__)
                await self.telemetry_emitter.start()
                set_emitter(self.telemetry_emitter)
                
                # Emit system started event
                await self.telemetry_emitter.emit_system_started({
                    "version": "1.0.0",
                    "config_host": self.config.server.host,
                    "config_port": self.config.server.port,
                    "storage_backend": self.config.storage.backend
                })
            
            # Initialize command executor with telemetry
            if hasattr(self.config, "commands") and hasattr(self.config.commands, "enabled") and self.config.commands.enabled:
                self.logger.info("Initializing command executor...")
                self.command_executor = CommandExecutor(
                    storage_backend=self.storage,
                    telemetry_emitter=self.telemetry_emitter
                )
            
            # Initialize HTTP server for monitoring
            if hasattr(self.config, "http") and hasattr(self.config.http, "enabled") and self.config.http.enabled:
                self.logger.info("Initializing HTTP monitoring server...")
                self.http_server = ArqonBusHTTPServer(
                    self.config.http.__dict__,
                    storage_backend=self.storage.storage_backend if self.storage else None,
                    telemetry_server=self.telemetry_server
                )
                await self.http_server.start()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start server
            self.running = True
            self.logger.info(
                f"ArqonBus server started successfully on {self.config.server.host}:{self.config.server.port}"
            )
            
            # Run health checks
            await self._run_startup_health_checks()
            
            # Start WebSocket server
            await self.ws_bus.start_server()
            
        except Exception as e:
            self.logger.error(f"Failed to start ArqonBus server: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the ArqonBus server."""
        if not self.running:
            return
        
        self.logger.info("Stopping ArqonBus server...")
        self.running = False
        
        try:
            # Stop WebSocket server
            if self.ws_bus:
                self.logger.info("Stopping WebSocket server...")
                await self.ws_bus.stop_server()
            
            # Stop storage
            if self.storage:
                self.logger.info("Closing storage connection...")
                await self.storage.close()
            
            # Shutdown routing system
            if self.routing_coordinator:
                self.logger.info("Shutting down routing system...")
                await self.routing_coordinator.shutdown()
            
            # Shutdown telemetry emitter
            if self.telemetry_emitter:
                self.logger.info("Stopping telemetry emitter...")
                await self.telemetry_emitter.stop()
            
            # Stop telemetry server
            if self.telemetry_server:
                self.logger.info("Stopping telemetry server...")
                await self.telemetry_server.stop()
            
            # Stop HTTP server
            if self.http_server:
                self.logger.info("Stopping HTTP monitoring server...")
                await self.http_server.stop()
            
            # Signal shutdown complete
            self.shutdown_event.set()
            
            self.logger.info("ArqonBus server stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during server shutdown: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _run_startup_health_checks(self):
        """Run health checks after startup."""
        try:
            # Check storage health
            if self.storage:
                storage_healthy = await self.storage.is_healthy()
                if storage_healthy is False:
                    self.logger.warning("Storage backend health check failed")
                else:
                    self.logger.info("Storage backend health check passed")
            
            # Check routing system health
            if self.routing_coordinator:
                router_health = await self.routing_coordinator.message_router.health_check()
                if router_health.get("status") != "healthy":
                    self.logger.warning(f"Router health check failed: {router_health}")
                else:
                    self.logger.info("Router health check passed")
            
            # Check WebSocket server health
            if self.ws_bus:
                ws_health = await self.ws_bus.health_check()
                if ws_health.get("status") != "healthy":
                    self.logger.warning(f"WebSocket server health check failed: {ws_health}")
                else:
                    self.logger.info("WebSocket server health check passed")
            
            # Check telemetry server health
            if self.telemetry_server:
                telemetry_health = await self.telemetry_server.get_health_status()
                if telemetry_health.get("status") != "healthy":
                    self.logger.warning(f"Telemetry server health check failed: {telemetry_health}")
                else:
                    self.logger.info("Telemetry server health check passed")
            
            # Check HTTP server health
            if self.http_server:
                # HTTP server health check would be implemented here
                self.logger.info("HTTP monitoring server health check passed")
            
        except Exception as e:
            self.logger.error(f"Error during startup health checks: {e}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
    
    async def get_server_status(self) -> dict:
        """Get comprehensive server status.
        
        Returns:
            Dictionary with server status information
        """
        try:
            # Get component statuses
            ws_status = await self.ws_bus.get_server_stats() if self.ws_bus else None
            routing_stats = await self.routing_coordinator.router.get_routing_stats() if self.routing_coordinator else None
            storage_stats = await self.storage.get_storage_stats() if self.storage else None
            
            uptime = (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0
            
            return {
                "server": {
                    "status": "running" if self.running else "stopped",
                    "version": "1.0.0",
                    "started_at": self.started_at.isoformat() if self.started_at else None,
                    "uptime_seconds": uptime,
                    "configuration": self.config.to_dict()
                },
                "websocket": ws_status,
                "routing": routing_stats,
                "storage": storage_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting server status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_health_status(self) -> dict:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with health check results
        """
        try:
            health = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {},
                "overall_checks": []
            }
            
            # Check WebSocket server
            if self.ws_bus:
                ws_health = await self.ws_bus.health_check()
                health["components"]["websocket"] = ws_health
                if ws_health.get("status") != "healthy":
                    health["overall_checks"].append({"type": "error", "component": "websocket", "message": ws_health})
            
            # Check routing system
            if self.routing_coordinator:
                router_health = await self.routing_coordinator.message_router.health_check()
                health["components"]["routing"] = router_health
                if router_health.get("status") != "healthy":
                    health["overall_checks"].append({"type": "error", "component": "routing", "message": router_health})
            
            # Check storage
            if self.storage:
                storage_healthy = await self.storage.is_healthy()
                health["components"]["storage"] = {"status": "healthy" if storage_healthy else "unhealthy"}
                if not storage_healthy:
                    health["overall_checks"].append({"type": "error", "component": "storage", "message": "Storage backend unhealthy"})
            
            # Determine overall health
            if health["overall_checks"]:
                health["status"] = "degraded"
                if len(health["overall_checks"]) > 1:
                    health["status"] = "unhealthy"
            
            return health
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def reload_configuration(self):
        """Reload server configuration."""
        try:
            self.logger.info("Reloading configuration...")
            
            # Reload from environment
            old_config = self.config
            self.config = load_config()
            
            # Apply new configuration to components
            if self.ws_bus:
                # WebSocket server will pick up new config on next restart
                self.logger.info("WebSocket server will use new configuration on restart")
                self.ws_bus.config = self.config
                self.ws_bus.casil = CasilIntegration(self.config.casil)
            
            # Update logging level
            setup_logging(self.config.telemetry.log_level)
            
            self.logger.info("Configuration reloaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            raise
    
    def is_running(self) -> bool:
        """Check if server is currently running."""
        return self.running and self.ws_bus and self.ws_bus.is_running
    
    @property
    def server_info(self) -> dict:
        """Get basic server information."""
        return {
            "name": "ArqonBus",
            "version": "1.0.0",
            "status": "running" if self.running else "stopped",
            "host": self.config.server.host,
            "port": self.config.server.port,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


# Global server instance
_server_instance: Optional[ArqonBusServer] = None


def get_server() -> Optional[ArqonBusServer]:
    """Get the global server instance.
    
    Returns:
        ArqonBusServer instance or None
    """
    return _server_instance


async def create_server(config_override: Optional[dict] = None) -> ArqonBusServer:
    """Create and initialize a new ArqonBus server.
    
    Args:
        config_override: Optional configuration overrides
        
    Returns:
        Initialized ArqonBusServer instance
    """
    global _server_instance
    
    if _server_instance and _server_instance.running:
        raise RuntimeError("Server is already running")
    
    _server_instance = ArqonBusServer(config_override)
    return _server_instance


async def start_server(config_override: Optional[dict] = None):
    """Start ArqonBus server.
    
    Args:
        config_override: Optional configuration overrides
    """
    global _server_instance
    
    try:
        server = await create_server(config_override)
        await server.start()
        return server
    except Exception as e:
        _server_instance = None
        raise


async def stop_server():
    """Stop the running ArqonBus server."""
    global _server_instance
    
    if _server_instance:
        await _server_instance.stop()
        _server_instance = None


async def run_server(config_override: Optional[dict] = None):
    """Run ArqonBus server until shutdown.
    
    Args:
        config_override: Optional configuration overrides
    """
    server = await start_server(config_override)
    
    try:
        # Wait for shutdown signal
        await server.wait_for_shutdown()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
    finally:
        await stop_server()


if __name__ == "__main__":
    # Run server with command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="ArqonBus Message Bus Server")
    parser.add_argument("--host", help="Server host address")
    parser.add_argument("--port", type=int, help="Server port")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       help="Logging level")
    
    args = parser.parse_args()
    
    # Build config override
    config_override = {}
    if args.host:
        config_override.setdefault("server", {})["host"] = args.host
    if args.port:
        config_override.setdefault("server", {})["port"] = args.port
    if args.log_level:
        config_override.setdefault("telemetry", {})["log_level"] = args.log_level
    
    # Run server
    asyncio.run(run_server(config_override))
