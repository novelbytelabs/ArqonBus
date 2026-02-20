import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from arqonbus.storage.postgres import PostgresStorageBackend


pytestmark = [pytest.mark.integration]


def _postgres_test_url() -> str:
    return os.getenv(
        "ARQONBUS_TEST_POSTGRES_URL",
        "postgresql://arqonbus:arqonbus@127.0.0.1:5432/arqonbus",
    )


def _event(
    *,
    tenant_id: str,
    agent_id: str,
    episode_id: str,
    event_id: str,
    source_ts: str,
    event_type: str = "episode.created",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "episode_id": episode_id,
        "source_ts": source_ts,
        "schema_version": 1,
        "payload": {
            "content_ref": f"sqlite://continuum/episodes/{episode_id}",
            "summary": "episode summary",
            "tags": ["memory", "test"],
            "embedding_ref": None,
            "metadata": {"source": "integration-test"},
        },
    }


async def _build_backend_or_skip() -> PostgresStorageBackend:
    url = _postgres_test_url()
    try:
        return await PostgresStorageBackend.create(
            {
                "postgres_url": url,
                "storage_mode": "strict",
                "max_size": 1000,
            }
        )
    except Exception as exc:
        pytest.skip(f"Postgres integration unavailable at {url}: {exc}")


@pytest.mark.asyncio
async def test_continuum_projector_persistence_round_trip():
    backend = await _build_backend_or_skip()
    tenant = f"tenant-it-{uuid.uuid4().hex[:8]}"
    agent = "agent-it"
    episode = "episode-it-1"
    now = datetime.now(timezone.utc)
    created_ts = now.isoformat()
    stale_ts = (now - timedelta(seconds=5)).isoformat()

    try:
        async with backend.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection_events WHERE tenant_id = $1",
                tenant,
            )
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection WHERE tenant_id = $1",
                tenant,
            )
            await conn.execute(
                "DELETE FROM arqonbus_continuum_projection_dlq WHERE event->>'tenant_id' = $1",
                tenant,
            )

        first = await backend.continuum_project_event(
            _event(
                tenant_id=tenant,
                agent_id=agent,
                episode_id=episode,
                event_id="evt-created",
                source_ts=created_ts,
                event_type="episode.created",
            )
        )
        assert first["status"] == "projected"

        duplicate = await backend.continuum_project_event(
            _event(
                tenant_id=tenant,
                agent_id=agent,
                episode_id=episode,
                event_id="evt-created",
                source_ts=created_ts,
                event_type="episode.created",
            )
        )
        assert duplicate["status"] == "duplicate"

        stale = await backend.continuum_project_event(
            _event(
                tenant_id=tenant,
                agent_id=agent,
                episode_id=episode,
                event_id="evt-stale",
                source_ts=stale_ts,
                event_type="episode.updated",
            )
        )
        assert stale["status"] == "stale_rejected"

        projection = await backend.continuum_projector_get(tenant, agent, episode)
        assert projection is not None
        assert projection["last_event_id"] == "evt-created"
        assert projection["tenant_id"] == tenant

        listed = await backend.continuum_projector_list(limit=10, tenant_id=tenant, agent_id=agent)
        assert len(listed) >= 1

        stats = await backend.continuum_projector_status()
        assert stats["projection_count"] >= 1
        assert stats["seen_event_count"] >= 1

        dlq = await backend.continuum_projector_dlq_push(
            "integration_test",
            _event(
                tenant_id=tenant,
                agent_id=agent,
                episode_id=episode,
                event_id="evt-dlq",
                source_ts=created_ts,
            ),
        )
        assert "dlq_id" in dlq

        dlq_get = await backend.continuum_projector_dlq_get(dlq["dlq_id"])
        assert dlq_get is not None
        assert dlq_get["reason"] == "integration_test"

        dlq_list = await backend.continuum_projector_dlq_list(limit=20)
        assert any(item["dlq_id"] == dlq["dlq_id"] for item in dlq_list)

        removed = await backend.continuum_projector_dlq_remove(dlq["dlq_id"])
        assert removed is True

        between = await backend.continuum_projector_events_between(
            from_ts=now - timedelta(minutes=5),
            to_ts=now + timedelta(minutes=5),
            tenant_id=tenant,
            agent_id=agent,
        )
        assert any(item["event_id"] == "evt-created" for item in between)
    finally:
        await backend.close()
