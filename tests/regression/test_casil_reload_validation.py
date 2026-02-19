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
async def test_invalid_casil_reload_does_not_change_active_policy():
    config = ArqonBusConfig()
    config.casil.enabled = True
    config.casil.mode = "monitor"

    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "admin"}))
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)

    await bus._handle_command(_command("op.casil.reload", {"mode": "invalid-mode"}), "client-admin")
    response = bus.send_to_client.call_args.args[1]
    assert response.status == "error"
    assert response.error_code == "VALIDATION_ERROR"
    assert bus.config.casil.mode == "monitor"
