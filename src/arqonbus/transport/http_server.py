"""HTTP server for ArqonBus monitoring and health endpoints.

This module provides HTTP endpoints for health checks, metrics collection,
and system monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
import time

try:
    from aiohttp import web, web_request, web_response
    from aiohttp.web_runner import AppRunner, TCPSite
    HTTP_SERVER_AVAILABLE = True
except ImportError:
    web = None
    web_request = None
    web_response = None
    HTTP_SERVER_AVAILABLE = False
    # Lightweight stubs for type hints to avoid attribute errors in tests
    class _StubRequest:
        pass
    class _StubResponse:
        pass
    class _StubNamespace:
        Request = _StubRequest
        Response = _StubResponse
    web_request = _StubNamespace()
    web_response = _StubNamespace()

from ..utils.logging import get_logger
from ..utils.metrics import (
    export_prometheus_format,
    get_all_metrics,
    record_counter,
    record_histogram,
)
from .. import __version__

logger = get_logger(__name__)


class ArqonBusHTTPServer:
    """HTTP server for ArqonBus monitoring and health endpoints.
    
    Provides REST endpoints for system monitoring, health checks,
    metrics collection, and administrative functions.
    """
    
    def __init__(self, config: Dict[str, Any], storage_backend=None, telemetry_server=None):
        """Initialize HTTP server.
        
        Args:
            config: Configuration dictionary with HTTP server settings
            storage_backend: Storage backend for history and status queries
            telemetry_server: Telemetry server for metrics and events
        """
        self.config = config
        self.host = config.get("http_host", "localhost")
        self.port = config.get("http_port", 8080)
        self.enabled = config.get("http_enabled", True)
        self.storage_backend = storage_backend
        self.telemetry_server = telemetry_server
        
        # HTTP server
        self.app = None
        self.runner = None
        self.site = None
        self.is_running = False
        
        # Request tracking
        self._request_stats = {
            "total_requests": 0,
            "requests_by_endpoint": {},
            "average_response_time_ms": 0.0,
            "error_count": 0,
            "start_time": time.time()
        }
        
        # Security settings
        self.api_key = config.get("api_key")
        self.cors_origins = config.get("cors_origins", ["*"])
        self.rate_limit = config.get("rate_limit", {"requests_per_minute": 1000})
        
        # Rate limiting
        self._rate_limiters = {}
    
    async def start(self) -> bool:
        """Start the HTTP server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        if not self.enabled:
            logger.info("HTTP server is disabled")
            return False
        
        if not HTTP_SERVER_AVAILABLE:
            logger.warning("aiohttp not available, HTTP server disabled")
            return False
        
        try:
            # Create aiohttp application
            self.app = web.Application(
                client_max_size=10 * 1024 * 1024,  # 10MB
                #middlewares=[self._rate_limit_middleware, self._cors_middleware]
            )
            
            # Set up routes
            self._setup_routes()
            
            # Create and start server
            self.runner = AppRunner(self.app)
            await self.runner.setup()
            
            self.site = TCPSite(
                self.runner,
                self.host,
                self.port
            )
            
            await self.site.start()
            self.is_running = True
            
            logger.info(f"HTTP server started on {self.host}:{self.port}")
            
            # Start background tasks
            asyncio.create_task(self._health_monitor())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self.runner:
            await self.runner.cleanup()
            self.is_running = False
            logger.info("HTTP server stopped")
    
    def _setup_routes(self):
        """Set up HTTP routes."""
        def add_get(path: str, handler):
            self.app.router.add_get(path, self._tracked_handler(path, handler))

        def add_post(path: str, handler):
            self.app.router.add_post(path, self._tracked_handler(path, handler))

        # Health endpoints
        add_get("/health", self.health_check)
        add_get("/status", self.status_check)
        add_get("/version", self.get_version)

        # Metrics endpoints
        add_get("/metrics", self.get_metrics)
        add_get("/metrics/prometheus", self.get_prometheus_metrics)

        # Storage endpoints
        add_get("/storage/history", self.get_storage_history)
        add_get("/storage/stats", self.get_storage_stats)

        # System endpoints
        add_get("/system/info", self.get_system_info)
        add_get("/system/config", self.get_system_config)

        # Telemetry endpoints
        add_get("/telemetry/events", self.get_telemetry_events)
        add_get("/telemetry/stats", self.get_telemetry_stats)

        # Admin endpoints
        add_post("/admin/shutdown", self.admin_shutdown)
        add_post("/admin/restart", self.admin_restart)

    def _tracked_handler(self, endpoint: str, handler):
        """Wrap endpoint handlers with request metrics and latency tracking."""

        async def _wrapped(request):
            started_at = time.perf_counter()
            errored = False
            try:
                response = await handler(request)
                status = getattr(response, "status", 200)
                if status >= 400:
                    errored = True
                return response
            except Exception:
                errored = True
                raise
            finally:
                duration_seconds = max(0.0, time.perf_counter() - started_at)
                self._update_request_stats(endpoint, duration_seconds * 1000.0, error=errored)
                try:
                    labels = {"endpoint": endpoint}
                    record_counter("http_requests_total", 1, labels)
                    record_histogram("http_request_duration_seconds", duration_seconds, labels)
                    if errored:
                        record_counter("http_errors_total", 1, labels)
                except Exception as e:
                    logger.warning("Failed to record HTTP metrics for %s: %s", endpoint, e)

        return _wrapped
    
    async def health_check(self, request: web_request.Request) -> web_response.Response:
        """Basic health check endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Health status response
        """
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "arqonbus"
        })
    
    async def status_check(self, request: web_request.Request) -> web_response.Response:
        """Detailed status check endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Detailed status response
        """
        try:
            # Get system status
            status_data = {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "arqonbus",
                "version": __version__,
                "uptime_seconds": time.time() - self._request_stats["start_time"],
                "endpoints": {
                    "http": self.is_running,
                    "websocket": True,  # Assume WebSocket is working
                    "storage": self.storage_backend is not None,
                    "telemetry": self.telemetry_server is not None if self.telemetry_server else False
                },
                "requests": self._get_request_stats()
            }
            
            # Add storage health if available
            if self.storage_backend:
                try:
                    storage_health = await self.storage_backend.health_check()
                    status_data["storage"] = storage_health
                except Exception as e:
                    status_data["storage"] = {"status": "unhealthy", "error": str(e)}
                    status_data["status"] = "degraded"
            
            # Add telemetry health if available
            if self.telemetry_server:
                try:
                    telemetry_health = await self.telemetry_server.get_health_status()
                    status_data["telemetry"] = telemetry_health
                except Exception as e:
                    status_data["telemetry"] = {"status": "unhealthy", "error": str(e)}
                    status_data["status"] = "degraded"
            
            return web.json_response(status_data)
            
        except Exception as e:
            logger.error(f"Error in status check: {e}")
            return web.json_response({
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }, status=500)

    async def get_version(self, request: web_request.Request) -> web_response.Response:
        """Service version endpoint."""
        return web.json_response(
            {
                "service": "arqonbus",
                "version": __version__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    
    async def get_metrics(self, request: web_request.Request) -> web_response.Response:
        """Get system metrics endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Metrics data response
        """
        try:
            metrics = get_all_metrics()
            metrics["http_server"] = self._get_request_stats()
            return web.json_response(metrics)
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return web.json_response({
                "error": "Failed to get metrics",
                "details": str(e)
            }, status=500)
    
    async def get_prometheus_metrics(self, request: web_request.Request) -> web_response.Response:
        """Get Prometheus-format metrics endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Prometheus format metrics response
        """
        try:
            prometheus_data = export_prometheus_format()
            return web_response.Response(
                text=prometheus_data,
                content_type="text/plain; version=0.0.4; charset=utf-8"
            )
            
        except Exception as e:
            logger.error(f"Error getting Prometheus metrics: {e}")
            return web.json_response({
                "error": "Failed to get Prometheus metrics",
                "details": str(e)
            }, status=500)
    
    async def get_storage_history(self, request: web_request.Request) -> web_response.Response:
        """Get storage history endpoint.
        
        Args:
            request: HTTP request with query parameters
            
        Returns:
            Storage history response
        """
        if not self.storage_backend:
            return web.json_response({"error": "Storage backend not available"}, status=503)
        
        try:
            # Extract query parameters
            client_id = request.query.get("client_id")
            room = request.query.get("room")
            channel = request.query.get("channel")
            limit = int(request.query.get("limit", "50"))
            
            # Get history from storage
            history = await self.storage_backend.get_history(
                client_id=client_id,
                room=room,
                channel=channel,
                limit=limit
            )
            
            # Convert envelopes to dictionaries
            history_data = []
            for envelope in history:
                history_data.append({
                    "id": envelope.id,
                    "type": envelope.type,
                    "timestamp": envelope.timestamp,
                    "from_client": envelope.from_client,
                    "to_client": envelope.to_client,
                    "room": envelope.room,
                    "channel": envelope.channel,
                    "payload": envelope.payload
                })
            
            return web.json_response({
                "history": history_data,
                "count": len(history_data),
                "query": {
                    "client_id": client_id,
                    "room": room,
                    "channel": channel,
                    "limit": limit
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting storage history: {e}")
            return web.json_response({
                "error": "Failed to get storage history",
                "details": str(e)
            }, status=500)
    
    async def get_storage_stats(self, request: web_request.Request) -> web_response.Response:
        """Get storage statistics endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Storage statistics response
        """
        if not self.storage_backend:
            return web.json_response({"error": "Storage backend not available"}, status=503)
        
        try:
            stats = await self.storage_backend.get_storage_stats()
            return web.json_response(stats)
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return web.json_response({
                "error": "Failed to get storage stats",
                "details": str(e)
            }, status=500)
    
    async def get_system_info(self, request: web_request.Request) -> web_response.Response:
        """Get system information endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            System information response
        """
        try:
            info = {
                "service": "arqonbus",
                "version": __version__,
                "description": "ArqonBus Core Message Bus",
                "architecture": {
                    "transport": "WebSocket",
                    "protocol": "JSON Envelope",
                    "storage": "Redis Streams (optional)",
                    "telemetry": "WebSocket",
                    "monitoring": "HTTP Endpoints"
                },
                "features": {
                    "real_time_messaging": True,
                    "room_routing": True,
                    "channel_routing": True,
                    "message_history": True,
                    "command_system": True,
                    "telemetry": True,
                    "persistence": True
                },
                "endpoints": {
                    "websocket": f'ws://{self.config.get("host", "localhost")}:{self.config.get("port", 9100)}',
                    "http": f"http://{self.host}:{self.port}",
                    "telemetry": (
                        f'ws://{self.config.get("host", "localhost")}:{self.config.get("telemetry_port", 8081)}'
                    ),
                }
            }
            
            return web.json_response(info)
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return web.json_response({
                "error": "Failed to get system info",
                "details": str(e)
            }, status=500)
    
    async def get_system_config(self, request: web_request.Request) -> web_response.Response:
        """Get system configuration endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            System configuration response (sanitized)
        """
        try:
            # Return sanitized configuration
            sanitized_config = {
                "server": {
                    "host": self.host,
                    "port": self.port,
                    "enabled": self.enabled
                },
                "storage": {
                    "type": "redis_streams" if hasattr(self.storage_backend, 'redis_client') else "memory",
                    "available": self.storage_backend is not None
                },
                "telemetry": {
                    "enabled": self.telemetry_server is not None,
                    "host": self.telemetry_server.host if self.telemetry_server else None,
                    "port": self.telemetry_server.port if self.telemetry_server else None
                },
                "features": {
                    "cors": self.cors_origins,
                    "rate_limiting": self.rate_limit is not None
                }
            }
            
            return web.json_response(sanitized_config)
            
        except Exception as e:
            logger.error(f"Error getting system config: {e}")
            return web.json_response({
                "error": "Failed to get system config",
                "details": str(e)
            }, status=500)
    
    async def get_telemetry_events(self, request: web_request.Request) -> web_response.Response:
        """Get telemetry events endpoint.
        
        Args:
            request: HTTP request with query parameters
            
        Returns:
            Telemetry events response
        """
        if not self.telemetry_server:
            return web.json_response({"error": "Telemetry server not available"}, status=503)
        
        try:
            # Get performance metrics
            metrics = await self.telemetry_server.get_performance_metrics()
            return web.json_response(metrics)
            
        except Exception as e:
            logger.error(f"Error getting telemetry events: {e}")
            return web.json_response({
                "error": "Failed to get telemetry events",
                "details": str(e)
            }, status=500)
    
    async def get_telemetry_stats(self, request: web_request.Request) -> web_response.Response:
        """Get telemetry statistics endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Telemetry statistics response
        """
        if not self.telemetry_server:
            return web.json_response({"error": "Telemetry server not available"}, status=503)
        
        try:
            health = await self.telemetry_server.get_health_status()
            return web.json_response(health)
            
        except Exception as e:
            logger.error(f"Error getting telemetry stats: {e}")
            return web.json_response({
                "error": "Failed to get telemetry stats",
                "details": str(e)
            }, status=500)

    def _is_admin_request_authorized(self, request: web_request.Request) -> bool:
        """Validate admin request authorization.

        If no API key is configured, admin endpoints are treated as local/dev open.
        """
        if not self.api_key:
            return True
        provided = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        return provided == self.api_key
    
    async def admin_shutdown(self, request: web_request.Request) -> web_response.Response:
        """Admin shutdown endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Shutdown response
        """
        if not self._is_admin_request_authorized(request):
            return web.json_response(
                {"error": "Unauthorized", "details": "Valid X-API-Key required"},
                status=401,
            )
        logger.warning("Admin shutdown requested via HTTP endpoint")
        
        try:
            # Schedule shutdown
            asyncio.create_task(self._shutdown_server())
            
            return web.json_response({
                "status": "shutdown_initiated",
                "message": "Server shutdown initiated"
            })
            
        except Exception as e:
            logger.error(f"Error in admin shutdown: {e}")
            return web.json_response({
                "error": "Failed to initiate shutdown",
                "details": str(e)
            }, status=500)
    
    async def admin_restart(self, request: web_request.Request) -> web_response.Response:
        """Admin restart endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            Restart response
        """
        if not self._is_admin_request_authorized(request):
            return web.json_response(
                {"error": "Unauthorized", "details": "Valid X-API-Key required"},
                status=401,
            )
        logger.warning("Admin restart requested via HTTP endpoint")
        
        try:
            # Schedule restart
            asyncio.create_task(self._restart_server())
            
            return web.json_response({
                "status": "restart_initiated",
                "message": "Server restart initiated"
            })
            
        except Exception as e:
            logger.error(f"Error in admin restart: {e}")
            return web.json_response({
                "error": "Failed to initiate restart",
                "details": str(e)
            }, status=500)
    
    async def _shutdown_server(self):
        """Shutdown the server."""
        await asyncio.sleep(1)  # Give time for response
        await self.stop()
        logger.info("HTTP shutdown sequence completed")
    
    async def _restart_server(self):
        """Restart the server."""
        await asyncio.sleep(1)  # Give time for response
        await self.stop()
        await self.start()
        logger.info("HTTP restart sequence completed")
    
    async def _health_monitor(self):
        """Monitor HTTP server health."""
        while self.is_running:
            try:
                # Log server status periodically
                if self._request_stats["total_requests"] % 100 == 0 and self._request_stats["total_requests"] > 0:
                    stats = self._get_request_stats()
                    logger.info(f"HTTP server stats: {stats['total_requests']} requests, "
                               f"{stats['average_response_time_ms']:.2f}ms avg response time")
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in HTTP health monitor: {e}")
    
    def _get_request_stats(self) -> Dict[str, Any]:
        """Get current request statistics.
        
        Returns:
            Dictionary with request statistics
        """
        return {
            "total_requests": self._request_stats["total_requests"],
            "requests_by_endpoint": self._request_stats["requests_by_endpoint"].copy(),
            "average_response_time_ms": round(self._request_stats["average_response_time_ms"], 2),
            "error_count": self._request_stats["error_count"],
            "uptime_seconds": time.time() - self._request_stats["start_time"]
        }
    
    def _update_request_stats(self, endpoint: str, response_time_ms: float, error: bool = False):
        """Update request statistics.
        
        Args:
            endpoint: Request endpoint
            response_time_ms: Response time in milliseconds
            error: Whether the request resulted in an error
        """
        self._request_stats["total_requests"] += 1
        
        # Update endpoint stats
        if endpoint not in self._request_stats["requests_by_endpoint"]:
            self._request_stats["requests_by_endpoint"][endpoint] = {
                "count": 0,
                "total_time_ms": 0,
                "errors": 0
            }
        
        endpoint_stats = self._request_stats["requests_by_endpoint"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["total_time_ms"] += response_time_ms
        
        if error:
            endpoint_stats["errors"] += 1
            self._request_stats["error_count"] += 1
        
        # Update average response time
        total_time = self._request_stats["average_response_time_ms"] * (self._request_stats["total_requests"] - 1)
        total_time += response_time_ms
        self._request_stats["average_response_time_ms"] = total_time / self._request_stats["total_requests"]
