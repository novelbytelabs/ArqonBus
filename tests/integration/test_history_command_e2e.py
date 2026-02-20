import asyncio
import itertools
import time
from datetime import datetime, timedelta, timezone

import pytest
import websockets

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.security.jwt_auth import issue_hs256_token
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(47880)


def _next_port() -> int:
    return next(_port_sequence)


async def _recv_response(ws, request_id: str) -> Envelope:
    for _ in range(6):
        frame = await asyncio.wait_for(ws.recv(), timeout=2.0)
        if not isinstance(frame, (bytes, bytearray)):
            continue
        envelope = Envelope.from_proto_bytes(bytes(frame))
        if envelope.type == "response" and envelope.request_id == request_id:
            return envelope
    raise AssertionError(f"response for {request_id} not received")


@pytest.mark.asyncio
async def test_history_command_lane_over_protobuf_wire():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.security.enable_authentication = True
    cfg.security.jwt_secret = "history-e2e-secret"
    cfg.security.jwt_algorithm = "HS256"
    cfg.infra_protocol = "protobuf"
    cfg.allow_json_infra = False
    cfg.storage.enable_persistence = True

    storage = MessageStorage(MemoryStorageBackend(max_size=500))
    bus = WebSocketBus(ClientRegistry(), storage=storage, config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        now = int(time.time())
        token = issue_hs256_token(
            {"sub": "admin", "role": "admin", "tenant_id": "tenant-a", "exp": now + 120},
            cfg.security.jwt_secret or "",
        )
        async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {token}"}) as ws:
            welcome = await asyncio.wait_for(ws.recv(), timeout=2.0)
            assert isinstance(welcome, (bytes, bytearray))

            ts_base = datetime.now(timezone.utc)
            for idx in (1, 2, 3):
                event = Envelope(
                    id=generate_message_id(),
                    type="message",
                    timestamp=ts_base + timedelta(seconds=idx),
                    room="ops",
                    channel="events",
                    payload={"idx": idx},
                    metadata={"sequence": idx},
                )
                await ws.send(event.to_proto_bytes())
                await asyncio.wait_for(ws.recv(), timeout=2.0)  # message_response ack

            get_cmd = Envelope(
                id=generate_message_id(),
                type="command",
                timestamp=datetime.now(timezone.utc),
                command="op.history.get",
                args={"room": "ops", "channel": "events", "limit": 10},
            )
            await ws.send(get_cmd.to_proto_bytes())
            get_response = await _recv_response(ws, get_cmd.id)
            assert get_response.status == "success"
            get_data = get_response.payload["data"]
            assert get_data["count"] >= 3

            replay_cmd = Envelope(
                id=generate_message_id(),
                type="command",
                timestamp=datetime.now(timezone.utc),
                command="op.history.replay",
                args={
                    "room": "ops",
                    "channel": "events",
                    "from_ts": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    "to_ts": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
                    "strict_sequence": True,
                    "limit": 100,
                },
            )
            await ws.send(replay_cmd.to_proto_bytes())
            replay_response = await _recv_response(ws, replay_cmd.id)
            assert replay_response.status == "success"
            replay_data = replay_response.payload["data"]
            assert replay_data["count"] >= 3
            indexes = [int(entry["envelope"]["payload"]["idx"]) for entry in replay_data["entries"]]
            assert indexes[:3] == [1, 2, 3]
    finally:
        await bus.stop_server()
