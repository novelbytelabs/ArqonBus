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
async def test_op_store_default_namespace_is_tenant_scoped():
    config = ArqonBusConfig()
    registry = MagicMock()
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    registry.get_client = AsyncMock(
        side_effect=[
            SimpleNamespace(metadata={"tenant_id": "tenant-a"}),
            SimpleNamespace(metadata={"tenant_id": "tenant-b"}),
            SimpleNamespace(metadata={"tenant_id": "tenant-a"}),
        ]
    )

    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)

    await bus._handle_command(
        _command("op.store.set", {"key": "shared", "value": "alpha"}),
        "client-a",
    )
    await bus._handle_command(_command("op.store.get", {"key": "shared"}), "client-b")
    tenant_b_response = bus.send_to_client.call_args.args[1]
    assert tenant_b_response.payload["data"]["found"] is False

    await bus._handle_command(_command("op.store.get", {"key": "shared"}), "client-a")
    tenant_a_response = bus.send_to_client.call_args.args[1]
    assert tenant_a_response.payload["data"]["found"] is True
    assert tenant_a_response.payload["data"]["value"] == "alpha"
