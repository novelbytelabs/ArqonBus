from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.transport.websocket_bus import WebSocketBus


def _command(command: str, args: dict) -> Envelope:
    return Envelope(
        id=generate_message_id(),
        type="command",
        command=command,
        args=args,
        payload={},
    )


def _event(
    *,
    event_id: str = "evt-1",
    event_type: str = "episode.created",
    source_ts: str = "2026-02-20T00:00:00+00:00",
    tenant_id: str = "tenant-a",
    agent_id: str = "agent-1",
    episode_id: str = "episode-1",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "episode_id": episode_id,
        "source_ts": source_ts,
        "schema_version": 1,
        "payload": {
            "content_ref": f"sqlite://continuum/episodes/{episode_id}",
            "summary": "summary",
            "tags": ["tag-a"],
            "embedding_ref": None,
            "metadata": {"m": 1},
        },
    }


def _make_bus(role: str = "admin") -> WebSocketBus:
    cfg = ArqonBusConfig()
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": role}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    bus = WebSocketBus(client_registry=registry, config=cfg)
    bus.send_to_client = AsyncMock(return_value=True)
    return bus


def _response_data(bus: WebSocketBus) -> dict:
    response = bus.send_to_client.call_args.args[1]
    assert response.status in {"success", "error"}
    return response.payload.get("data", {})


@pytest.mark.asyncio
async def test_projector_status_requires_admin():
    bus = _make_bus(role="user")
    await bus._handle_command(_command("op.continuum.projector.status", {}), "client-1")
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "error"
    assert response.error_code == "AUTHORIZATION_ERROR"


@pytest.mark.asyncio
async def test_project_event_and_get_projection():
    bus = _make_bus(role="admin")
    event = _event(event_id="evt-101", episode_id="ep-101")
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": event}),
        "client-1",
    )
    data = _response_data(bus)
    assert data["status"] == "projected"

    await bus._handle_command(
        _command(
            "op.continuum.projector.get",
            {"tenant_id": "tenant-a", "agent_id": "agent-1", "episode_id": "ep-101"},
        ),
        "client-1",
    )
    data = _response_data(bus)
    assert data["found"] is True
    assert data["projection"]["last_event_id"] == "evt-101"


@pytest.mark.asyncio
async def test_project_event_duplicate_detected():
    bus = _make_bus(role="admin")
    event = _event(event_id="evt-dup", episode_id="ep-dup")
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": event}),
        "client-1",
    )
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": event}),
        "client-1",
    )
    data = _response_data(bus)
    assert data["status"] == "duplicate"


@pytest.mark.asyncio
async def test_stale_update_rejected():
    bus = _make_bus(role="admin")
    current = _event(event_id="evt-new", episode_id="ep-stale", source_ts="2026-02-20T00:00:05+00:00")
    stale = _event(event_id="evt-old", episode_id="ep-stale", source_ts="2026-02-20T00:00:01+00:00")
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": current}),
        "client-1",
    )
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": stale}),
        "client-1",
    )
    data = _response_data(bus)
    assert data["status"] == "stale_rejected"


@pytest.mark.asyncio
async def test_invalid_event_goes_to_dlq_and_can_be_replayed():
    bus = _make_bus(role="admin")
    invalid_event = _event(event_id="evt-bad")
    invalid_event["payload"].pop("content_ref")
    await bus._handle_command(
        _command("op.continuum.projector.project_event", {"event": invalid_event}),
        "client-1",
    )
    data = _response_data(bus)
    assert data["status"] == "dlq_queued"
    dlq_id = data["dlq_id"]

    await bus._handle_command(
        _command("op.continuum.projector.dlq.list", {"limit": 10}),
        "client-1",
    )
    dlq_data = _response_data(bus)
    assert dlq_data["count"] >= 1

    fixed_event = _event(event_id="evt-bad")
    async with bus._ops_lock:
        for idx, item in enumerate(bus._continuum_dlq):
            if item["dlq_id"] == dlq_id:
                bus._continuum_dlq[idx]["event"] = fixed_event
                break

    await bus._handle_command(
        _command("op.continuum.projector.dlq.replay", {"dlq_id": dlq_id}),
        "client-1",
    )
    replay_data = _response_data(bus)
    assert replay_data["replayed"] is True


@pytest.mark.asyncio
async def test_backfill_dry_run_and_apply():
    bus = _make_bus(role="admin")
    e1 = _event(event_id="evt-bf-1", episode_id="ep-bf-1", source_ts="2026-02-20T00:00:01+00:00")
    e2 = _event(event_id="evt-bf-2", episode_id="ep-bf-2", source_ts="2026-02-20T00:00:02+00:00")
    await bus._handle_command(_command("op.continuum.projector.project_event", {"event": e1}), "client-1")
    await bus._handle_command(_command("op.continuum.projector.project_event", {"event": e2}), "client-1")

    await bus._handle_command(
        _command(
            "op.continuum.projector.backfill",
            {
                "from_ts": "2026-02-20T00:00:00+00:00",
                "to_ts": "2026-02-20T00:00:03+00:00",
                "dry_run": True,
            },
        ),
        "client-1",
    )
    dry_run_data = _response_data(bus)
    assert dry_run_data["dry_run"] is True
    assert dry_run_data["selected_count"] >= 2

    await bus._handle_command(
        _command(
            "op.continuum.projector.backfill",
            {
                "from_ts": "2026-02-20T00:00:00+00:00",
                "to_ts": "2026-02-20T00:00:03+00:00",
                "dry_run": False,
            },
        ),
        "client-1",
    )
    apply_data = _response_data(bus)
    assert apply_data["dry_run"] is False
    assert apply_data["duplicates"] >= 2
