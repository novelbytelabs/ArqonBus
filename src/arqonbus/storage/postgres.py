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

        CREATE TABLE IF NOT EXISTS arqonbus_continuum_projection (
            tenant_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            episode_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            content_ref TEXT NOT NULL,
            summary TEXT,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            embedding_ref TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_event_id TEXT NOT NULL,
            last_event_ts TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (tenant_id, agent_id, episode_id)
        );

        CREATE TABLE IF NOT EXISTS arqonbus_continuum_projection_events (
            tenant_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            episode_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source_ts TIMESTAMPTZ NOT NULL,
            event JSONB NOT NULL,
            projected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (tenant_id, agent_id, event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_arqonbus_cont_proj_events_source_ts
          ON arqonbus_continuum_projection_events (source_ts DESC);
        CREATE INDEX IF NOT EXISTS idx_arqonbus_cont_proj_events_episode
          ON arqonbus_continuum_projection_events (tenant_id, agent_id, episode_id, source_ts DESC);

        CREATE TABLE IF NOT EXISTS arqonbus_continuum_projection_dlq (
            dlq_id TEXT PRIMARY KEY,
            reason TEXT NOT NULL,
            event JSONB NOT NULL,
            queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_arqonbus_cont_proj_dlq_queued_at
          ON arqonbus_continuum_projection_dlq (queued_at DESC);
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

    # Continuum projector persistence hooks
    async def continuum_project_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        tenant_id = str(event["tenant_id"])
        agent_id = str(event["agent_id"])
        episode_id = str(event["episode_id"])
        event_id = str(event["event_id"])
        event_type = str(event["event_type"])
        source_ts = datetime.fromisoformat(str(event["source_ts"]).replace("Z", "+00:00"))
        payload = dict(event["payload"])

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                inserted = await conn.fetchrow(
                    """
                    INSERT INTO arqonbus_continuum_projection_events
                        (tenant_id, agent_id, event_id, episode_id, event_type, source_ts, event)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                    ON CONFLICT (tenant_id, agent_id, event_id) DO NOTHING
                    RETURNING event_id
                    """,
                    tenant_id,
                    agent_id,
                    event_id,
                    episode_id,
                    event_type,
                    source_ts,
                    json.dumps(event),
                )
                if inserted is None:
                    return {
                        "status": "duplicate",
                        "event_id": event_id,
                        "projection_key": (tenant_id, agent_id, episode_id),
                    }

                existing = await conn.fetchrow(
                    """
                    SELECT last_event_ts
                    FROM arqonbus_continuum_projection
                    WHERE tenant_id = $1 AND agent_id = $2 AND episode_id = $3
                    """,
                    tenant_id,
                    agent_id,
                    episode_id,
                )
                if existing and source_ts < existing["last_event_ts"]:
                    return {
                        "status": "stale_rejected",
                        "event_id": event_id,
                        "projection_key": (tenant_id, agent_id, episode_id),
                        "existing_last_event_ts": existing["last_event_ts"].isoformat(),
                    }

                await conn.execute(
                    """
                    INSERT INTO arqonbus_continuum_projection
                        (
                            tenant_id, agent_id, episode_id, event_type,
                            content_ref, summary, tags, embedding_ref, metadata,
                            last_event_id, last_event_ts, updated_at, deleted
                        )
                    VALUES
                        ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::jsonb, $10, $11, NOW(), $12)
                    ON CONFLICT (tenant_id, agent_id, episode_id)
                    DO UPDATE SET
                        event_type = EXCLUDED.event_type,
                        content_ref = EXCLUDED.content_ref,
                        summary = EXCLUDED.summary,
                        tags = EXCLUDED.tags,
                        embedding_ref = EXCLUDED.embedding_ref,
                        metadata = EXCLUDED.metadata,
                        last_event_id = EXCLUDED.last_event_id,
                        last_event_ts = EXCLUDED.last_event_ts,
                        updated_at = NOW(),
                        deleted = EXCLUDED.deleted
                    """,
                    tenant_id,
                    agent_id,
                    episode_id,
                    event_type,
                    str(payload.get("content_ref")),
                    payload.get("summary"),
                    json.dumps(payload.get("tags", [])),
                    payload.get("embedding_ref"),
                    json.dumps(payload.get("metadata", {})),
                    event_id,
                    source_ts,
                    event_type == "episode.deleted",
                )

        return {
            "status": "projected",
            "event_id": event_id,
            "projection_key": (tenant_id, agent_id, episode_id),
            "deleted": event_type == "episode.deleted",
        }

    async def continuum_projector_status(self) -> Dict[str, Any]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        async with self.pool.acquire() as conn:
            projection_count = await conn.fetchval(
                "SELECT COUNT(*) FROM arqonbus_continuum_projection"
            )
            seen_event_count = await conn.fetchval(
                "SELECT COUNT(*) FROM arqonbus_continuum_projection_events"
            )
            dlq_count = await conn.fetchval(
                "SELECT COUNT(*) FROM arqonbus_continuum_projection_dlq"
            )
        return {
            "projection_count": int(projection_count or 0),
            "seen_event_count": int(seen_event_count or 0),
            "dlq_count": int(dlq_count or 0),
        }

    async def continuum_projector_get(
        self, tenant_id: str, agent_id: str, episode_id: str
    ) -> Optional[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tenant_id, agent_id, episode_id, event_type, content_ref, summary,
                       tags, embedding_ref, metadata, last_event_id, last_event_ts,
                       updated_at, deleted
                FROM arqonbus_continuum_projection
                WHERE tenant_id = $1 AND agent_id = $2 AND episode_id = $3
                """,
                tenant_id,
                agent_id,
                episode_id,
            )
        if row is None:
            return None
        return {
            "tenant_id": row["tenant_id"],
            "agent_id": row["agent_id"],
            "episode_id": row["episode_id"],
            "event_type": row["event_type"],
            "content_ref": row["content_ref"],
            "summary": row["summary"],
            "tags": list(row["tags"] or []),
            "embedding_ref": row["embedding_ref"],
            "metadata": dict(row["metadata"] or {}),
            "last_event_id": row["last_event_id"],
            "last_event_ts": row["last_event_ts"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "deleted": bool(row["deleted"]),
        }

    async def continuum_projector_list(
        self,
        *,
        limit: int = 100,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        conditions = []
        params: List[Any] = []
        if tenant_id:
            params.append(tenant_id)
            conditions.append(f"tenant_id = ${len(params)}")
        if agent_id:
            params.append(agent_id)
            conditions.append(f"agent_id = ${len(params)}")
        params.append(max(1, int(limit)))
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT tenant_id, agent_id, episode_id, event_type, content_ref, summary,
                   tags, embedding_ref, metadata, last_event_id, last_event_ts,
                   updated_at, deleted
            FROM arqonbus_continuum_projection
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ${len(params)}
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [
            {
                "tenant_id": row["tenant_id"],
                "agent_id": row["agent_id"],
                "episode_id": row["episode_id"],
                "event_type": row["event_type"],
                "content_ref": row["content_ref"],
                "summary": row["summary"],
                "tags": list(row["tags"] or []),
                "embedding_ref": row["embedding_ref"],
                "metadata": dict(row["metadata"] or {}),
                "last_event_id": row["last_event_id"],
                "last_event_ts": row["last_event_ts"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "deleted": bool(row["deleted"]),
            }
            for row in rows
        ]

    async def continuum_projector_dlq_push(self, reason: str, event: Dict[str, Any]) -> Dict[str, Any]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        dlq_id = f"dlq_{event.get('event_id', 'evt')}_{datetime.now(timezone.utc).timestamp()}"
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO arqonbus_continuum_projection_dlq (dlq_id, reason, event)
                VALUES ($1, $2, $3::jsonb)
                """,
                dlq_id,
                reason,
                json.dumps(event),
            )
            row = await conn.fetchrow(
                "SELECT queued_at FROM arqonbus_continuum_projection_dlq WHERE dlq_id = $1",
                dlq_id,
            )
        return {
            "dlq_id": dlq_id,
            "topic": "continuum.episode.dlq.v1",
            "reason": reason,
            "event": event,
            "queued_at": row["queued_at"].isoformat() if row else datetime.now(timezone.utc).isoformat(),
        }

    async def continuum_projector_dlq_list(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT dlq_id, reason, event, queued_at
                FROM arqonbus_continuum_projection_dlq
                ORDER BY queued_at DESC
                LIMIT $1
                """,
                max(1, int(limit)),
            )
        return [
            {
                "dlq_id": row["dlq_id"],
                "reason": row["reason"],
                "event": dict(row["event"]),
                "queued_at": row["queued_at"].isoformat(),
                "topic": "continuum.episode.dlq.v1",
            }
            for row in rows
        ]

    async def continuum_projector_dlq_get(self, dlq_id: str) -> Optional[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT dlq_id, reason, event, queued_at
                FROM arqonbus_continuum_projection_dlq
                WHERE dlq_id = $1
                """,
                dlq_id,
            )
        if row is None:
            return None
        return {
            "dlq_id": row["dlq_id"],
            "reason": row["reason"],
            "event": dict(row["event"]),
            "queued_at": row["queued_at"].isoformat(),
            "topic": "continuum.episode.dlq.v1",
        }

    async def continuum_projector_dlq_remove(self, dlq_id: str) -> bool:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM arqonbus_continuum_projection_dlq WHERE dlq_id = $1",
                dlq_id,
            )
        return result.endswith("1")

    async def continuum_projector_events_between(
        self,
        *,
        from_ts: datetime,
        to_ts: datetime,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Postgres projector backend unavailable")
        conditions = ["source_ts >= $1", "source_ts <= $2"]
        params: List[Any] = [from_ts, to_ts]
        if tenant_id:
            params.append(tenant_id)
            conditions.append(f"tenant_id = ${len(params)}")
        if agent_id:
            params.append(agent_id)
            conditions.append(f"agent_id = ${len(params)}")
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT event
            FROM arqonbus_continuum_projection_events
            WHERE {where_clause}
            ORDER BY source_ts ASC
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row["event"]) for row in rows]
