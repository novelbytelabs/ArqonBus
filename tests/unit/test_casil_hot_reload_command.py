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


@pytest.mark.asyncio
async def test_op_casil_reload_requires_admin_role():
    config = ArqonBusConfig()
    config.casil.enabled = True
    config.casil.mode = "monitor"

    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "user"}))
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)

    await bus._handle_command(_command("op.casil.reload", {"mode": "enforce"}), "client-user")
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "error"
    assert response.error_code == "AUTHORIZATION_ERROR"
    assert bus.config.casil.mode == "monitor"


@pytest.mark.asyncio
async def test_op_casil_reload_updates_policy_for_admin():
    config = ArqonBusConfig()
    config.casil.enabled = True
    config.casil.mode = "monitor"

    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "admin"}))
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)

    await bus._handle_command(
        _command(
            "op.casil.reload",
            {
                "mode": "enforce",
                "block_on_probable_secret": True,
                "redaction_patterns": ["token"],
            },
        ),
        "client-admin",
    )
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "success"
    assert bus.config.casil.mode == "enforce"
    assert bus.config.casil.policies.block_on_probable_secret is True
    assert bus.config.casil.policies.redaction.patterns == ["token"]
