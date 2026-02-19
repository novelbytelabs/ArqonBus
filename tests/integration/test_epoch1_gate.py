import asyncio
import itertools
import json
import time
from datetime import datetime, timezone

import pytest
import websockets
from websockets.exceptions import InvalidStatus

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.ids import generate_message_id
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.security.jwt_auth import issue_hs256_token
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(46000)


def _next_port() -> int:
    return next(_port_sequence)


def _status_code(exc: BaseException) -> int | None:
    if hasattr(exc, "status_code"):
        return getattr(exc, "status_code")
    response = getattr(exc, "response", None)
    if response is not None and hasattr(response, "status_code"):
        return response.status_code
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _issue_token(secret: str, *, role: str = "user", tenant_id: str = "tenant-a", ttl: int = 120) -> str:
    now = int(time.time())
    return issue_hs256_token(
        {"sub": "client-subject", "role": role, "tenant_id": tenant_id, "exp": now + ttl},
        secret,
    )


def _make_config(port: int, secret: str) -> ArqonBusConfig:
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = port
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = secret
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = False
    return cfg


@pytest.mark.asyncio
async def test_epoch1_gate_accepts_valid_jwt_and_returns_welcome():
    secret = "epoch1-secret"
    cfg = _make_config(_next_port(), secret)
    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()

    try:
        token = _issue_token(secret)
        uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"
        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token}"}) as ws:
            welcome = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert welcome["type"] == "message"
            assert "welcome" in welcome.get("payload", {})
    finally:
        await bus.stop_server()


@pytest.mark.asyncio
async def test_epoch1_gate_rejects_missing_or_invalid_jwt():
    secret = "epoch1-secret"
    cfg = _make_config(_next_port(), secret)
    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        with pytest.raises(InvalidStatus) as missing_exc:
            async with websockets.connect(uri):
                pass
        assert _status_code(missing_exc.value) == 401

        with pytest.raises(InvalidStatus) as invalid_exc:
            async with websockets.connect(
                uri,
                additional_headers={"Authorization": "Bearer invalid.token.value"},
            ):
                pass
        assert _status_code(invalid_exc.value) == 401
    finally:
        await bus.stop_server()


@pytest.mark.asyncio
async def test_epoch1_gate_rejects_expired_jwt():
    secret = "epoch1-secret"
    cfg = _make_config(_next_port(), secret)
    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()

    try:
        expired = _issue_token(secret, ttl=-1)
        uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"
        with pytest.raises(InvalidStatus) as exc:
            async with websockets.connect(
                uri,
                additional_headers={"Authorization": f"Bearer {expired}"},
            ):
                pass
        assert _status_code(exc.value) == 401
    finally:
        await bus.stop_server()


@pytest.mark.asyncio
async def test_epoch1_gate_authenticated_clients_can_echo_in_same_room():
    secret = "epoch1-secret"
    cfg = _make_config(_next_port(), secret)
    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        token1 = _issue_token(secret, tenant_id="tenant-a")
        token2 = _issue_token(secret, tenant_id="tenant-a")
        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token1}"}) as ws1:
            async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token2}"}) as ws2:
                welcome1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                welcome2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                c1 = welcome1["payload"]["client_id"]
                c2 = welcome2["payload"]["client_id"]

                await bus.client_registry.join_room_channel(c1, "science", "general")
                await bus.client_registry.join_room_channel(c2, "science", "general")

                message = {
                    "id": generate_message_id(),
                    "type": "message",
                    "timestamp": _now_iso(),
                    "version": "1.0",
                    "room": "science",
                    "channel": "general",
                    "payload": {"content": "HELLO"},
                }
                await ws1.send(json.dumps(message))

                received = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                assert received["type"] == "message"
                assert received["payload"]["content"] == "HELLO"
    finally:
        await bus.stop_server()


@pytest.mark.asyncio
async def test_epoch1_gate_casil_policy_blocks_malware_message():
    secret = "epoch1-secret"
    cfg = _make_config(_next_port(), secret)
    cfg.casil.enabled = True
    cfg.casil.mode = "enforce"
    cfg.casil.policies.block_on_probable_secret = True
    cfg.casil.policies.redaction.patterns = [r"malware"]

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        token1 = _issue_token(secret)
        token2 = _issue_token(secret)
        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token1}"}) as ws1:
            async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token2}"}) as ws2:
                welcome1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                welcome2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                c1 = welcome1["payload"]["client_id"]
                c2 = welcome2["payload"]["client_id"]

                await bus.client_registry.join_room_channel(c1, "science", "general")
                await bus.client_registry.join_room_channel(c2, "science", "general")

                blocked_message = {
                    "id": generate_message_id(),
                    "type": "message",
                    "timestamp": _now_iso(),
                    "version": "1.0",
                    "room": "science",
                    "channel": "general",
                    "payload": {"content": "this contains malware"},
                }
                await ws1.send(json.dumps(blocked_message))

                sender_error = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                assert sender_error["type"] == "error"
                assert sender_error["error"] == "CASIL blocked message"

                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(ws2.recv(), timeout=0.3)
    finally:
        await bus.stop_server()
