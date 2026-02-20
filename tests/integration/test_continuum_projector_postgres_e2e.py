import asyncio
import json
import os
import time
from datetime import datetime, timezone
from itertools import count

import pytest
import websockets

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.ids import generate_message_id
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.security.jwt_auth import issue_hs256_token
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.postgres import PostgresStorageBackend
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = count(47750)


def _next_port() -> int:
    return next(_port_sequence)


def _postgres_test_url() -> str:
    return os.getenv(
        "ARQONBUS_TEST_POSTGRES_URL",
        "postgresql://arqonbus:arqonbus@127.0.0.1:5432/arqonbus",
    )


def _event(tenant_id: str, agent_id: str, episode_id: str, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "event_type": "episode.created",
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "episode_id": episode_id,
        "source_ts": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "payload": {
            "content_ref": f"sqlite://continuum/episodes/{episode_id}",
            "summary": "e2e projector event",
            "tags": ["e2e", "continuum"],
            "embedding_ref": None,
            "metadata": {"source": "test_continuum_projector_postgres_e2e"},
        },
    }


async def _recv_command_response(ws, request_id: str) -> dict:
    for _ in range(8):
        frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
        if frame.get("type") == "response" and frame.get("request_id") == request_id:
            return frame
    raise AssertionError(f"response for {request_id} not received")


async def _build_backend_or_skip() -> PostgresStorageBackend:
    try:
        return await PostgresStorageBackend.create(
            {"postgres_url": _postgres_test_url(), "storage_mode": "strict", "max_size": 1000}
        )
    except Exception as exc:
        pytest.skip(f"Postgres integration unavailable at {_postgres_test_url()}: {exc}")


@pytest.mark.asyncio
async def test_continuum_projector_command_lane_persists_to_postgres():
    backend = await _build_backend_or_skip()
    tenant = f"tenant-e2e-{int(time.time())}"
    agent = "agent-e2e"
    episode = "episode-e2e-1"
    event_id = f"evt-e2e-{int(time.time())}"

    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "continuum-e2e-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.storage.enable_persistence = True

    bus = WebSocketBus(
        client_registry=ClientRegistry(),
        storage=MessageStorage(backend),
        config=cfg,
    )

    try:
        async with backend.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection_events WHERE tenant_id = $1",
                tenant,
            )
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection WHERE tenant_id = $1",
                tenant,
            )
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection_dlq WHERE event->>'tenant_id' = $1",
                tenant,
            )

        await bus.start_server()
        uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"
        admin_token = issue_hs256_token(
            {"sub": "admin", "role": "admin", "tenant_id": tenant, "exp": int(time.time()) + 120},
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "version": "1.0",
                        "command": "op.continuum.projector.project_event",
                        "args": {"event": _event(tenant, agent, episode, event_id)},
                    }
                )
            )
            response = await _recv_command_response(ws, cmd_id)
            assert response["status"] == "success"
            assert response["payload"]["data"]["status"] == "projected"

        projection = await backend.continuum_projector_get(tenant, agent, episode)
        assert projection is not None
        assert projection["last_event_id"] == event_id
        assert projection["tenant_id"] == tenant
    finally:
        await bus.stop_server()
        await backend.close()
