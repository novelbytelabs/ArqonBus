from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from arqonbus.protocol.envelope import Envelope
from arqonbus.storage.postgres import PostgresStorageBackend


class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Pool:
    def __init__(self, conn):
        self._conn = conn
        self.close = AsyncMock()

    def acquire(self):
        return _Acquire(self._conn)


@pytest.mark.asyncio
async def test_postgres_create_degraded_when_dependency_missing(monkeypatch):
    from arqonbus.storage import postgres as pg_mod

    monkeypatch.setattr(pg_mod, "POSTGRES_AVAILABLE", False)
    backend = await PostgresStorageBackend.create(
        {"postgres_url": "postgresql://localhost:5432/arqonbus", "storage_mode": "degraded"}
    )
    assert backend.pool is None
    assert backend.storage_mode == "degraded"


@pytest.mark.asyncio
async def test_postgres_create_strict_fails_when_dependency_missing(monkeypatch):
    from arqonbus.storage import postgres as pg_mod

    monkeypatch.setattr(pg_mod, "POSTGRES_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="strict storage mode"):
        await PostgresStorageBackend.create(
            {"postgres_url": "postgresql://localhost:5432/arqonbus", "storage_mode": "strict"}
        )


@pytest.mark.asyncio
async def test_postgres_create_and_append_success(monkeypatch):
    from arqonbus.storage import postgres as pg_mod

    conn = SimpleNamespace(execute=AsyncMock(return_value="INSERT 0 1"))
    pool = _Pool(conn)
    create_pool = AsyncMock(return_value=pool)
    monkeypatch.setattr(pg_mod, "POSTGRES_AVAILABLE", True)
    monkeypatch.setattr(pg_mod, "asyncpg", SimpleNamespace(create_pool=create_pool))

    backend = await PostgresStorageBackend.create(
        {"postgres_url": "postgresql://localhost:5432/arqonbus", "storage_mode": "strict"}
    )

    envelope = Envelope(
        id="msg-1",
        type="message",
        timestamp=datetime.now(timezone.utc),
        room="room-a",
        channel="channel-a",
        payload={"ok": True},
    )
    result = await backend.append(envelope)

    assert result.success is True
    assert result.message_id == "msg-1"
    assert conn.execute.await_count >= 2  # schema + insert


@pytest.mark.asyncio
async def test_postgres_strict_runtime_failure_raises(monkeypatch):
    from arqonbus.storage import postgres as pg_mod

    conn = SimpleNamespace(execute=AsyncMock(side_effect=Exception("write failed")))
    pool = _Pool(conn)
    create_pool = AsyncMock(return_value=pool)
    monkeypatch.setattr(pg_mod, "POSTGRES_AVAILABLE", True)
    monkeypatch.setattr(pg_mod, "asyncpg", SimpleNamespace(create_pool=create_pool))

    with pytest.raises(RuntimeError, match="strict storage mode"):
        await PostgresStorageBackend.create(
            {"postgres_url": "postgresql://localhost:5432/arqonbus", "storage_mode": "strict"}
        )
