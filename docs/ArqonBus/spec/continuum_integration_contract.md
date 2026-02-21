# Arqon Continuum <-> ArqonBus Integration Contract (v0.1)

Status: Active  
Last Updated: 2026-02-20  
Owners: ArqonBus + Arqon Continuum maintainers

## 1. Scope and Roles

- `Arqon Continuum` owns canonical episodic memory in local hot path (`SAS + Sled + SQLite`).
- `ArqonBus` owns shared coordination, distributed state propagation, and governance transport.
- `Postgres` is a global durable projection surface, not Continuum's primary write path.
- `Valkey` is distributed hot-state/coordination, not canonical episode storage.

## 2. Data Ownership

- Canonical episode record: Continuum (`SQLite`).
- Canonical distributed coordination state: Bus + Valkey.
- Canonical global audit/governance projection: Postgres.

## 3. Event Contract (Continuum -> Bus)

Topic:
- `continuum.episode.v1`

Required envelope fields:
- `event_id` (UUIDv7 or ULID string)
- `event_type` (`episode.created|episode.updated|episode.deleted|episode.summarized`)
- `tenant_id`
- `agent_id`
- `episode_id` (ULID string)
- `source_ts` (UTC ISO8601)
- `schema_version` (`1`)

Required payload fields:
- `content_ref` (opaque pointer; avoid full body on hot path)
- `summary` (optional short text)
- `tags` (array of strings)
- `embedding_ref` (optional)
- `metadata` (object)

Delivery semantics:
- At-least-once delivery.
- Idempotent consumption via `(tenant_id, agent_id, event_id)`.
- Sensitive content remains local unless explicit policy permits export.

## 4. Projection Contract (Bus -> Postgres)

- Async projector consumes `continuum.episode.v1`.
- Upsert key: `(tenant_id, agent_id, episode_id)`.
- Dedup key: `event_id`.
- Monotonic guard: maintain `last_event_ts` and reject stale out-of-order updates.
- Stale update handling: log + metric + no overwrite.

## 5. Valkey Contract

Allowed key families:
- `tenant:{tenant_id}:agent:{agent_id}:presence:*`
- `tenant:{tenant_id}:agent:{agent_id}:rate_limit:*`
- `tenant:{tenant_id}:episode:{episode_id}:cache:*` (short TTL only)

Rules:
- All keys must be tenant-prefixed.
- No canonical episode bodies in Valkey.
- Coordination/cache only.

## 6. Consistency and Failure Semantics

- Continuum local episode writes must not depend on Bus availability.
- Export pipeline is async retryable.
- Dead-letter topic:
  - `continuum.episode.dlq.v1`
- Fail-closed: auth/policy violations.
- Fail-open: analytics projection path only (must not block local writes).

## 7. Security and Isolation

- mTLS/JWT between Continuum producer and Bus ingress.
- Tenant isolation required in topic namespace, Valkey keys, and Postgres rows.
- Redaction and policy gates must run before publish.
- All control-plane actions in projector/replay flows are auditable.

## 8. Replay and Backfill

- Replay source of truth: Continuum change-log/export cursor.
- Replay idempotency key: `event_id`.
- Backfill control parameters:
  - `from_ts`
  - `to_ts`
  - `tenant_id`
  - `agent_id`
  - `dry_run`

## 9. SLO Targets

- Local episode write p99: unchanged from Continuum baseline.
- Event publish p99 (in-cluster): < 20 ms.
- Projection lag p95: < 5 s.
- Duplicate projection rate: < 0.1%.

## 10. Rollout Phases

1. Emit-only: Continuum publishes events; no Postgres serving dependency.
2. Shadow projection: projector writes Postgres but is non-serving.
3. Read-only analytics on Postgres projection.
4. Enable replay/backfill with operational runbook.
5. Enforce alerts on lag, DLQ volume, and projection error rates.

## 11. Reflex Boundary Rules

- Reflex hot-path memory/indexing (`RAM/Sled`) remains in-process and local to Reflex.
- Bus integration from Reflex is asynchronous (`publish/subscribe`) and coordination-only.
- Bus contracts must not require Reflex to route canonical episode content through Valkey/Postgres.
- Valkey usage for Reflex coordination remains tenant-scoped key families only.
- Any Reflex-facing payload published through Bus should use references/pointers, not raw hot-path state dumps.
