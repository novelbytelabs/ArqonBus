# Arqon Reflex <-> ArqonBus Integration Boundary (v0.1)

Status: Active  
Last Updated: 2026-02-20  
Owners: ArqonReflex + ArqonBus maintainers

## Scope

Define strict ownership and interaction boundaries so Reflex hot-path behavior is not degraded by Bus integration.

## Ownership

- Reflex owns local hot-path memory/indexing:
  - in-process RAM/SAS
  - local Sled structures
- ArqonBus owns distributed transport, coordination, and governance.
- Valkey/Postgres are shared coordination/projection substrates and are not Reflex canonical hot-path stores.

## Required Interaction Model

- Reflex -> Bus communication is asynchronous publish/subscribe.
- Bus must accept pointer/reference style payloads for Reflex-originated events.
- Bus must not require Reflex to serialize full local hot-path state into Valkey/Postgres.

## Forbidden Patterns

- Writing canonical Reflex episode/state bodies directly to Valkey.
- Treating Postgres as Reflex real-time read dependency for hot-path decisions.
- Global (non-tenant-prefixed) Valkey coordination keys for Reflex flows.

## Allowed Coordination Keys (Valkey)

- `tenant:{tenant_id}:agent:{agent_id}:presence:*`
- `tenant:{tenant_id}:agent:{agent_id}:rate_limit:*`
- `tenant:{tenant_id}:episode:{episode_id}:cache:*` (short TTL)

## Verification Hooks

- Contract tests: `tests/unit/test_continuum_integration_contract.py`
- Bus projector integration tests:
  - `tests/integration/test_continuum_projector_postgres.py`
  - `tests/integration/test_continuum_projector_postgres_e2e.py`
