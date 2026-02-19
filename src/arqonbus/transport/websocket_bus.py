"""WebSocket server for ArqonBus real-time messaging."""
import asyncio
from copy import deepcopy
import json
import logging
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Set, Callable, Any
from urllib.parse import parse_qs, urlsplit
from websockets import Response, serve
from websockets.exceptions import ConnectionClosed
from websockets.datastructures import Headers

from ..protocol.envelope import Envelope
from ..protocol.ids import generate_message_id
from ..protocol.validator import EnvelopeValidator
from ..routing.client_registry import ClientRegistry
from ..config.config import get_config
from ..casil.integration import CasilIntegration
from ..casil.outcome import CASILDecision
from ..security.jwt_auth import JWTAuthError, validate_jwt


logger = logging.getLogger(__name__)


@dataclass
class _WebhookRule:
    rule_id: str
    url: str
    owner_client_id: str
    room: Optional[str] = None
    channel: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: float = 2.0
    created_at: str = ""


@dataclass
class _CronJob:
    job_id: str
    owner_client_id: str
    room: str
    channel: str
    payload: Dict[str, Any]
    delay_seconds: float
    interval_seconds: Optional[float]
    repeat_count: int
    created_at: str


@dataclass
class _OmegaSubstrate:
    substrate_id: str
    name: str
    kind: str
    owner_client_id: str
    metadata: Dict[str, Any]
    created_at: str


class _FeatureDisabledError(RuntimeError):
    """Raised when a feature-flagged command path is disabled."""


class WebSocketBus:
    """WebSocket server for ArqonBus message routing.
    
    Handles:
    - WebSocket connections and disconnections
    - Message parsing and validation
    - Client registration and management
    - Message routing to rooms/channels
    - Connection lifecycle management
    """
    
    def __init__(self, client_registry: ClientRegistry, routing_coordinator: Optional[Any] = None, storage: Optional[Any] = None, config: Optional[Any] = None):
        """Initialize WebSocket bus.
        
        Args:
            client_registry: Client registry for managing connections
            routing_coordinator: Optional routing coordinator for operator management
            storage: Optional MessageStorage backend
            config: Optional configuration object
        """
        self.client_registry = client_registry
        self.routing_coordinator = routing_coordinator
        self.storage = storage
        self.config = config or get_config()
        self.server = None
        self.running = False
        self._server_task = None
        self.casil = CasilIntegration(self.config.casil)
        
        # Connection handlers
        self.message_handlers: Dict[str, Callable] = {
            "message": self._handle_message,
            "command": self._handle_command,
            "response": self._handle_response,
            "telemetry": self._handle_telemetry,
            "operator.join": self._handle_operator_join
        }
        
        # Task delivery loops {client_id: asyncio.Task}
        self._operator_tasks: Dict[str, asyncio.Task] = {}

        # Epoch 2 standard operator state.
        self._webhook_rules: Dict[str, _WebhookRule] = {}
        self._cron_jobs: Dict[str, _CronJob] = {}
        self._cron_tasks: Dict[str, asyncio.Task] = {}
        self._store: Dict[str, Dict[str, Any]] = {}
        self._omega_substrates: Dict[str, _OmegaSubstrate] = {}
        self._omega_events: list[Dict[str, Any]] = []
        self._ops_lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_processed": 0,
            "events_emitted": 0,
            "errors": 0,
            "started_at": None,
            "last_activity": None
        }

    async def start_server(self, host: Optional[str] = None, port: Optional[int] = None):
        """Start the WebSocket server.
        
        Args:
            host: Host to bind to (defaults to config)
            port: Port to bind to (defaults to config)
        """
        if self.running:
            logger.warning("WebSocket server is already running")
            return
        
        host = host or self.config.server.host
        port = port or self.config.websocket.port
        
        logger.info(f"Starting ArqonBus WebSocket server on {host}:{port}")
        
        try:
            compression = "deflate" if self.config.websocket.compression else None

            self.server = await serve(
                self._handle_connection,
                host,
                port,
                max_size=self.config.websocket.max_message_size,
                process_request=self._process_request,
                compression=compression,
                ping_interval=self.config.server.ping_interval,
                ping_timeout=self.config.server.ping_timeout,
                close_timeout=self.config.server.connection_timeout,
                reuse_port=True,
                reuse_address=True
            )
            
            # Connect storage backend
            if self.storage:
                if hasattr(self.storage, "connect"):
                    await self.storage.connect()

                # Verify storage connection
                if not await self.storage.health_check():
                    logger.error("Storage health check failed. Server will not start.")
                    await self.stop_server()
                    raise RuntimeError("Storage health check failed")
            else:
                 logger.warning("Starting WebSocket server without storage backend.")
            
            self.running = True
            self._stats["started_at"] = asyncio.get_event_loop().time()
            self._stats["active_connections"] = 0
            
            logger.info(f"ArqonBus WebSocket server started successfully on {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server."""
        if not self.running or not self.server:
            return
        
        logger.info("Stopping ArqonBus WebSocket server")
        
        self.running = False
        
        # Close all client connections
        clients = await self.client_registry.get_all_clients()
        for client in clients:
            try:
                await self._disconnect_client(client.client_id)
            except Exception as e:
                logger.error(f"Error disconnecting client {client.client_id}: {e}")

        # Cleanup scheduled operator jobs.
        await self._cancel_all_cron_jobs()
        
        # Close server
        self.server.close()
        await self.server.wait_closed()
        
        logger.info("ArqonBus WebSocket server stopped")
    
    async def _process_request(self, connection: Any, request: Any) -> Optional[Response]:
        """Process incoming handshake request for edge authentication."""
        if not self.config.security.enable_authentication:
            return None

        token = self._extract_auth_token(request)
        if not token:
            return self._unauthorized_response("Missing bearer token")

        try:
            claims = validate_jwt(
                token,
                self.config.security.jwt_secret or "",
                allowed_algorithms=[self.config.security.jwt_algorithm],
            )
        except JWTAuthError as exc:
            logger.warning("WebSocket auth rejected: %s", exc)
            return self._unauthorized_response("Invalid token")

        # Persist claims on the connection for later client metadata binding.
        setattr(connection, "_arqon_auth_claims", claims)
        return None

    @staticmethod
    def _unauthorized_response(details: str) -> Response:
        body = (
            '{"error":"Unauthorized","details":"' + details.replace('"', "'") + '"}'
        ).encode("utf-8")
        headers = Headers()
        headers["Content-Type"] = "application/json"
        headers["WWW-Authenticate"] = 'Bearer realm="arqonbus"'
        return Response(401, "Unauthorized", headers, body)

    @staticmethod
    def _extract_auth_token(request: Any) -> Optional[str]:
        headers = getattr(request, "headers", None)
        auth_header = None
        if headers is not None:
            auth_header = headers.get("Authorization") or headers.get("authorization")

        if auth_header:
            parts = auth_header.strip().split(" ", 1)
            if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
                return parts[1].strip()

        raw_path = getattr(request, "path", "")
        if raw_path:
            query = parse_qs(urlsplit(raw_path).query)
            for key in ("token", "access_token", "auth_token"):
                values = query.get(key)
                if values and values[0]:
                    return values[0]

        return None

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_positive_float(raw_value: Any, field_name: str) -> float:
        value = float(raw_value)
        if value <= 0:
            raise ValueError(f"'{field_name}' must be > 0")
        return value

    @staticmethod
    def _parse_positive_int(raw_value: Any, field_name: str) -> int:
        value = int(raw_value)
        if value <= 0:
            raise ValueError(f"'{field_name}' must be > 0")
        return value

    @staticmethod
    def _coerce_bool(raw_value: Any, field_name: str) -> bool:
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, int):
            return bool(raw_value)
        if isinstance(raw_value, str):
            lowered = raw_value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"'{field_name}' must be a boolean")

    @staticmethod
    def _coerce_str_list(raw_value: Any, field_name: str) -> list[str]:
        if isinstance(raw_value, str):
            return [raw_value]
        if isinstance(raw_value, list):
            converted: list[str] = []
            for item in raw_value:
                if not isinstance(item, (str, int, float)):
                    raise ValueError(f"'{field_name}' items must be scalar values")
                converted.append(str(item))
            return converted
        raise ValueError(f"'{field_name}' must be a string or list")

    async def _client_metadata(self, client_id: str) -> Dict[str, Any]:
        client_info = await self.client_registry.get_client(client_id)
        metadata = getattr(client_info, "metadata", None) if client_info else None
        if isinstance(metadata, dict):
            return dict(metadata)
        return {}

    async def _client_is_admin(self, client_id: str) -> bool:
        metadata = await self._client_metadata(client_id)
        return str(metadata.get("role", "")).lower() == "admin"

    async def _default_store_namespace(self, client_id: str) -> str:
        metadata = await self._client_metadata(client_id)
        tenant_id = metadata.get("tenant_id")
        if tenant_id:
            return f"tenant:{tenant_id}"
        return "default"

    async def _send_command_response(
        self,
        client_id: str,
        request_id: str,
        *,
        success: bool,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> None:
        response = Envelope(
            type="response",
            request_id=request_id,
            status="success" if success else "error",
            payload={"message": message, "data": data or {}},
            error_code=error_code,
            sender="arqonbus",
        )
        await self.send_to_client(client_id, response)

    async def _register_webhook_rule(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        url = str(args.get("url", "")).strip()
        if not url:
            raise ValueError("'url' is required")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("'url' must start with http:// or https://")

        room = args.get("room")
        channel = args.get("channel")
        timeout_seconds = self._parse_positive_float(
            args.get("timeout_seconds", 2.0),
            "timeout_seconds",
        )
        headers = args.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError("'headers' must be an object")

        rule = _WebhookRule(
            rule_id=f"wh_{uuid.uuid4().hex[:12]}",
            url=url,
            owner_client_id=client_id,
            room=str(room) if room is not None else None,
            channel=str(channel) if channel is not None else None,
            headers={str(k): str(v) for k, v in headers.items()},
            timeout_seconds=timeout_seconds,
            created_at=self._utc_now_iso(),
        )

        async with self._ops_lock:
            self._webhook_rules[rule.rule_id] = rule

        return {
            "rule_id": rule.rule_id,
            "url": rule.url,
            "room": rule.room,
            "channel": rule.channel,
            "timeout_seconds": rule.timeout_seconds,
            "created_at": rule.created_at,
        }

    async def _unregister_webhook_rule(self, client_id: str, rule_id: str) -> bool:
        is_admin = await self._client_is_admin(client_id)
        async with self._ops_lock:
            rule = self._webhook_rules.get(rule_id)
            if not rule:
                return False
            if rule.owner_client_id != client_id and not is_admin:
                raise PermissionError("Cannot remove webhook rule owned by another client")
            self._webhook_rules.pop(rule_id, None)
        return True

    async def _list_webhook_rules(self, client_id: str) -> Dict[str, Any]:
        is_admin = await self._client_is_admin(client_id)
        async with self._ops_lock:
            rules = list(self._webhook_rules.values())

        visible_rules = []
        for rule in rules:
            if not is_admin and rule.owner_client_id != client_id:
                continue
            visible_rules.append(
                {
                    "rule_id": rule.rule_id,
                    "url": rule.url,
                    "owner_client_id": rule.owner_client_id,
                    "room": rule.room,
                    "channel": rule.channel,
                    "timeout_seconds": rule.timeout_seconds,
                    "created_at": rule.created_at,
                }
            )
        return {"rules": visible_rules, "count": len(visible_rules)}

    async def _remove_webhook_rules_for_client(self, client_id: str) -> None:
        async with self._ops_lock:
            owned_rule_ids = [
                rule_id
                for rule_id, rule in self._webhook_rules.items()
                if rule.owner_client_id == client_id
            ]
            for rule_id in owned_rule_ids:
                self._webhook_rules.pop(rule_id, None)

    @staticmethod
    def _webhook_matches(rule: _WebhookRule, envelope: Envelope) -> bool:
        if rule.room and envelope.room != rule.room:
            return False
        if rule.channel and envelope.channel != rule.channel:
            return False
        return True

    async def _dispatch_webhooks_for_message(
        self,
        envelope: Envelope,
        sender_client_id: str,
    ) -> None:
        async with self._ops_lock:
            rules = [
                rule
                for rule in self._webhook_rules.values()
                if self._webhook_matches(rule, envelope)
            ]

        if not rules:
            return

        payload = {
            "rule_version": "v1",
            "sender_client_id": sender_client_id,
            "envelope": envelope.to_dict(),
        }

        await asyncio.gather(
            *(self._send_webhook_post(rule, payload) for rule in rules),
            return_exceptions=True,
        )

    async def _send_webhook_post(self, rule: _WebhookRule, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        headers.update(rule.headers or {})
        request = urllib.request.Request(rule.url, data=body, headers=headers, method="POST")

        def _post() -> int:
            with urllib.request.urlopen(request, timeout=rule.timeout_seconds) as response:
                return int(getattr(response, "status", 200))

        try:
            status_code = await asyncio.to_thread(_post)
            logger.debug("Webhook %s delivered status=%s", rule.rule_id, status_code)
        except urllib.error.URLError as exc:
            logger.warning("Webhook %s delivery failed: %s", rule.rule_id, exc.reason)
        except Exception as exc:
            logger.warning("Webhook %s delivery error: %s", rule.rule_id, exc)

    async def _schedule_cron_job(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        room = str(args.get("room", "")).strip()
        channel = str(args.get("channel", "")).strip()
        if not room or not channel:
            raise ValueError("'room' and 'channel' are required")

        payload = args.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("'payload' must be an object")

        delay_seconds = self._parse_positive_float(args.get("delay_seconds", 1.0), "delay_seconds")
        interval_raw = args.get("interval_seconds")
        interval_seconds = (
            self._parse_positive_float(interval_raw, "interval_seconds")
            if interval_raw is not None
            else None
        )
        repeat_count = self._parse_positive_int(args.get("repeat_count", 1), "repeat_count")

        if repeat_count > 1 and interval_seconds is None:
            raise ValueError("'interval_seconds' is required when repeat_count > 1")

        job = _CronJob(
            job_id=f"cron_{uuid.uuid4().hex[:12]}",
            owner_client_id=client_id,
            room=room,
            channel=channel,
            payload=payload,
            delay_seconds=delay_seconds,
            interval_seconds=interval_seconds,
            repeat_count=repeat_count,
            created_at=self._utc_now_iso(),
        )

        task = asyncio.create_task(self._run_cron_job(job))
        async with self._ops_lock:
            self._cron_jobs[job.job_id] = job
            self._cron_tasks[job.job_id] = task

        return {
            "job_id": job.job_id,
            "room": job.room,
            "channel": job.channel,
            "delay_seconds": job.delay_seconds,
            "interval_seconds": job.interval_seconds,
            "repeat_count": job.repeat_count,
            "created_at": job.created_at,
        }

    async def _run_cron_job(self, job: _CronJob) -> None:
        try:
            await asyncio.sleep(job.delay_seconds)
            for iteration in range(1, job.repeat_count + 1):
                cron_envelope = Envelope(
                    id=generate_message_id(),
                    type="message",
                    room=job.room,
                    channel=job.channel,
                    payload=job.payload,
                    sender="op-cron",
                    metadata={"cron_job_id": job.job_id, "iteration": iteration},
                )
                if self.config.storage.enable_persistence and self.storage:
                    try:
                        await self.storage.store_message(cron_envelope)
                    except Exception as exc:
                        logger.warning("Cron job %s storage write failed: %s", job.job_id, exc)
                await self.client_registry.broadcast_to_room_channel(
                    cron_envelope,
                    job.room,
                    job.channel,
                    exclude_client_id=None,
                )

                if iteration < job.repeat_count:
                    await asyncio.sleep(job.interval_seconds or 0.0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Cron job %s failed: %s", job.job_id, exc)
        finally:
            async with self._ops_lock:
                self._cron_jobs.pop(job.job_id, None)
                self._cron_tasks.pop(job.job_id, None)

    async def _cancel_cron_job(self, client_id: str, job_id: str) -> bool:
        is_admin = await self._client_is_admin(client_id)
        task = None
        async with self._ops_lock:
            job = self._cron_jobs.get(job_id)
            if not job:
                return False
            if job.owner_client_id != client_id and not is_admin:
                raise PermissionError("Cannot cancel cron job owned by another client")
            task = self._cron_tasks.pop(job_id, None)
            self._cron_jobs.pop(job_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Cron job %s cancelled", job_id)
        return True

    async def _list_cron_jobs(self, client_id: str) -> Dict[str, Any]:
        is_admin = await self._client_is_admin(client_id)
        async with self._ops_lock:
            jobs = list(self._cron_jobs.values())

        visible_jobs = []
        for job in jobs:
            if not is_admin and job.owner_client_id != client_id:
                continue
            visible_jobs.append(
                {
                    "job_id": job.job_id,
                    "owner_client_id": job.owner_client_id,
                    "room": job.room,
                    "channel": job.channel,
                    "delay_seconds": job.delay_seconds,
                    "interval_seconds": job.interval_seconds,
                    "repeat_count": job.repeat_count,
                    "created_at": job.created_at,
                }
            )
        return {"jobs": visible_jobs, "count": len(visible_jobs)}

    async def _cancel_cron_jobs_for_client(self, client_id: str) -> None:
        async with self._ops_lock:
            owned_job_ids = [
                job_id
                for job_id, job in self._cron_jobs.items()
                if job.owner_client_id == client_id
            ]

        for job_id in owned_job_ids:
            try:
                await self._cancel_cron_job(client_id, job_id)
            except Exception:
                logger.warning(
                    "Failed to cleanup cron job %s for disconnected client %s",
                    job_id,
                    client_id,
                )

    async def _cancel_all_cron_jobs(self) -> None:
        async with self._ops_lock:
            items = list(self._cron_tasks.items())
            self._cron_tasks = {}
            self._cron_jobs = {}

        for _, task in items:
            task.cancel()
        for _, task in items:
            try:
                await task
            except asyncio.CancelledError:
                logger.debug("Cron task cancelled during shutdown")
            except Exception as exc:
                logger.warning("Cron task cleanup failed during shutdown: %s", exc)

    async def _store_set(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        key = str(args.get("key", "")).strip()
        if not key:
            raise ValueError("'key' is required")
        namespace = str(args.get("namespace") or await self._default_store_namespace(client_id))
        value = args.get("value")
        if value is None:
            raise ValueError("'value' is required")

        async with self._ops_lock:
            namespace_store = self._store.setdefault(namespace, {})
            existed = key in namespace_store
            namespace_store[key] = value
        return {"namespace": namespace, "key": key, "updated": existed}

    async def _store_get(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        key = str(args.get("key", "")).strip()
        if not key:
            raise ValueError("'key' is required")
        namespace = str(args.get("namespace") or await self._default_store_namespace(client_id))
        async with self._ops_lock:
            namespace_store = self._store.get(namespace, {})
            found = key in namespace_store
            value = namespace_store.get(key)
        return {"namespace": namespace, "key": key, "found": found, "value": value}

    async def _store_delete(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        key = str(args.get("key", "")).strip()
        if not key:
            raise ValueError("'key' is required")
        namespace = str(args.get("namespace") or await self._default_store_namespace(client_id))
        async with self._ops_lock:
            namespace_store = self._store.get(namespace, {})
            deleted = key in namespace_store
            if deleted:
                namespace_store.pop(key, None)
        return {"namespace": namespace, "key": key, "deleted": deleted}

    async def _store_list(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        namespace = str(args.get("namespace") or await self._default_store_namespace(client_id))
        async with self._ops_lock:
            namespace_store = self._store.get(namespace, {})
            keys = sorted(namespace_store.keys())
        return {"namespace": namespace, "count": len(keys), "keys": keys}

    @staticmethod
    def _casil_snapshot(casil_config: Any) -> Dict[str, Any]:
        return {
            "enabled": casil_config.enabled,
            "mode": casil_config.mode,
            "default_decision": casil_config.default_decision,
            "scope_include": list(casil_config.scope.include),
            "scope_exclude": list(casil_config.scope.exclude),
            "max_payload_bytes": casil_config.policies.max_payload_bytes,
            "max_inspect_bytes": casil_config.limits.max_inspect_bytes,
            "max_patterns": casil_config.limits.max_patterns,
            "block_on_probable_secret": casil_config.policies.block_on_probable_secret,
            "redaction_paths": list(casil_config.policies.redaction.paths),
            "redaction_patterns": list(casil_config.policies.redaction.patterns),
            "transport_redaction": casil_config.policies.redaction.transport_redaction,
            "metadata_to_logs": casil_config.metadata.to_logs,
            "metadata_to_telemetry": casil_config.metadata.to_telemetry,
            "metadata_to_envelope": casil_config.metadata.to_envelope,
        }

    async def _reload_casil_policy(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if not await self._client_is_admin(client_id):
            raise PermissionError("Only admin clients can reload CASIL policy")

        candidate = deepcopy(self.config.casil)

        if "enabled" in args:
            candidate.enabled = self._coerce_bool(args["enabled"], "enabled")
        if "mode" in args:
            candidate.mode = str(args["mode"]).strip().lower()
        if "default_decision" in args:
            candidate.default_decision = str(args["default_decision"]).strip().lower()
        if "scope_include" in args:
            candidate.scope.include = self._coerce_str_list(args["scope_include"], "scope_include")
        if "scope_exclude" in args:
            candidate.scope.exclude = self._coerce_str_list(args["scope_exclude"], "scope_exclude")
        if "max_payload_bytes" in args:
            candidate.policies.max_payload_bytes = self._parse_positive_int(
                args["max_payload_bytes"],
                "max_payload_bytes",
            )
        if "max_inspect_bytes" in args:
            candidate.limits.max_inspect_bytes = self._parse_positive_int(
                args["max_inspect_bytes"],
                "max_inspect_bytes",
            )
        if "max_patterns" in args:
            candidate.limits.max_patterns = self._parse_positive_int(args["max_patterns"], "max_patterns")
        if "block_on_probable_secret" in args:
            candidate.policies.block_on_probable_secret = self._coerce_bool(
                args["block_on_probable_secret"],
                "block_on_probable_secret",
            )
        if "redaction_paths" in args:
            candidate.policies.redaction.paths = self._coerce_str_list(args["redaction_paths"], "redaction_paths")
        if "redaction_patterns" in args:
            candidate.policies.redaction.patterns = self._coerce_str_list(
                args["redaction_patterns"],
                "redaction_patterns",
            )
        if "transport_redaction" in args:
            candidate.policies.redaction.transport_redaction = self._coerce_bool(
                args["transport_redaction"],
                "transport_redaction",
            )
        if "metadata_to_logs" in args:
            candidate.metadata.to_logs = self._coerce_bool(args["metadata_to_logs"], "metadata_to_logs")
        if "metadata_to_telemetry" in args:
            candidate.metadata.to_telemetry = self._coerce_bool(
                args["metadata_to_telemetry"],
                "metadata_to_telemetry",
            )
        if "metadata_to_envelope" in args:
            candidate.metadata.to_envelope = self._coerce_bool(
                args["metadata_to_envelope"],
                "metadata_to_envelope",
            )

        errors = []
        if candidate.mode not in ("monitor", "enforce"):
            errors.append(f"Invalid CASIL mode: {candidate.mode}")
        if candidate.default_decision not in ("allow", "block"):
            errors.append(f"Invalid CASIL default_decision: {candidate.default_decision}")
        if candidate.limits.max_inspect_bytes < 0:
            errors.append("CASIL max_inspect_bytes must be non-negative")
        if candidate.limits.max_patterns < 0:
            errors.append("CASIL max_patterns must be non-negative")
        if candidate.policies.max_payload_bytes < 0:
            errors.append("CASIL max_payload_bytes must be non-negative")

        if errors:
            raise ValueError("; ".join(errors))

        async with self._ops_lock:
            self.config.casil = candidate
            self.casil.config = candidate
            self.casil.engine.config = candidate

        return self._casil_snapshot(candidate)

    def _omega_snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self.config.tier_omega.enabled,
            "lab_room": self.config.tier_omega.lab_room,
            "lab_channel": self.config.tier_omega.lab_channel,
            "max_events": self.config.tier_omega.max_events,
            "max_substrates": self.config.tier_omega.max_substrates,
            "substrate_count": len(self._omega_substrates),
            "event_count": len(self._omega_events),
        }

    def _require_omega_enabled(self) -> None:
        if not self.config.tier_omega.enabled:
            raise _FeatureDisabledError("Tier-Omega experimental lane is disabled")

    async def _omega_register_substrate(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        self._require_omega_enabled()
        if not await self._client_is_admin(client_id):
            raise PermissionError("Only admin clients can register Tier-Omega substrates")

        name = str(args.get("name", "")).strip()
        kind = str(args.get("kind", "")).strip()
        metadata = args.get("metadata") or {}
        if not name:
            raise ValueError("'name' is required")
        if not kind:
            raise ValueError("'kind' is required")
        if not isinstance(metadata, dict):
            raise ValueError("'metadata' must be an object")

        substrate = _OmegaSubstrate(
            substrate_id=f"omega_{uuid.uuid4().hex[:12]}",
            name=name,
            kind=kind,
            owner_client_id=client_id,
            metadata=metadata,
            created_at=self._utc_now_iso(),
        )

        async with self._ops_lock:
            max_substrates = max(1, int(self.config.tier_omega.max_substrates))
            if len(self._omega_substrates) >= max_substrates:
                raise ValueError("Tier-Omega substrate limit reached")
            self._omega_substrates[substrate.substrate_id] = substrate

        return {
            "substrate_id": substrate.substrate_id,
            "name": substrate.name,
            "kind": substrate.kind,
            "created_at": substrate.created_at,
        }

    async def _omega_unregister_substrate(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        self._require_omega_enabled()
        if not await self._client_is_admin(client_id):
            raise PermissionError("Only admin clients can unregister Tier-Omega substrates")

        substrate_id = str(args.get("substrate_id", "")).strip()
        if not substrate_id:
            raise ValueError("'substrate_id' is required")

        async with self._ops_lock:
            substrate = self._omega_substrates.pop(substrate_id, None)
            if substrate is None:
                return {"removed": False, "substrate_id": substrate_id, "removed_events": 0}

            previous_count = len(self._omega_events)
            self._omega_events = [
                event for event in self._omega_events if event.get("substrate_id") != substrate_id
            ]
            removed_events = previous_count - len(self._omega_events)

        return {
            "removed": True,
            "substrate_id": substrate_id,
            "name": substrate.name,
            "kind": substrate.kind,
            "removed_events": removed_events,
        }

    async def _omega_list_substrates(self) -> Dict[str, Any]:
        self._require_omega_enabled()
        async with self._ops_lock:
            substrates = list(self._omega_substrates.values())

        payload = []
        for substrate in substrates:
            payload.append(
                {
                    "substrate_id": substrate.substrate_id,
                    "name": substrate.name,
                    "kind": substrate.kind,
                    "owner_client_id": substrate.owner_client_id,
                    "metadata": substrate.metadata,
                    "created_at": substrate.created_at,
                }
            )
        return {"substrates": payload, "count": len(payload)}

    async def _omega_emit_event(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        self._require_omega_enabled()
        if not await self._client_is_admin(client_id):
            raise PermissionError("Only admin clients can emit Tier-Omega events")

        substrate_id = str(args.get("substrate_id", "")).strip()
        signal = str(args.get("signal", "")).strip()
        payload = args.get("payload") or {}
        if not substrate_id:
            raise ValueError("'substrate_id' is required")
        if not signal:
            raise ValueError("'signal' is required")
        if not isinstance(payload, dict):
            raise ValueError("'payload' must be an object")

        async with self._ops_lock:
            if substrate_id not in self._omega_substrates:
                raise ValueError(f"Unknown substrate_id: {substrate_id}")
            event = {
                "event_id": f"omega_evt_{uuid.uuid4().hex[:12]}",
                "substrate_id": substrate_id,
                "signal": signal,
                "payload": payload,
                "emitted_by": client_id,
                "timestamp": self._utc_now_iso(),
            }
            self._omega_events.append(event)
            max_events = max(1, int(self.config.tier_omega.max_events))
            if len(self._omega_events) > max_events:
                self._omega_events = self._omega_events[-max_events:]

        event_envelope = Envelope(
            id=generate_message_id(),
            type="telemetry",
            room=self.config.tier_omega.lab_room,
            channel=self.config.tier_omega.lab_channel,
            payload={"omega_event": event},
            sender="op-omega",
        )
        await self.client_registry.broadcast_to_room_channel(
            event_envelope,
            self.config.tier_omega.lab_room,
            self.config.tier_omega.lab_channel,
            exclude_client_id=None,
        )
        return event

    async def _omega_list_events(self, args: Dict[str, Any]) -> Dict[str, Any]:
        self._require_omega_enabled()
        limit = int(args.get("limit", 50))
        if limit < 1:
            raise ValueError("'limit' must be >= 1")
        substrate_id = str(args.get("substrate_id", "")).strip() or None
        signal = str(args.get("signal", "")).strip() or None
        async with self._ops_lock:
            events = list(self._omega_events)

        if substrate_id:
            events = [event for event in events if event.get("substrate_id") == substrate_id]
        if signal:
            events = [event for event in events if event.get("signal") == signal]

        events = events[-limit:]
        return {
            "events": events,
            "count": len(events),
            "limit": limit,
            "substrate_id": substrate_id,
            "signal": signal,
        }

    async def _omega_clear_events(self, client_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        self._require_omega_enabled()
        if not await self._client_is_admin(client_id):
            raise PermissionError("Only admin clients can clear Tier-Omega events")

        substrate_id = str(args.get("substrate_id", "")).strip() or None
        signal = str(args.get("signal", "")).strip() or None

        async with self._ops_lock:
            previous_count = len(self._omega_events)
            retained = []
            for event in self._omega_events:
                substrate_match = substrate_id is None or event.get("substrate_id") == substrate_id
                signal_match = signal is None or event.get("signal") == signal
                if substrate_match and signal_match:
                    continue
                retained.append(event)
            self._omega_events = retained
            remaining_count = len(self._omega_events)

        removed_count = previous_count - remaining_count
        return {
            "removed_count": removed_count,
            "remaining_count": remaining_count,
            "substrate_id": substrate_id,
            "signal": signal,
        }

    async def _handle_connection(self, websocket: Any):
        """Handle new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            path: Connection path (unused for now)
        """
        client_id = None
        
        try:
            claims = getattr(websocket, "_arqon_auth_claims", None)
            metadata = {}
            if isinstance(claims, dict):
                role = claims.get("role")
                tenant_id = claims.get("tenant_id")
                subject = claims.get("sub")
                if role:
                    metadata["role"] = role
                elif self.config.security.enable_authentication:
                    metadata["role"] = "user"
                if tenant_id:
                    metadata["tenant_id"] = tenant_id
                if subject:
                    metadata["subject"] = subject
            elif self.config.security.enable_authentication:
                metadata["role"] = "user"

            # Register new client
            client_id = await self.client_registry.register_client(
                websocket, metadata=metadata or None
            )
            self._stats["total_connections"] += 1
            self._stats["active_connections"] += 1
            self._stats["last_activity"] = asyncio.get_event_loop().time()
            
            logger.info(f"Client {client_id} connected")
            
            # Send welcome message
            welcome_msg = Envelope(
                type="message",
                payload={"welcome": "Connected to ArqonBus", "client_id": client_id},
                sender="arqonbus"
            )
            await websocket.send(welcome_msg.to_json())
            # Track connection event for telemetry-style stats
            self._stats["events_emitted"] += 1
            
            # Handle incoming messages
            async for message_str in websocket:

                await self._handle_message_from_client(client_id, websocket, message_str)
                
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected normally")
        except Exception as e:
            logger.error(f"Error handling connection for client {client_id}: {e}")
            self._stats["errors"] += 1
        finally:
            # Cleanup on disconnect
            if client_id:
                await self._disconnect_client(client_id)
    
    async def _handle_message_from_client(self, client_id: str, websocket: Any, message_str: str):
        """Handle incoming message from client.
        
        Args:
            client_id: Client who sent the message
            websocket: Client's WebSocket connection
            message_str: Raw message string
        """
        try:
            # Parse and validate message
            envelope, validation_errors = EnvelopeValidator.validate_and_parse_json(message_str)
            
            if validation_errors:
                error_msg = Envelope(
                    type="error",
                    request_id=envelope.id,
                    error="Message validation failed",
                    error_code="VALIDATION_ERROR",
                    payload={"errors": validation_errors},
                    sender="arqonbus"
                )
                await websocket.send(error_msg.to_json())
                return
            
            # Add client info to envelope
            envelope.sender = client_id
            
            # Update client activity
            await self.client_registry.update_client_activity(client_id)
            self._stats["last_activity"] = asyncio.get_event_loop().time()

            # Count messages as soon as they're accepted for processing
            self._stats["messages_processed"] += 1
            if envelope.type == "command":
                self._stats["events_emitted"] += 1

            # CASIL inspection (post-validation, pre-routing)
            if envelope.type in ("message", "command"):
                context = {"client_id": client_id, "room": envelope.room, "channel": envelope.channel}
                casil_outcome = await self.casil.process(envelope, context)
                if casil_outcome.decision == CASILDecision.BLOCK:
                    error_msg = Envelope(
                        type="error",
                        request_id=envelope.id,
                        error="CASIL blocked message",
                        error_code=casil_outcome.reason_code,
                        payload={"reason": casil_outcome.reason_code},
                        sender="arqonbus",
                        room=envelope.room,
                        channel=envelope.channel,
                    )
                    await websocket.send(error_msg.to_json())
                    return
            
            # Route message based on type
            handler = self.message_handlers.get(envelope.type)
            if handler:
                await handler(envelope, client_id)
            else:
                logger.warning(f"Unknown message type: {envelope.type}")

            # Minimal ack responses for legacy tests
            if envelope.type == "message":
                ack = Envelope(
                    id=envelope.id,
                    type="message_response",
                    payload=envelope.payload,
                    sender="arqonbus"
                )
                await websocket.send(ack.to_json())
            elif envelope.type == "command":
                ack = Envelope(
                    id=envelope.id,
                    type="command_response",
                    command=envelope.payload.get("command") if envelope.payload else envelope.command,
                    payload={"result": "ok"},
                    sender="arqonbus"
                )
                await websocket.send(ack.to_json())
            
        except Exception as e:
            logger.error(f"Error processing message from client {client_id}: {e}")
            self._stats["errors"] += 1
            
            # Send error response
            error_msg = Envelope(
                type="error",
                error=f"Internal server error: {str(e)}",
                error_code="INTERNAL_ERROR",
                sender="arqonbus"
            )
            try:
                await websocket.send(error_msg.to_json())
            except Exception as exc:
                logger.warning(
                    "Failed to send error envelope to client %s: %s",
                    client_id,
                    exc,
                )
    
    async def _handle_message(self, envelope: Envelope, client_id: str):
        """Handle regular message routing.
        
        Args:
            envelope: Message envelope
            client_id: Client who sent the message
        """
        if not envelope.room or not envelope.channel:
            logger.warning(f"Message from {client_id} missing room or channel")
            return
        
        # Store message if storage is enabled
        if self.config.storage.enable_persistence:
            if self.storage:
                try:
                    result = await self.storage.store_message(envelope)
                    if not result.success:
                        logger.warning(
                            "Failed to persist message %s from %s: %s",
                            envelope.id,
                            client_id,
                            result.error_message,
                        )
                except Exception as e:
                    logger.error("Message persistence error for %s: %s", envelope.id, e)
        
        # Broadcast to room/channel
        sent_count = await self.client_registry.broadcast_to_room_channel(
            envelope, envelope.room, envelope.channel, exclude_client_id=client_id
        )

        await self._dispatch_webhooks_for_message(envelope, client_id)
        
        logger.debug(f"Broadcasted message from {client_id} to {sent_count} clients in {envelope.room}:{envelope.channel}")
    
    async def _handle_command(self, envelope: Envelope, client_id: str):
        """Handle command messages.
        
        Args:
            envelope: Command envelope
            client_id: Client who sent the command
        """
        args = envelope.args or {}

        try:
            if envelope.command == "op.omega.status":
                data = self._omega_snapshot()
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega lane status",
                    data=data,
                )
                return

            if envelope.command == "op.omega.register_substrate":
                data = await self._omega_register_substrate(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega substrate registered",
                    data=data,
                )
                return

            if envelope.command == "op.omega.list_substrates":
                data = await self._omega_list_substrates()
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega substrates listed",
                    data=data,
                )
                return

            if envelope.command == "op.omega.unregister_substrate":
                data = await self._omega_unregister_substrate(client_id, args)
                if not data.get("removed"):
                    await self._send_command_response(
                        client_id,
                        envelope.id,
                        success=False,
                        message=f"Tier-Omega substrate '{data['substrate_id']}' not found",
                        data={"substrate_id": data["substrate_id"]},
                        error_code="NOT_FOUND",
                    )
                    return
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega substrate removed",
                    data=data,
                )
                return

            if envelope.command == "op.omega.emit_event":
                data = await self._omega_emit_event(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega event emitted",
                    data=data,
                )
                return

            if envelope.command == "op.omega.clear_events":
                data = await self._omega_clear_events(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega events cleared",
                    data=data,
                )
                return

            if envelope.command == "op.omega.list_events":
                data = await self._omega_list_events(args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Tier-Omega events listed",
                    data=data,
                )
                return

            if envelope.command == "op.casil.get":
                data = self._casil_snapshot(self.config.casil)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="CASIL policy snapshot",
                    data=data,
                )
                return

            if envelope.command == "op.casil.reload":
                data = await self._reload_casil_policy(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="CASIL policy reloaded",
                    data=data,
                )
                return

            if envelope.command == "op.webhook.register":
                data = await self._register_webhook_rule(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Webhook rule registered",
                    data=data,
                )
                return

            if envelope.command == "op.webhook.unregister":
                rule_id = str(args.get("rule_id", "")).strip()
                if not rule_id:
                    raise ValueError("'rule_id' is required")
                removed = await self._unregister_webhook_rule(client_id, rule_id)
                if not removed:
                    await self._send_command_response(
                        client_id,
                        envelope.id,
                        success=False,
                        message=f"Webhook rule '{rule_id}' not found",
                        data={"rule_id": rule_id},
                        error_code="NOT_FOUND",
                    )
                    return
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Webhook rule removed",
                    data={"rule_id": rule_id},
                )
                return

            if envelope.command == "op.webhook.list":
                data = await self._list_webhook_rules(client_id)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Webhook rules retrieved",
                    data=data,
                )
                return

            if envelope.command == "op.cron.schedule":
                data = await self._schedule_cron_job(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Cron job scheduled",
                    data=data,
                )
                return

            if envelope.command == "op.cron.cancel":
                job_id = str(args.get("job_id", "")).strip()
                if not job_id:
                    raise ValueError("'job_id' is required")
                cancelled = await self._cancel_cron_job(client_id, job_id)
                if not cancelled:
                    await self._send_command_response(
                        client_id,
                        envelope.id,
                        success=False,
                        message=f"Cron job '{job_id}' not found",
                        data={"job_id": job_id},
                        error_code="NOT_FOUND",
                    )
                    return
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Cron job cancelled",
                    data={"job_id": job_id},
                )
                return

            if envelope.command == "op.cron.list":
                data = await self._list_cron_jobs(client_id)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Cron jobs retrieved",
                    data=data,
                )
                return

            if envelope.command == "op.store.set":
                data = await self._store_set(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Store value written",
                    data=data,
                )
                return

            if envelope.command == "op.store.get":
                data = await self._store_get(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Store value retrieved",
                    data=data,
                )
                return

            if envelope.command == "op.store.delete":
                data = await self._store_delete(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Store value deleted",
                    data=data,
                )
                return

            if envelope.command == "op.store.list":
                data = await self._store_list(client_id, args)
                await self._send_command_response(
                    client_id,
                    envelope.id,
                    success=True,
                    message="Store keys listed",
                    data=data,
                )
                return
        except PermissionError as exc:
            await self._send_command_response(
                client_id,
                envelope.id,
                success=False,
                message=str(exc),
                error_code="AUTHORIZATION_ERROR",
            )
            return
        except _FeatureDisabledError as exc:
            await self._send_command_response(
                client_id,
                envelope.id,
                success=False,
                message=str(exc),
                error_code="FEATURE_DISABLED",
            )
            return
        except (TypeError, ValueError) as exc:
            await self._send_command_response(
                client_id,
                envelope.id,
                success=False,
                message=f"Validation error: {exc}",
                error_code="VALIDATION_ERROR",
            )
            return
        except Exception as exc:
            logger.error("Operator command failed (%s): %s", envelope.command, exc)
            await self._send_command_response(
                client_id,
                envelope.id,
                success=False,
                message=f"Execution error: {exc}",
                error_code="EXECUTION_ERROR",
            )
            return

        if envelope.command == "truth.verify":
            # Bridge to distributed task queue (Phase 2 completion)
            if self.routing_coordinator and self.routing_coordinator.operator_registry:
                storage = self.routing_coordinator.operator_registry.storage
                if storage:
                    # Enqueue to the truth group stream
                    # Enqueue to the truth group stream or channel
                    group = getattr(self.config.casil, "truth_worker_group", "truth_workers")
                    stream = f"arqonbus:group:{group}"
                    
                    # Store data from args or payload
                    job_data = envelope.args or envelope.payload
                    
                    # We use the generic storage.backend.redis_client if possible, 
                    # or just use MessageStorage.store_message with a custom stream name
                    # But store_message uses room/channel. We want a custom stream.
                    if hasattr(storage.backend, "redis_client") and storage.backend.redis_client:
                        # Serialize envelope to dict for stream
                        # Actually we just want the payload/args for the worker
                        await storage.backend.redis_client.xadd(stream, job_data, maxlen=10000)
                        logger.info(f"Routed command {envelope.command} from {client_id} to stream {stream}")
                        
                        # Send ACK to client
                        ack = Envelope(
                            type="response",
                            request_id=envelope.id,
                            status="success",
                            payload={"message": "Task enqueued"},
                            sender="arqonbus"
                        )
                        await self.send_to_client(client_id, ack)
                        return

        # Fallback/Default implementation
        response = Envelope(
            type="message",
            request_id=envelope.id,
            status="pending",
            payload={"message": f"Command {envelope.command} processing not fully implemented"},
            sender="arqonbus"
        )
        await self.send_to_client(client_id, response)
    
    async def _handle_response(self, envelope: Envelope, client_id: str):
        """Handle response messages.
        
        Args:
            envelope: Response envelope
            client_id: Client who sent the response
        """
        logger.debug(f"Received response from {client_id}: {envelope.request_id}")
        
        # Forward to ResultCollector for RSI competing tasks
        if self.routing_coordinator and hasattr(self.routing_coordinator, "collector"):
            if envelope.request_id:
                await self.routing_coordinator.collector.add_result(envelope.request_id, envelope)
        
        # Response handling will be implemented with commands
    
    async def _handle_telemetry(self, envelope: Envelope, client_id: str):
        """Handle telemetry messages.
        
        Args:
            envelope: Telemetry envelope
            client_id: Client who sent the telemetry
        """
        self._stats["events_emitted"] += 1

        # Persist telemetry when storage is enabled.
        if self.config.storage.enable_persistence and self.storage:
            try:
                await self.storage.store_message(
                    envelope,
                    room=envelope.room or "integriguard",
                    channel=envelope.channel or "telemetry-stream",
                )
            except Exception as e:
                logger.error("Telemetry persistence error for %s: %s", envelope.id, e)

        # Broadcast telemetry only when routing hints are present.
        if envelope.room and envelope.channel:
            await self.client_registry.broadcast_to_room_channel(
                envelope,
                envelope.room,
                envelope.channel,
                exclude_client_id=client_id,
            )
        logger.debug(f"Processed telemetry from {client_id}")

    async def _handle_operator_join(self, envelope: Envelope, client_id: str):
        """Handle operator registration for a work group."""
        if not self.routing_coordinator or not self.routing_coordinator.operator_registry:
            logger.error("Operator registry not available")
            return

        payload = envelope.payload or {}
        group = payload.get("group")
        if not group:
            logger.warning(f"Operator {client_id} tried to join without group")
            return
        

        auth_token = payload.get("auth_token", "")
        registered = await self.routing_coordinator.operator_registry.register_operator(
            client_id, group, auth_token=auth_token
        )
        if not registered:
            response = Envelope(
                type="error",
                request_id=envelope.id,
                error="Operator registration denied",
                error_code="OPERATOR_AUTH_FAILED",
                sender="arqonbus",
            )
            await self.send_to_client(client_id, response)
            return
        
        # Start a dedicated push loop for this operator
        task = asyncio.create_task(self._operator_push_loop(client_id, group))
        self._operator_tasks[client_id] = task
        
        logger.info(f"Operator {client_id} registered for group {group}")

    async def _operator_push_loop(self, client_id: str, group: str):
        """Periodically poll Redis for new tasks and push to the operator via WebSocket."""
        if not self.routing_coordinator or not self.routing_coordinator.operator_registry:
            return

        storage = self.routing_coordinator.operator_registry.storage
        if not storage:
            logger.warning("Storage not available for operator push loop")
            return

        stream = f"arqonbus:group:{group}"
        
        try:

            while self.running and client_id in self._operator_tasks:
                # Read 1 job from the group
                # Using client_id as consumer_id ensures exactly-once within the group
                res = await storage.read_group(stream, group, client_id, count=1, block_ms=5000)
                
                if not res:
                    continue

                for _, messages in res:
                    for msg_id, data in messages:
                        # Wrap job in Envelope for delivery
                        task_envelope = Envelope(
                            id=msg_id,
                            type="command",
                            command="truth.verify",
                            payload=data,
                            sender="arqonbus"
                        )
                        
                        await self.send_to_client(client_id, task_envelope)
                        # Note: We don't ACK here; worker must send an ACK command back
                        # Or if we want AUTO-ACK (not recommended for truthloop)
                        
                await asyncio.sleep(0.1) # Breather
                
        except Exception as e:
            logger.error(f"Error in operator push loop for {client_id}: {e}")
        finally:
            self._operator_tasks.pop(client_id, None)

    async def _disconnect_client(self, client_id: str):
        """Disconnect and cleanup a client.
        
        Args:
            client_id: Client to disconnect
        """
        try:
            # Cleanup operator tasks
            task = self._operator_tasks.pop(client_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug("Operator task for %s cancelled", client_id)
            
            # Unregister from operator registry
            if self.routing_coordinator and self.routing_coordinator.operator_registry:
                await self.routing_coordinator.operator_registry.unregister_operator(client_id)

            await self._cancel_cron_jobs_for_client(client_id)
            await self._remove_webhook_rules_for_client(client_id)
            await self.client_registry.unregister_client(client_id)
            self._stats["active_connections"] = max(0, self._stats["active_connections"] - 1)
            logger.info(f"Disconnected client {client_id}")
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")
    
    async def broadcast_message(self, envelope: Envelope, room: str, channel: str) -> int:
        """Broadcast message to all clients in room/channel.
        
        Args:
            envelope: Message to broadcast
            room: Target room
            channel: Target channel
            
        Returns:
            Number of clients who received the message
        """
        return await self.client_registry.broadcast_to_room_channel(envelope, room, channel)
    
    async def send_to_client(self, client_id: str, envelope: Envelope) -> bool:
        """Send message directly to a specific client.
        
        Args:
            client_id: Target client ID
            envelope: Message to send
            
        Returns:
            True if message was sent successfully
        """
        from websockets.exceptions import ConnectionClosed
        try:
            client_info = await self.client_registry.get_client(client_id)
            if client_info:
                await client_info.websocket.send(envelope.to_json())
                return True
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected during send")
            await self._disconnect_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self._disconnect_client(client_id)
            return False
    
    async def get_server_stats(self) -> Dict:
        """Get server statistics.
        
        Returns:
            Dictionary of server statistics
        """
        client_stats = await self.client_registry.get_stats()
        
        return {
            "server": self._stats.copy(),
            "clients": client_stats,
            "config": {
                "host": self.config.server.host,
                "port": self.config.server.port,
                "max_connections": self.config.server.max_connections,
                "ping_interval": self.config.server.ping_interval
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def health_check(self) -> Dict:
        """Perform health check on the WebSocket server.
        
        Returns:
            Health check results
        """
        try:
            stats = await self.get_server_stats()
            
            health = {
                "status": "healthy",
                "uptime": stats["server"]["started_at"] and (asyncio.get_event_loop().time() - stats["server"]["started_at"]),
                "active_connections": stats["server"]["active_connections"],
                "total_messages_routed": self._stats.get("total_messages_routed", 0),
                "routing_errors": self._stats.get("routing_errors", 0),
                "error_rate": float(self._stats.get("routing_errors", 0)) / max(1, int(self._stats.get("total_messages_routed", 0))),
                "checks": []
            }
            
            # Check for potential issues
            if health["error_rate"] > 0.1:  # 10% error rate
                health["checks"].append({"type": "error", "message": "High error rate detected"})
            
            if health["active_connections"] > self.config.server.max_connections * 0.9:
                health["checks"].append({"type": "warning", "message": "Approaching max connection limit"})
            
            # Check client registry health
            client_health = await self.client_registry.health_check()
            if client_health.get("status") != "healthy":
                health["checks"].append({"type": "error", "message": f"Client registry unhealthy: {client_health}"})
            
            return health
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    @property
    def is_running(self) -> bool:
        return self.running and self.server is not None and not getattr(self.server, 'is_closing', lambda: False)()
        """Check if server is currently running."""
        return self.running and self.server is not None and not self.server.is_closing()
    
    @property
    def server_info(self) -> Dict:
        """Get server information."""
        return {
            "host": self.config.server.host,
            "port": self.config.server.port,
            "running": self.is_running,
            "max_connections": self.config.server.max_connections
        }


async def run_server():
    """Run the ArqonBus WebSocket server."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize components
    client_registry = ClientRegistry()
    ws_bus = WebSocketBus(client_registry)
    
    try:
        # Start server
        await ws_bus.start_server()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await ws_bus.stop_server()


if __name__ == "__main__":
    asyncio.run(run_server())
