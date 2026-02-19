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


pytestmark = [pytest.mark.integration, pytest.mark.socket]

_port_sequence = itertools.count(47450)


def _next_port() -> int:
    return next(_port_sequence)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_op_casil_reload_and_get_updates_live_policy():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "casil-reload-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = False
    cfg.casil.enabled = True
    cfg.casil.mode = "monitor"

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
            await asyncio.wait_for(ws.recv(), timeout=2.0)  # welcome

            reload_id = generate_message_id()
            reload_cmd = {
                "id": reload_id,
                "type": "command",
                "timestamp": _now_iso(),
                "version": "1.0",
                "command": "op.casil.reload",
                "args": {"mode": "enforce"},
            }
            await ws.send(json.dumps(reload_cmd))

            saw_reload_success = False
            for _ in range(3):
                response = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if (
                    response.get("type") == "response"
                    and response.get("request_id") == reload_id
                    and response.get("status") == "success"
                ):
                    saw_reload_success = True
                    assert response["payload"]["data"]["mode"] == "enforce"
                    break
            assert saw_reload_success is True

            get_id = generate_message_id()
            get_cmd = {
                "id": get_id,
                "type": "command",
                "timestamp": _now_iso(),
                "version": "1.0",
                "command": "op.casil.get",
                "args": {},
            }
            await ws.send(json.dumps(get_cmd))

            saw_get_success = False
            for _ in range(3):
                response = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if (
                    response.get("type") == "response"
                    and response.get("request_id") == get_id
                    and response.get("status") == "success"
                ):
                    saw_get_success = True
                    assert response["payload"]["data"]["mode"] == "enforce"
                    break
            assert saw_get_success is True
    finally:
        await bus.stop_server()
