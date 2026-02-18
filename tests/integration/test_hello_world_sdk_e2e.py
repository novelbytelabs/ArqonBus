import asyncio
import itertools
import json
from datetime import datetime, timezone

import pytest
import websockets

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.ids import generate_message_id
from arqonbus.sdk import ArqonBusClient
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(47350)


def _next_port() -> int:
    return next(_port_sequence)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_hello_world_bot_path_with_python_sdk():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.storage.enable_persistence = False

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        async with websockets.connect(uri) as observer_ws:
            observer_welcome = json.loads(await asyncio.wait_for(observer_ws.recv(), timeout=2.0))
            observer_id = observer_welcome["payload"]["client_id"]

            async with ArqonBusClient(uri) as sdk_client:
                sdk_welcome = await sdk_client.recv_json(timeout=2.0)
                sdk_client_id = sdk_welcome["payload"]["client_id"]

                await bus.client_registry.join_room_channel(observer_id, "science", "general")
                await bus.client_registry.join_room_channel(sdk_client_id, "science", "general")

                await sdk_client.send_json(
                    {
                        "id": generate_message_id(),
                        "type": "message",
                        "timestamp": _now_iso(),
                        "version": "1.0",
                        "room": "science",
                        "channel": "general",
                        "payload": {"content": "Hello World from SDK"},
                    }
                )

                received = json.loads(await asyncio.wait_for(observer_ws.recv(), timeout=2.0))
                assert received["type"] == "message"
                assert received["payload"]["content"] == "Hello World from SDK"
    finally:
        await bus.stop_server()
