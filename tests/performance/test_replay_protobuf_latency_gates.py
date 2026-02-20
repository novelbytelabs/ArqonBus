import os
import statistics
import time
from datetime import datetime, timedelta, timezone

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend


def _percentile(sorted_values, p):
    if not sorted_values:
        return 0.0
    idx = max(0, min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * p))))
    return sorted_values[idx]


@pytest.mark.performance
def test_protobuf_encode_decode_latency_gate():
    max_p95_ms = float(os.getenv("ARQONBUS_PERF_PROTOBUF_P95_MS", "3.0"))
    max_avg_ms = float(os.getenv("ARQONBUS_PERF_PROTOBUF_AVG_MS", "1.5"))

    envelope = Envelope(
        id="arq_1700000000000000000_7_c0ffee",
        timestamp=datetime.now(timezone.utc),
        type="command",
        command="op.history.replay",
        args={"room": "ops", "channel": "events", "limit": 100},
        metadata={"sequence": 11, "vector_clock": {"node-a": 11}},
        payload={"probe": True},
    )

    samples = []
    for _ in range(2000):
        started = time.perf_counter()
        decoded = Envelope.from_proto_bytes(envelope.to_proto_bytes())
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        samples.append(elapsed_ms)
        assert decoded.command == "op.history.replay"

    samples.sort()
    p95 = _percentile(samples, 0.95)
    avg = statistics.mean(samples)
    assert p95 <= max_p95_ms, f"protobuf p95 latency {p95:.3f}ms exceeds {max_p95_ms:.3f}ms"
    assert avg <= max_avg_ms, f"protobuf avg latency {avg:.3f}ms exceeds {max_avg_ms:.3f}ms"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_history_replay_latency_gate():
    max_p95_ms = float(os.getenv("ARQONBUS_PERF_REPLAY_P95_MS", "30.0"))
    max_avg_ms = float(os.getenv("ARQONBUS_PERF_REPLAY_AVG_MS", "20.0"))

    storage = MessageStorage(MemoryStorageBackend(max_size=10000))
    now = datetime.now(timezone.utc)
    for idx in range(4000):
        await storage.store_message(
            Envelope(
                id=f"arq_1700000000000000000_{idx + 1}_{idx % 0xFFFFFF:06x}",
                type="message",
                timestamp=now + timedelta(milliseconds=idx),
                room="ops",
                channel="events",
                payload={"idx": idx},
                metadata={"sequence": idx + 1},
            )
        )

    samples = []
    for _ in range(30):
        started = time.perf_counter()
        replay = await storage.get_history_replay(
            room="ops",
            channel="events",
            from_ts=now - timedelta(seconds=1),
            to_ts=datetime.now(timezone.utc) + timedelta(seconds=1),
            limit=5000,
            strict_sequence=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        samples.append(elapsed_ms)
        assert len(replay) >= 3900

    samples.sort()
    p95 = _percentile(samples, 0.95)
    avg = statistics.mean(samples)
    assert p95 <= max_p95_ms, f"history replay p95 latency {p95:.3f}ms exceeds {max_p95_ms:.3f}ms"
    assert avg <= max_avg_ms, f"history replay avg latency {avg:.3f}ms exceeds {max_avg_ms:.3f}ms"
