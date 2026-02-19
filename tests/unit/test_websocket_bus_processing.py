from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.interface import StorageResult
from arqonbus.transport.websocket_bus import WebSocketBus


def _make_bus(storage=None):
    config = ArqonBusConfig()
    config.storage.enable_persistence = True
    config.casil.enabled = False

    client_registry = MagicMock()
    client_registry.broadcast_to_room_channel = AsyncMock(return_value=1)
    return WebSocketBus(client_registry=client_registry, storage=storage, config=config), client_registry


@pytest.mark.asyncio
async def test_handle_message_persists_and_broadcasts():
    storage = MagicMock()
    storage.store_message = AsyncMock(return_value=StorageResult(success=True, message_id="m1"))
    bus, client_registry = _make_bus(storage=storage)

    envelope = Envelope(
        id="msg-1",
        type="message",
        room="science",
        channel="general",
        payload={"content": "hello"},
    )
    await bus._handle_message(envelope, client_id="sender-1")

    storage.store_message.assert_awaited_once()
    client_registry.broadcast_to_room_channel.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_without_storage_still_broadcasts():
    bus, client_registry = _make_bus(storage=None)

    envelope = Envelope(
        id="msg-2",
        type="message",
        room="science",
        channel="general",
        payload={"content": "hello"},
    )
    await bus._handle_message(envelope, client_id="sender-2")

    client_registry.broadcast_to_room_channel.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_telemetry_persists_and_broadcasts_when_routing_hints_present():
    storage = MagicMock()
    storage.store_message = AsyncMock(return_value=StorageResult(success=True, message_id="t1"))
    bus, client_registry = _make_bus(storage=storage)

    envelope = Envelope(
        id="tel-1",
        type="telemetry",
        room="integriguard",
        channel="telemetry-stream",
        payload={"eventType": "metric", "payload": {"x": 1}},
    )
    await bus._handle_telemetry(envelope, client_id="sender-t")

    storage.store_message.assert_awaited_once()
    client_registry.broadcast_to_room_channel.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_telemetry_persists_with_defaults_without_room_channel():
    storage = MagicMock()
    storage.store_message = AsyncMock(return_value=StorageResult(success=True, message_id="t2"))
    bus, client_registry = _make_bus(storage=storage)

    envelope = Envelope(
        id="tel-2",
        type="telemetry",
        payload={"eventType": "metric", "payload": {"x": 2}},
    )
    await bus._handle_telemetry(envelope, client_id="sender-t")

    storage.store_message.assert_awaited_once()
    client_registry.broadcast_to_room_channel.assert_not_awaited()
