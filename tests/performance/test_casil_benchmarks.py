import time

import pytest

from arqonbus.casil.engine import CASILEngine
from arqonbus.casil.outcome import CASILDecision
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope


def _baseline_round_trip(iterations: int):
    start = time.perf_counter()
    for _ in range(iterations):
        pass
    return time.perf_counter() - start


def _casil_round_trip(iterations: int, engine: CASILEngine, envelope: Envelope):
    start = time.perf_counter()
    for _ in range(iterations):
        engine.inspect(envelope, {"room": envelope.room, "channel": envelope.channel})
    return time.perf_counter() - start


@pytest.mark.performance
def test_casil_overhead_monitor_mode():
    iterations = 500
    envelope = Envelope(type="message", room="bench", channel="test", payload={"data": "x" * 10})
    cfg = CASILConfig(enabled=True)
    cfg.mode = "monitor"
    engine = CASILEngine(cfg)

    baseline = _baseline_round_trip(iterations)
    casil_time = _casil_round_trip(iterations, engine, envelope)
    per_message_overhead_ms = ((casil_time - baseline) / iterations) * 1000

    # Target <5ms overhead per message; keep assertion lenient for CI variability
    assert per_message_overhead_ms < 5.0


@pytest.mark.performance
def test_casil_disabled_matches_baseline():
    iterations = 500
    envelope = Envelope(type="message", room="bench", channel="test", payload={"data": "x" * 10})
    cfg = CASILConfig(enabled=False)
    engine = CASILEngine(cfg)

    baseline = _baseline_round_trip(iterations)
    casil_time = _casil_round_trip(iterations, engine, envelope)
    if baseline == 0:
        return
    delta = abs(casil_time - baseline) / baseline
    assert delta < 0.1  # target ±1%, allow slack for timing noise
