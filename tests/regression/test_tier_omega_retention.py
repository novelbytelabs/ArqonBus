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


def _make_bus(*, role: str = "admin", max_events: int = 2) -> WebSocketBus:
    config = ArqonBusConfig()
    config.tier_omega.enabled = True
    config.tier_omega.max_events = max_events
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": role}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)
    return bus


@pytest.mark.asyncio
async def test_omega_event_window_retains_latest_entries():
    bus = _make_bus(max_events=2)

    await bus._handle_command(
        _command("op.omega.register_substrate", {"name": "alpha", "kind": "relational"}),
        "client-1",
    )
    register_response = bus.send_to_client.call_args.args[1]
    substrate_id = register_response.payload["data"]["substrate_id"]

    for idx in range(3):
        await bus._handle_command(
            _command(
                "op.omega.emit_event",
                {
                    "substrate_id": substrate_id,
                    "signal": f"pulse-{idx}",
                    "payload": {"idx": idx},
                },
            ),
            "client-1",
        )

    await bus._handle_command(_command("op.omega.list_events", {"limit": 10}), "client-1")
    list_response = bus.send_to_client.call_args.args[1]

    assert list_response.status == "success"
    events = list_response.payload["data"]["events"]
    assert len(events) == 2
    assert events[0]["signal"] == "pulse-1"
    assert events[1]["signal"] == "pulse-2"
