from datetime import datetime, timedelta, timezone

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.time_semantics import vector_clock_compare
from arqonbus.protocol.validator import EnvelopeValidator
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_causal_ordering_with_partitioned_operators():
    backend = MemoryStorageBackend(max_size=100)
    storage = MessageStorage(backend)
    base = datetime.now(timezone.utc)

    events = [
        Envelope(
            id="arq_1700000000000000000_1_aa11aa",
            type="message",
            timestamp=base + timedelta(seconds=1),
            room="ops",
            channel="partition-a",
            payload={"operator": "a", "step": 1},
            metadata={"sequence": 1, "vector_clock": {"op-a": 1, "op-b": 0}},
        ),
        Envelope(
            id="arq_1700000000000000000_2_bb22bb",
            type="message",
            timestamp=base + timedelta(seconds=2),
            room="ops",
            channel="partition-b",
            payload={"operator": "b", "step": 1},
            metadata={"sequence": 2, "vector_clock": {"op-a": 0, "op-b": 1}},
        ),
        Envelope(
            id="arq_1700000000000000000_3_cc33cc",
            type="message",
            timestamp=base + timedelta(seconds=3),
            room="ops",
            channel="partition-a",
            payload={"operator": "a", "step": 2},
            metadata={"sequence": 3, "vector_clock": {"op-a": 2, "op-b": 1}},
        ),
    ]

    for envelope in events:
        assert EnvelopeValidator.validate_envelope(envelope) == []
        await storage.store_message(envelope)

    replay = await storage.get_history_replay(
        room="ops",
        from_ts=base,
        to_ts=base + timedelta(seconds=10),
        limit=50,
        strict_sequence=True,
    )

    assert [entry.envelope.metadata["sequence"] for entry in replay] == [1, 2, 3]
    assert vector_clock_compare(
        replay[0].envelope.metadata["vector_clock"],
        replay[1].envelope.metadata["vector_clock"],
    ) == "concurrent"
