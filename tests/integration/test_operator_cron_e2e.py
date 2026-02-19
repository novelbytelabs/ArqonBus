import asyncio
import itertools
import json
from datetime import datetime, timezone

import pytest
import websockets

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.ids import generate_message_id
from arqonbus.routing.client_registry import ClientRegistry
from arqonbus.transport.websocket_bus import WebSocketBus


pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.socket]

_port_sequence = itertools.count(47250)


def _next_port() -> int:
    return next(_port_sequence)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_op_cron_schedule_delivers_message_to_target_room_channel():
    cfg = ArqonBusConfig()
    cfg.server.host = "127.0.0.1"
    cfg.websocket.port = _next_port()
    cfg.storage.enable_persistence = False

    bus = WebSocketBus(ClientRegistry(), config=cfg)
    await bus.start_server()
    uri = f"ws://{cfg.server.host}:{cfg.websocket.port}"

    try:
        async with websockets.connect(uri) as ws1:
            async with websockets.connect(uri) as ws2:
                welcome1 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                welcome2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                c1 = welcome1["payload"]["client_id"]
                c2 = welcome2["payload"]["client_id"]

                await bus.client_registry.join_room_channel(c1, "science", "general")
                await bus.client_registry.join_room_channel(c2, "science", "general")

                cmd_id = generate_message_id()
                schedule_cmd = {
                    "id": cmd_id,
                    "type": "command",
                    "timestamp": _now_iso(),
                    "version": "1.0",
                    "command": "op.cron.schedule",
                    "args": {
                        "room": "science",
                        "channel": "general",
                        "payload": {"content": "cron-hello"},
                        "delay_seconds": 0.05,
                    },
                }
                await ws1.send(json.dumps(schedule_cmd))

                # ws1 receives both command response and legacy command ack.
                saw_schedule_success = False
                for _ in range(3):
                    response = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
                    if (
                        response.get("type") == "response"
                        and response.get("request_id") == cmd_id
                        and response.get("status") == "success"
                    ):
                        saw_schedule_success = True
                        break
                assert saw_schedule_success is True

                scheduled_message = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
                assert scheduled_message["type"] == "message"
                assert scheduled_message["payload"]["content"] == "cron-hello"
                assert scheduled_message["metadata"]["cron_job_id"].startswith("cron_")
    finally:
        await bus.stop_server()
