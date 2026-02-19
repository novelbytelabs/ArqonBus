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

_port_sequence = itertools.count(47550)


def _next_port() -> int:
    return next(_port_sequence)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_casil_mode_can_be_reloaded_without_restart():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "casil-reload-e2e-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = False

    cfg.casil.enabled = True
    cfg.casil.mode = "monitor"
    cfg.casil.policies.block_on_probable_secret = True
    cfg.casil.policies.redaction.patterns = [r"token"]

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        now = int(time.time())
        admin_token = issue_hs256_token(
            {"sub": "admin", "role": "admin", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )
        user_token_1 = issue_hs256_token(
            {"sub": "user-1", "role": "user", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )
        user_token_2 = issue_hs256_token(
            {"sub": "user-2", "role": "user", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )

        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {admin_token}"}) as admin_ws:
            async with websockets.connect(
                uri,
                additional_headers={"Authorization": f"Bearer {user_token_1}"},
            ) as sender_ws:
                async with websockets.connect(
                    uri,
                    additional_headers={"Authorization": f"Bearer {user_token_2}"},
                ) as receiver_ws:
                    admin_welcome = json.loads(await asyncio.wait_for(admin_ws.recv(), timeout=2.0))
                    sender_welcome = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout=2.0))
                    receiver_welcome = json.loads(await asyncio.wait_for(receiver_ws.recv(), timeout=2.0))
                    sender_id = sender_welcome["payload"]["client_id"]
                    receiver_id = receiver_welcome["payload"]["client_id"]

                    await bus.client_registry.join_room_channel(sender_id, "science", "general")
                    await bus.client_registry.join_room_channel(receiver_id, "science", "general")
                    assert admin_welcome["payload"]["client_id"]

                    monitor_message_id = generate_message_id()
                    monitor_message = {
                        "id": monitor_message_id,
                        "type": "message",
                        "timestamp": _now_iso(),
                        "version": "1.0",
                        "room": "science",
                        "channel": "general",
                        "payload": {"content": "token-value-123"},
                    }
                    await sender_ws.send(json.dumps(monitor_message))
                    sender_ack = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout=2.0))
                    assert sender_ack["type"] == "message_response"
                    assert sender_ack["id"] == monitor_message_id

                    receiver_first = json.loads(await asyncio.wait_for(receiver_ws.recv(), timeout=2.0))
                    assert receiver_first["type"] == "message"

                    reload_id = generate_message_id()
                    reload_cmd = {
                        "id": reload_id,
                        "type": "command",
                        "timestamp": _now_iso(),
                        "version": "1.0",
                        "command": "op.casil.reload",
                        "args": {"mode": "enforce"},
                    }
                    await admin_ws.send(json.dumps(reload_cmd))
                    saw_reload_success = False
                    for _ in range(3):
                        response = json.loads(await asyncio.wait_for(admin_ws.recv(), timeout=2.0))
                        if (
                            response.get("type") == "response"
                            and response.get("request_id") == reload_id
                            and response.get("status") == "success"
                        ):
                            saw_reload_success = True
                            assert response["payload"]["data"]["mode"] == "enforce"
                            break
                    assert saw_reload_success is True
                    assert bus.is_running is True

                    enforce_message_id = generate_message_id()
                    enforce_message = {
                        "id": enforce_message_id,
                        "type": "message",
                        "timestamp": _now_iso(),
                        "version": "1.0",
                        "room": "science",
                        "channel": "general",
                        "payload": {"content": "token-value-456"},
                    }
                    await sender_ws.send(json.dumps(enforce_message))
                    blocked = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout=2.0))
                    assert blocked["type"] == "error"
                    assert blocked["request_id"] == enforce_message_id
                    assert blocked["error"] == "CASIL blocked message"

                    with pytest.raises(asyncio.TimeoutError):
                        await asyncio.wait_for(receiver_ws.recv(), timeout=0.4)
    finally:
        await bus.stop_server()
