from datetime import datetime, timedelta, timezone

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_history_replay_enforces_time_window_and_sequence():
    backend = MemoryStorageBackend(max_size=100)
    storage = MessageStorage(backend)
    base = datetime.now(timezone.utc)

    first = await storage.store_message(
        Envelope(
            id="arq_1700000000000000000_4_dd44dd",
            type="message",
            timestamp=base + timedelta(seconds=1),
            room="ops",
            channel="events",
            payload={"idx": 0},
            metadata={"sequence": 1},
        )
    )
    await storage.store_message(
        Envelope(
            id="arq_1700000000000000000_5_ee55ee",
            type="message",
            timestamp=base + timedelta(seconds=3),
            room="ops",
            channel="events",
            payload={"idx": 1},
            metadata={"sequence": 2},
        )
    )
    third = await storage.store_message(
        Envelope(
            id="arq_1700000000000000000_6_ff66ff",
            type="message",
            timestamp=base + timedelta(seconds=5),
            room="ops",
            channel="events",
            payload={"idx": 2},
            metadata={"sequence": 3},
        )
    )

    replay = await storage.get_history_replay(
        room="ops",
        channel="events",
        from_ts=first.timestamp + timedelta(microseconds=1),
        to_ts=third.timestamp + timedelta(seconds=1),
        limit=50,
        strict_sequence=True,
    )

    assert [entry.envelope.payload["idx"] for entry in replay] == [1, 2]
