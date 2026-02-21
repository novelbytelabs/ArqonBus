BEGIN;

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

COMMIT;
