# ArqonBus vNext Status (Single Source of Truth)

Last updated: 2026-02-20
Branch: `dev/vnext-innovation-execution`
Program status: Phase0-7 complete for current slice; Continuum/Reflex integration track now active

## Why this file exists

Status interpretation: milestones through the current branch slice are complete; remaining "in progress" reflects roadmap scope outside this slice.

This is the canonical status file for vNext execution. If any other document conflicts
with this file, this file wins until the conflicting document is updated.

## Scope Freeze (Phase 0)

Epoch 1 scope freeze is complete. As of 2026-02-18, Checkpoint 2.2 is green and
execution has moved into Epoch 2 bootstrap work.

Current implementation scope:

- Epoch 2 Factory gate closure (CLI/SDK/operators/policy hot reload)
- Epoch 3 Tier-Omega experimental lane bootstrap (feature-flagged, isolated)
- Tier-Omega lifecycle hardening (bounded substrates/events with admin controls)
- Stability hardening discovered during manual gate validation
- Storage substrate expansion (Valkey aliases + Postgres backend)
- Tier-Omega Firecracker runtime integration (`op.omega.vm.*`)
- Continuum/Reflex integration contract baseline

Out of scope for this slice:

- Epoch 2 observability dashboard packaging
- Tier-Omega autonomous optimization loops or non-isolated substrate execution

## Program Milestones

| Milestone | Status | Notes |
| --- | --- | --- |
| M0: Baseline and truth alignment | Completed | Canonical status file and doc links aligned. |
| M1: Core Python stability pass | Completed | Dispatch/auth/http/websocket stabilization merged on branch. |
| M2: Test/Quality hardening gate | Completed | Unit/integration/e2e/regression + coverage/codecov wired. |
| M3: Epoch 2 Factory gate | Completed | CLI + SDK + standard operators + CASIL hot reload checkpoint closed. |
| M4: Tier-Omega experimental lane | Completed | Added feature-flagged `op.omega.*` path with unit/integration/e2e/regression coverage. |
| M5: Tier-Omega lifecycle hardening | Completed | Added substrate/event lifecycle controls and bounded lane governance. |
| M6: Valkey/Postgres + Tier-Omega Firecracker runtime | Completed | Added `valkey*` aliases, `postgres` backend, compose service, and `op.omega.vm.probe|list|launch|stop`. |
| M7: Continuum/Reflex integration contract baseline | Completed | Added contract spec + executable contract stubs for event/idempotency/failure semantics. |
| M8: Continuum projector/replay implementation | Completed | Added `op.continuum.projector.*` command lane with projection, stale guard, DLQ replay/list, and backfill controls. |
| M9: Postgres-backed projector persistence | Completed | Added Postgres projection/events/DLQ tables and backend hooks consumed by projector lane. |
| M10: Production data-stack hardening | Completed | Production preflight now requires both Valkey and Postgres URLs by default, plus real connectivity checks. |

## Phase 0 Completion Checklist

- [x] Canonical vNext status file created
- [x] Scope freeze defined for Epoch 1
- [x] Contradictory status docs marked and aligned
- [x] Execution branch created from `dev`

## Phase 1 Completion Checklist

- [x] Dispatch regression fixes started
- [x] Operator registration auth behavior made configurable
- [x] High-risk TODOs in hot-path modules removed/closed
- [x] Test layers made explicit in pytest configuration
- [x] Optional Integriguard/RSI dependency paths gated
- [x] CI profile split committed (`core`, `integration`, `performance`)

## Validation Commands

Core stability checks:

```bash
python -m pytest -q tests/unit
python -m pytest -q tests/test_dispatcher.py tests/test_dispatch_integration.py tests/test_dispatch_e2e.py
```

Optional external checks:

```bash
python -m pytest -q -m external
python -m pytest -q tests/integration
python -m pytest -q -m performance
```

## Phase 2: Test and Coverage Hardening

- [x] Explicit suite taxonomy: `unit`, `integration`, `e2e`, `regression`
- [x] Regression tests added for Phase 1 bugfixes
- [x] CI split into unit/integration/e2e/regression jobs
- [x] Combined coverage gate with XML export
- [x] Codecov upload workflow + repository config

## Phase 3: Socket-Gated Test Reliability

- [x] Socket capability marker added (`socket`)
- [x] Runtime skip/fail policy added for socket-required tests
- [x] CI e2e job enforces socket capability (`ARQONBUS_REQUIRE_SOCKET_TESTS=1`)
- [x] Optional performance job enforces socket capability
- [x] Added unit tests for command authorization/admin/http transport behavior

## Phase 4: Monitoring + Deployment Polish (Current Slice Completed)

- [x] Added HTTP `/version` endpoint
- [x] Added HTTP request instrumentation wrapper (count, latency, errors)
- [x] Added unit tests for `/version` and tracked handler metrics/error paths
- [x] Added top-level docs runbook entrypoint (`docs/runbook.md`)
- [x] Fixed README/docs index links to canonical architecture/API/runbook docs

## Phase 5: Epoch 2 Factory Bootstrap (Completed)

- [x] Added first-party `arqon` CLI entrypoint (`status`, `version`, `tail`)
- [x] Added minimal Python SDK client for JWT-authenticated WebSocket usage
- [x] Added unit/integration/e2e coverage for CLI + SDK bootstrap paths
- [x] Added regression coverage for RFC3339 `Z` timestamp envelope parsing
- [x] Added standard operator starter pack (`op.webhook`, `op.cron`, `op.store`)
- [x] Added SDK hello-world bot path (`examples/python/hello_world_bot.py`) with e2e validation
- [x] Added live CASIL policy hot reload command path (`op.casil.reload`) with integration/e2e coverage

## Phase 6: Tier-Omega Experimental Lane (Completed)

- [x] Added Tier-Omega config surface (`ARQONBUS_OMEGA_*`) with validation and config export
- [x] Added isolated Tier-Omega command lane (`op.omega.status|register_substrate|list_substrates|emit_event|list_events`)
- [x] Enforced admin-only mutation commands and explicit feature-disabled response (`FEATURE_DISABLED`)
- [x] Added unit/integration/e2e regression coverage for lane behavior and event retention window

## Phase 7: Tier-Omega Lifecycle Hardening (Completed)

- [x] Added bounded substrate governance (`ARQONBUS_OMEGA_MAX_SUBSTRATES`) with validation/export coverage
- [x] Added admin lifecycle commands (`op.omega.unregister_substrate`, `op.omega.clear_events`)
- [x] Added event query filters (`substrate_id`, `signal`) for `op.omega.list_events`
- [x] Added unit/integration/e2e/regression coverage for lifecycle controls and filter isolation

## Phase 8: Storage + Runtime Substrate Expansion (Completed)

- [x] Added storage backend aliases (`valkey`, `valkey_streams`) and strict preflight support for Valkey envs
- [x] Added Postgres storage backend and runtime wiring (`ARQONBUS_STORAGE_BACKEND=postgres`)
- [x] Added Postgres service in `deploy/docker-compose.yml`
- [x] Added Tier-Omega Firecracker runtime integration and admin VM controls (`op.omega.vm.*`)
- [x] Added unit/integration coverage for new storage/runtime behavior

## Phase 9: Continuum/Reflex Integration Contract (Completed Baseline)

- [x] Added contract spec: `docs/ArqonBus/spec/continuum_integration_contract.md`
- [x] Linked contract from `docs/ArqonBus/spec/00_master_spec.md`
- [x] Added executable contract stubs: `tests/unit/test_continuum_integration_contract.py`

## Active Next Slice: Projector + Replay Delivery (In Progress)

- [x] Implement Continuum episode projector (Bus -> Postgres) with idempotent upsert keying
- [x] Implement stale update rejection by monotonic `source_ts`
- [x] Implement DLQ emission path: `continuum.episode.dlq.v1`
- [x] Implement replay/backfill control path (`from_ts`, `to_ts`, `tenant_id`, `agent_id`, `dry_run`)
- [x] Add integration/regression suites for projector/replay/failure injection

## Verification Evidence (2026-02-20)

- [x] Valkey connection check passed (`ARQONBUS_VALKEY_URL=redis://127.0.0.1:6379/0`)
- [x] Postgres connection check passed (`ARQONBUS_POSTGRES_URL=postgresql://arqonbus:arqonbus@127.0.0.1:5432/arqonbus`)
- [x] Real Postgres integration test passed (`tests/integration/test_continuum_projector_postgres.py`)

## Epoch 1 Checkpoint 2.2 Progress

- [x] WebSocket connect path validated with authenticated test client
- [x] JWT authentication enforced at edge (missing/invalid/expired rejected)
- [x] Authenticated room echo validated between two clients
- [x] Safety policy blocking validated in enforce mode (bad payload not routed)
- [x] Manual `wscat` handshake validation completed in sandbox on 2026-02-18 (unauthenticated `401`; authenticated connect + welcome)
