import asyncio
import itertools
import json
import time
from datetime import datetime, timezone

import pytest
import websockets

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.ids import generate_message_id
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.security.jwt_auth import issue_hs256_token
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(47650)


def _next_port() -> int:
    return next(_port_sequence)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _recv_command_response(ws, request_id: str) -> dict:
    for _ in range(4):
        frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        if frame.get("type") == "response" and frame.get("request_id") == request_id:
            return frame
    raise AssertionError(f"response for {request_id} not received")


@pytest.mark.asyncio
async def test_tier_omega_disabled_returns_feature_disabled():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "omega-disabled-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.tier_omega.enabled = False
    cfg.storage.enable_persistence = False

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        now = int(time.time())
        admin_token = issue_hs256_token(
            {"sub": "admin", "role": "admin", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )
        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {admin_token}"}) as ws:
            await asyncio.wait_for(ws.recv(), timeout=2.0)
            cmd_id = generate_message_id()
            await ws.send(
                json.dumps(
                    {
                        "id": cmd_id,
                        "type": "command",
                        "timestamp": _now_iso(),
                        "version": "1.0",
                        "command": "op.omega.register_substrate",
                        "args": {"name": "alpha", "kind": "relational"},
                    }
                )
            )
            response = await _recv_command_response(ws, cmd_id)
            assert response["status"] == "error"
            assert response["error_code"] == "FEATURE_DISABLED"
    finally:
        await bus.stop_server()


@pytest.mark.asyncio
async def test_tier_omega_enabled_can_emit_isolated_lab_event():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "omega-enabled-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.tier_omega.enabled = True
    cfg.tier_omega.lab_room = "omega-lab"
    cfg.tier_omega.lab_channel = "signals"
    cfg.storage.enable_persistence = False

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        now = int(time.time())
        admin_token = issue_hs256_token(
            {"sub": "admin", "role": "admin", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )
        observer_token = issue_hs256_token(
            {"sub": "observer", "role": "user", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )

        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {admin_token}"}) as admin_ws:
            async with websockets.connect(
                uri,
                additional_headers={"Authorization": f"Bearer {observer_token}"},
            ) as observer_ws:
                admin_welcome = json.loads(await asyncio.wait_for(admin_ws.recv(), timeout=2.0))
                observer_welcome = json.loads(await asyncio.wait_for(observer_ws.recv(), timeout=2.0))
                observer_id = observer_welcome["payload"]["client_id"]
                await bus.client_registry.join_room_channel(
                    observer_id,
                    cfg.tier_omega.lab_room,
                    cfg.tier_omega.lab_channel,
                )
                assert admin_welcome["payload"]["client_id"]

                register_id = generate_message_id()
                await admin_ws.send(
                    json.dumps(
                        {
                            "id": register_id,
                            "type": "command",
                            "timestamp": _now_iso(),
                            "version": "1.0",
                            "command": "op.omega.register_substrate",
                            "args": {"name": "alpha", "kind": "relational"},
                        }
                    )
                )
                register_resp = await _recv_command_response(admin_ws, register_id)
                assert register_resp["status"] == "success"
                substrate_id = register_resp["payload"]["data"]["substrate_id"]

                emit_id = generate_message_id()
                await admin_ws.send(
                    json.dumps(
                        {
                            "id": emit_id,
                            "type": "command",
                            "timestamp": _now_iso(),
                            "version": "1.0",
                            "command": "op.omega.emit_event",
                            "args": {
                                "substrate_id": substrate_id,
                                "signal": "pulse",
                                "payload": {"value": 42},
                            },
                        }
                    )
                )
                emit_resp = await _recv_command_response(admin_ws, emit_id)
                assert emit_resp["status"] == "success"
                assert emit_resp["payload"]["data"]["signal"] == "pulse"

                lab_event = json.loads(await asyncio.wait_for(observer_ws.recv(), timeout=2.0))
                assert lab_event["type"] == "telemetry"
                omega_event = lab_event["payload"]["omega_event"]
                assert omega_event["signal"] == "pulse"
                assert omega_event["substrate_id"] == substrate_id
    finally:
        await bus.stop_server()
