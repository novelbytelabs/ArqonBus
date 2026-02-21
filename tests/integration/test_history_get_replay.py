from datetime import datetime, timedelta, timezone

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.interface import MessageStorage
from arqonbus.storage.memory import MemoryStorageBackend


@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_replay_returns_chronological_window():
    backend = MemoryStorageBackend(max_size=100)
    storage = MessageStorage(backend)
    now = datetime.now(timezone.utc)

    for idx in (1, 2, 3):
        await storage.store_message(
            Envelope(
                id=f"arq_{idx:026d}",
                type="message",
                timestamp=now + timedelta(seconds=idx),
                room="ops",
                channel="events",
                payload={"idx": idx},
                metadata={"sequence": idx},
            )
        )

    replay = await storage.get_history_replay(
        room="ops",
        channel="events",
        from_ts=now,
        to_ts=now + timedelta(seconds=10),
        limit=50,
        strict_sequence=True,
    )
    assert [entry.envelope.payload["idx"] for entry in replay] == [1, 2, 3]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_replay_detects_sequence_regression_in_strict_mode():
    backend = MemoryStorageBackend(max_size=100)
    storage = MessageStorage(backend)
    now = datetime.now(timezone.utc)

    await storage.store_message(
        Envelope(
            id="arq_11111111111111111111111111",
            type="message",
            timestamp=now + timedelta(seconds=1),
            room="ops",
            channel="events",
            payload={"idx": 1},
            metadata={"sequence": 2},
        )
    )
    await storage.store_message(
        Envelope(
            id="arq_22222222222222222222222222",
            type="message",
            timestamp=now + timedelta(seconds=2),
            room="ops",
            channel="events",
            payload={"idx": 2},
            metadata={"sequence": 1},
        )
    )

    with pytest.raises(ValueError, match="Sequence regression"):
        await storage.get_history_replay(
            room="ops",
            channel="events",
            from_ts=now,
            to_ts=now + timedelta(seconds=10),
            strict_sequence=True,
        )
