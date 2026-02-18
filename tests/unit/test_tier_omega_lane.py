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


def _make_bus(*, role: str = "admin", omega_enabled: bool = False) -> WebSocketBus:
    config = ArqonBusConfig()
    config.tier_omega.enabled = omega_enabled
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": role}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)
    return bus


@pytest.mark.asyncio
async def test_omega_status_returns_default_disabled_snapshot():
    bus = _make_bus(omega_enabled=False)
    await bus._handle_command(_command("op.omega.status", {}), "client-1")
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "success"
    assert response.payload["data"]["enabled"] is False


@pytest.mark.asyncio
async def test_omega_commands_are_blocked_when_feature_disabled():
    bus = _make_bus(omega_enabled=False)
    await bus._handle_command(
        _command("op.omega.register_substrate", {"name": "test", "kind": "sandbox"}),
        "client-1",
    )
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "error"
    assert response.error_code == "FEATURE_DISABLED"


@pytest.mark.asyncio
async def test_omega_enabled_allows_register_and_emit():
    bus = _make_bus(omega_enabled=True)

    await bus._handle_command(
        _command("op.omega.register_substrate", {"name": "alpha", "kind": "relational"}),
        "client-1",
    )
    register_response = bus.send_to_client.call_args.args[1]
    assert register_response.status == "success"
    substrate_id = register_response.payload["data"]["substrate_id"]

    await bus._handle_command(
        _command(
            "op.omega.emit_event",
            {"substrate_id": substrate_id, "signal": "pulse", "payload": {"x": 1}},
        ),
        "client-1",
    )
    emit_response = bus.send_to_client.call_args.args[1]
    assert emit_response.status == "success"
    assert emit_response.payload["data"]["signal"] == "pulse"
    bus.client_registry.broadcast_to_room_channel.assert_awaited()


@pytest.mark.asyncio
async def test_omega_mutation_requires_admin_even_when_enabled():
    bus = _make_bus(role="user", omega_enabled=True)
    await bus._handle_command(
        _command("op.omega.register_substrate", {"name": "alpha", "kind": "relational"}),
        "client-1",
    )
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "error"
    assert response.error_code == "AUTHORIZATION_ERROR"
