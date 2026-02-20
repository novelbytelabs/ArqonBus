from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend
from arqonbus.transport.websocket_bus import WebSocketBus


def _command(command: str, args: dict) -> Envelope:
    return Envelope(
        id=generate_message_id(),
        type="command",
        command=command,
        args=args,
        payload={},
    )


def _make_bus(role: str = "admin") -> WebSocketBus:
    cfg = ArqonBusConfig()
    cfg.storage.enable_persistence = True
    storage = MessageStorage(MemoryStorageBackend(max_size=200))
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": role}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    bus = WebSocketBus(client_registry=registry, storage=storage, config=cfg)
    bus.send_to_client = AsyncMock(return_value=True)
    return bus


def _response(bus: WebSocketBus):
    return bus.send_to_client.call_args.args[1]


@pytest.mark.asyncio
async def test_history_get_requires_room_for_non_admin():
    bus = _make_bus(role="user")
    await bus._handle_command(_command("op.history.get", {"limit": 10}), "client-1")
    response = _response(bus)
    assert response.status == "error"
    assert response.error_code == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_history_get_returns_entries_for_room():
    bus = _make_bus(role="admin")
    now = datetime.now(timezone.utc)

    for idx in (1, 2):
        await bus.storage.store_message(
            Envelope(
                id=f"arq_1700000000000000000_{idx}_{idx}{idx}{idx}{idx}{idx}{idx}",
                type="message",
                timestamp=now + timedelta(seconds=idx),
                room="ops",
                channel="events",
                payload={"idx": idx},
                metadata={"sequence": idx},
            )
        )

    await bus._handle_command(_command("history.get", {"room": "ops", "channel": "events", "limit": 10}), "client-1")
    response = _response(bus)
    assert response.status == "success"
    data = response.payload["data"]
    assert data["count"] == 2
    assert data["entries"][0]["envelope"]["room"] == "ops"


@pytest.mark.asyncio
async def test_history_replay_returns_chronological_entries():
    bus = _make_bus(role="admin")
    now = datetime.now(timezone.utc)

    for idx in (1, 2, 3):
        await bus.storage.store_message(
            Envelope(
                id=f"arq_1700000000000000000_{idx}_a{idx}a{idx}a{idx}",
                type="message",
                timestamp=now + timedelta(seconds=idx),
                room="ops",
                channel="events",
                payload={"idx": idx},
                metadata={"sequence": idx},
            )
        )

    from_ts = now - timedelta(seconds=1)
    to_ts = datetime.now(timezone.utc) + timedelta(seconds=3)
    await bus._handle_command(
        _command(
            "op.history.replay",
            {
                "room": "ops",
                "channel": "events",
                "from_ts": from_ts.isoformat(),
                "to_ts": to_ts.isoformat(),
                "strict_sequence": True,
                "limit": 50,
            },
        ),
        "client-1",
    )
    response = _response(bus)
    assert response.status == "success"
    data = response.payload["data"]
    assert [entry["envelope"]["payload"]["idx"] for entry in data["entries"]] == [1, 2, 3]
