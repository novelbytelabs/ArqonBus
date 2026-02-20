import asyncio
from unittest.mock import MagicMock

import pytest

from arqonbus.config.config import ArqonBusConfig
from arqonbus.protocol.operator import State
from arqonbus.protocol.synthesis_operator import SynthesisOperator
from arqonbus.transport.websocket_bus import WebSocketBus


@pytest.mark.asyncio
async def test_synthesis_operator_safety_variant_returns_guardrail_action():
    operator = SynthesisOperator("op-phase3", ["synthesis"])
    action = await operator.process(State(context={"variant": "safety"}))
    assert action.description.startswith("Safety:")
    assert action.payload["assert"] == "error_rate < 0.02"


@pytest.mark.asyncio
async def test_synthesis_operator_speed_variant_returns_tune_action():
    operator = SynthesisOperator("op-phase3", ["synthesis"])
    action = await operator.process(State(context={"variant": "speed", "latency_p99_ms": 120}))
    assert action.description.startswith("Performance:")
    assert action.payload["param"] == "dispatch_batch_size"


@pytest.mark.asyncio
async def test_cancel_all_cron_jobs_logs_non_cancel_errors(caplog):
    config = ArqonBusConfig()
    config.casil.enabled = False
    bus = WebSocketBus(client_registry=MagicMock(), config=config)

    loop = asyncio.get_running_loop()
    task = loop.create_future()
    task.set_exception(RuntimeError("cleanup failure"))
    bus._cron_tasks = {"job-1": task}
    bus._cron_jobs = {"job-1": MagicMock()}

    with caplog.at_level("WARNING"):
        await bus._cancel_all_cron_jobs()

    assert "Cron task cleanup failed during shutdown" in caplog.text
