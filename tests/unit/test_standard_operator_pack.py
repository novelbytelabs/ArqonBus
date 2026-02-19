from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.transport.websocket_bus import WebSocketBus


def _make_bus():
    config = ArqonBusConfig()
    registry = MagicMock()
    registry.get_client = AsyncMock(return_value=SimpleNamespace(metadata={"role": "user"}))
    registry.broadcast_to_room_channel = AsyncMock(return_value=0)
    bus = WebSocketBus(client_registry=registry, config=config)
    bus.send_to_client = AsyncMock(return_value=True)
    return bus


def _command(command: str, args: dict) -> Envelope:
    return Envelope(
        id=generate_message_id(),
        type="command",
        command=command,
        args=args,
        payload={},
    )


@pytest.mark.asyncio
async def test_op_store_set_get_list_delete_roundtrip():
    bus = _make_bus()

    await bus._handle_command(
        _command("op.store.set", {"namespace": "ns-a", "key": "alpha", "value": {"v": 1}}),
        "client-1",
    )
    set_response = bus.send_to_client.call_args.args[1]
    assert set_response.status == "success"
    assert set_response.payload["data"]["updated"] is False

    await bus._handle_command(
        _command("op.store.get", {"namespace": "ns-a", "key": "alpha"}),
        "client-1",
    )
    get_response = bus.send_to_client.call_args.args[1]
    assert get_response.status == "success"
    assert get_response.payload["data"]["found"] is True
    assert get_response.payload["data"]["value"] == {"v": 1}

    await bus._handle_command(_command("op.store.list", {"namespace": "ns-a"}), "client-1")
    list_response = bus.send_to_client.call_args.args[1]
    assert list_response.status == "success"
    assert list_response.payload["data"]["keys"] == ["alpha"]

    await bus._handle_command(
        _command("op.store.delete", {"namespace": "ns-a", "key": "alpha"}),
        "client-1",
    )
    delete_response = bus.send_to_client.call_args.args[1]
    assert delete_response.status == "success"
    assert delete_response.payload["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_op_webhook_register_list_unregister():
    bus = _make_bus()

    await bus._handle_command(
        _command(
            "op.webhook.register",
            {"url": "http://127.0.0.1:9999/hook", "room": "science", "channel": "general"},
        ),
        "client-1",
    )
    register_response = bus.send_to_client.call_args.args[1]
    assert register_response.status == "success"
    rule_id = register_response.payload["data"]["rule_id"]
    assert rule_id in bus._webhook_rules

    await bus._handle_command(_command("op.webhook.list", {}), "client-1")
    list_response = bus.send_to_client.call_args.args[1]
    assert list_response.status == "success"
    assert list_response.payload["data"]["count"] == 1

    await bus._handle_command(_command("op.webhook.unregister", {"rule_id": rule_id}), "client-1")
    unregister_response = bus.send_to_client.call_args.args[1]
    assert unregister_response.status == "success"
    assert rule_id not in bus._webhook_rules


@pytest.mark.asyncio
async def test_op_cron_schedule_and_cancel():
    bus = _make_bus()

    await bus._handle_command(
        _command(
            "op.cron.schedule",
            {
                "room": "science",
                "channel": "general",
                "payload": {"content": "scheduled"},
                "delay_seconds": 5,
            },
        ),
        "client-1",
    )
    schedule_response = bus.send_to_client.call_args.args[1]
    assert schedule_response.status == "success"
    job_id = schedule_response.payload["data"]["job_id"]
    assert job_id in bus._cron_jobs
    assert job_id in bus._cron_tasks

    await bus._handle_command(_command("op.cron.cancel", {"job_id": job_id}), "client-1")
    cancel_response = bus.send_to_client.call_args.args[1]
    assert cancel_response.status == "success"
    assert job_id not in bus._cron_jobs
    assert job_id not in bus._cron_tasks
