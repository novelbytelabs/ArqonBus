"""Postgres storage backend for ArqonBus."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .interface import HistoryEntry, StorageBackend, StorageResult
from .memory import MemoryStorageBackend
from ..protocol.envelope import Envelope

logger = logging.getLogger(__name__)

try:
    import asyncpg  # type: ignore

    POSTGRES_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via create strict/degraded tests
    asyncpg = None  # type: ignore[assignment]
    POSTGRES_AVAILABLE = False


class PostgresStorageBackend(StorageBackend):
    """Postgres-backed message history storage.

    In degraded mode, this backend falls back to an in-memory implementation if
    Postgres is unavailable. In strict mode it fails closed.
    """

    def __init__(
        self,
        *,
        postgres_url: str,
        max_size: int = 10000,
        storage_mode: str = "degraded",
        pool: Any = None,
        fallback_storage: Optional[MemoryStorageBackend] = None,
    ) -> None:
        self.postgres_url = postgres_url
        self.max_size = max_size
        self.storage_mode = storage_mode
        self.pool = pool
        self.fallback_storage = fallback_storage or MemoryStorageBackend(max_size=max_size)
        self._stats: Dict[str, Any] = {
            "backend_type": "postgres",
            "postgres_available": pool is not None,
            "postgres_operations": 0,
            "fallback_operations": 0,
            "last_postgres_error": None,
            "degraded_mode_active": pool is None,
        }

    @classmethod
    async def create(cls, config: Dict[str, Any]) -> "PostgresStorageBackend":
        postgres_url = config.get("postgres_url", "postgresql://localhost:5432/arqonbus")
        storage_mode = str(config.get("storage_mode", "degraded")).strip().lower()
        max_size = int(config.get("max_size", 10000))

        if storage_mode not in ("degraded", "strict"):
            raise ValueError(f"Unsupported storage mode for Postgres backend: {storage_mode}")

        if not POSTGRES_AVAILABLE:
            if storage_mode == "strict":
                raise RuntimeError("Postgres dependency is unavailable in strict storage mode")
            logger.warning("asyncpg dependency unavailable, falling back to memory storage")
            return cls(
                postgres_url=postgres_url,
                max_size=max_size,
                storage_mode=storage_mode,
                pool=None,
            )

        pool = None
        try:
            pool = await asyncpg.create_pool(postgres_url, min_size=1, max_size=10)
            backend = cls(
                postgres_url=postgres_url,
                max_size=max_size,
                storage_mode=storage_mode,
                pool=pool,
            )
            await backend._ensure_schema()
            logger.info("Connected to Postgres storage at %s", postgres_url)
            return backend
        except Exception as exc:
            logger.error("Postgres connection failed: %s", exc)
            if pool:
                await pool.close()
            if storage_mode == "strict":
                raise RuntimeError(f"Postgres connection failed in strict storage mode: {exc}") from exc
            return cls(
                postgres_url=postgres_url,
                max_size=max_size,
                storage_mode=storage_mode,
                pool=None,
            )

    async def _ensure_schema(self) -> None:
        if not self.pool:
            return
        query = """
        CREATE TABLE IF NOT EXISTS arqonbus_message_history (
            id BIGSERIAL PRIMARY KEY,
            message_id TEXT UNIQUE NOT NULL,
            room TEXT NOT NULL,
            channel TEXT NOT NULL,
            sender TEXT,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            envelope JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_arqonbus_room_channel_stored_at
          ON arqonbus_message_history (room, channel, stored_at DESC);
        CREATE INDEX IF NOT EXISTS idx_arqonbus_stored_at
          ON arqonbus_message_history (stored_at DESC);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def _handle_postgres_failure(self, error: Exception) -> None:
        self._stats["last_postgres_error"] = str(error)
        if self.storage_mode == "strict":
            raise RuntimeError(
                f"Postgres operation failed in strict storage mode: {error}"
            ) from error
        self._stats["degraded_mode_active"] = True
        logger.warning("Postgres operation failed; degraded fallback active: %s", error)

    async def append(self, envelope: Envelope, **kwargs) -> StorageResult:
        if not self.pool:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope, **kwargs)

        try:
            self._stats["postgres_operations"] += 1
            room = envelope.room or "default"
            channel = envelope.channel or "default"
            envelope_json = json.dumps(envelope.to_dict())
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO arqonbus_message_history
                        (message_id, room, channel, sender, envelope)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    envelope.id,
                    room,
                    channel,
                    envelope.sender,
                    envelope_json,
                )
            return StorageResult(
                success=True,
                message_id=envelope.id,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:
            await self._handle_postgres_failure(exc)
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.append(envelope, **kwargs)

    async def get_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[HistoryEntry]:
        if not self.pool:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(
                room=room,
                channel=channel,
                limit=limit,
                since=since,
                until=until,
            )

        try:
            self._stats["postgres_operations"] += 1
            conditions = []
            params: List[Any] = []

            if room is not None:
                params.append(room)
                conditions.append(f"room = ${len(params)}")
            if channel is not None:
                params.append(channel)
                conditions.append(f"channel = ${len(params)}")
            if since is not None:
                params.append(since)
                conditions.append(f"stored_at >= ${len(params)}")
            if until is not None:
                params.append(until)
                conditions.append(f"stored_at <= ${len(params)}")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(max(1, int(limit)))

            query = f"""
                SELECT envelope, stored_at
                FROM arqonbus_message_history
                {where_clause}
                ORDER BY stored_at DESC
                LIMIT ${len(params)}
            """

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

            entries: List[HistoryEntry] = []
            for row in rows:
                envelope_dict = dict(row["envelope"])
                entries.append(
                    HistoryEntry(
                        envelope=Envelope.from_dict(envelope_dict),
                        stored_at=row["stored_at"],
                        storage_metadata={"backend": "postgres"},
                    )
                )
            return entries
        except Exception as exc:
            await self._handle_postgres_failure(exc)
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.get_history(
                room=room,
                channel=channel,
                limit=limit,
                since=since,
                until=until,
            )

    async def delete_message(self, message_id: str) -> StorageResult:
        if not self.pool:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.delete_message(message_id)

        try:
            self._stats["postgres_operations"] += 1
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM arqonbus_message_history WHERE message_id = $1",
                    message_id,
                )
            deleted = result.endswith("1")
            if deleted:
                return StorageResult(
                    success=True,
                    message_id=message_id,
                    timestamp=datetime.now(timezone.utc),
                )
            return StorageResult(
                success=False,
                message_id=message_id,
                error_message="Message not found",
            )
        except Exception as exc:
            await self._handle_postgres_failure(exc)
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.delete_message(message_id)

    async def clear_history(
        self,
        room: Optional[str] = None,
        channel: Optional[str] = None,
        before: Optional[datetime] = None,
    ) -> StorageResult:
        if not self.pool:
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.clear_history(room=room, channel=channel, before=before)

        try:
            self._stats["postgres_operations"] += 1
            conditions = []
            params: List[Any] = []
            if room is not None:
                params.append(room)
                conditions.append(f"room = ${len(params)}")
            if channel is not None:
                params.append(channel)
                conditions.append(f"channel = ${len(params)}")
            if before is not None:
                params.append(before)
                conditions.append(f"stored_at < ${len(params)}")
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM arqonbus_message_history {where_clause}",
                    *params,
                )
            return StorageResult(
                success=True,
                timestamp=datetime.now(timezone.utc),
                metadata={"deleted": result},
            )
        except Exception as exc:
            await self._handle_postgres_failure(exc)
            self._stats["fallback_operations"] += 1
            return await self.fallback_storage.clear_history(room=room, channel=channel, before=before)

    async def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        stats["max_size"] = self.max_size
        if not self.pool:
            stats["fallback_stats"] = await self.fallback_storage.get_stats()
            return stats

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COUNT(*) AS count, MAX(stored_at) AS last_stored_at FROM arqonbus_message_history"
                )
            stats["total_messages"] = int(row["count"]) if row else 0
            stats["last_stored_at"] = row["last_stored_at"].isoformat() if row and row["last_stored_at"] else None
            return stats
        except Exception as exc:
            await self._handle_postgres_failure(exc)
            stats["fallback_stats"] = await self.fallback_storage.get_stats()
            return stats

    async def health_check(self) -> bool:
        if not self.pool:
            return await self.fallback_storage.health_check()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
        await self.fallback_storage.close()
