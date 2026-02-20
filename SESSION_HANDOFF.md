# ArqonBus Session Handoff

Last updated: 2026-02-20

## Current status
Productionization and Continuum integration slices are complete through projector persistence, operational hardening, CI postgres gating, and release-gate closeout hardening.

## Latest completed work (unreleased in this handoff snapshot)
- Added release-candidate notes artifact:
  - `docs/ArqonBus/releases/2026-02-20_v0.1.0-rc1.md`
- Added rollout smoke automation script:
  - `scripts/manual_checks/rollout_smoke_check.sh`
- Added Reflex integration boundary spec and linked companion references:
  - `docs/ArqonBus/spec/reflex_integration_boundary.md`
  - `docs/ArqonBus/spec/00_master_spec.md`
  - `docs/ArqonBus/spec/continuum_integration_contract.md`
- Extended executable cross-project boundary checks:
  - `tests/unit/test_continuum_integration_contract.py`
- Updated runbook/status for release execution track:
  - `docs/ArqonBus/checklist/runbook.md`
  - `docs/ArqonBus/vnext_status.md`
- Added websocket command-lane history semantics:
  - `src/arqonbus/transport/websocket_bus.py` (`op.history.get|replay` + aliases)
  - room-scoped fail-closed access for non-admin clients
  - replay window and strict-sequence contract responses
- Added history command-lane tests:
  - `tests/unit/test_history_command_lane.py`
  - `tests/integration/test_history_command_e2e.py`
- Added protobuf/replay latency performance gates:
  - `tests/performance/test_replay_protobuf_latency_gates.py`
  - `.github/workflows/arqonbus-tests.yml` (performance selector now `performance and not external`)
- Added RC hardening checklist:
  - `docs/ArqonBus/checklist/release_candidate_hardening_2026-02-20.md`
- Updated API/runbook/docs for history command-lane contracts:
  - `docs/ArqonBus/spec/api.md`
  - `docs/ArqonBus/checklist/runbook.md`
  - `docs/ArqonBus/checklist/productionization_checklist.md`
  - `docs/ArqonBus/vnext_status.md`
- Added Phase C protocol/time semantics test closure:
  - `src/arqonbus/protocol/time_semantics.py`
  - `src/arqonbus/protocol/validator.py` (sequence/vector/causal metadata validation)
  - `src/arqonbus/storage/interface.py` (`get_history_replay` API with strict sequence checks)
  - `src/arqonbus/storage/memory.py` (timezone-safe replay filtering)
  - `src/arqonbus/protocol/ids.py` (ULID-style compatibility for cross-language fixture IDs)
  - `tests/unit/test_ids_validation.py`
  - `tests/unit/test_timekeeper_sequence.py`
  - `tests/unit/test_vector_clock.py`
  - `tests/integration/test_history_get_replay.py`
  - `tests/integration/test_json_adapter_compat.py`
  - `tests/integration/test_proto_contract_crosslang.py`
  - `tests/integration/test_time_ordering_e2e.py`
  - `tests/integration/test_history_replay_e2e.py`
  - `tests/regression/test_time_envelope_regressions.py`
  - `tests/regression/test_proto_json_adapter_regressions.py`
  - `tests/regression/test_proto_evolution_regressions.py`
  - `docs/ArqonBus/checklist/phase_c_protocol_time_test_task_list.md`
  - `docs/ArqonBus/vnext_status.md`
- Added Postgres-backed socket e2e test for Continuum projector lane:
  - `tests/integration/test_continuum_projector_postgres_e2e.py`
- Added projector metrics instrumentation (lag/DLQ/replay/backfill):
  - `src/arqonbus/transport/websocket_bus.py`
  - `tests/unit/test_continuum_projector_lane.py`
- Added Postgres migration SQL + backup/restore runbook:
  - `scripts/migrations/20260220_continuum_projector_postgres.sql`
  - `docs/ArqonBus/runbooks/continuum_projector_postgres_migration_backup_restore.md`
- Added dedicated CI stage for live Postgres projector tests:
  - `.github/workflows/arqonbus-tests.yml`
- Added release-gate closeout note:
  - `docs/ArqonBus/checklist/release_gate_closeout_2026-02-20.md`
- Replaced synthesis prototype behavior with concrete deterministic operator logic:
  - `src/arqonbus/protocol/synthesis_operator.py`
  - `tests/regression/test_phase3_runtime_integrity.py`
- Added production preflight rejection for auth bypass toggle:
  - `src/arqonbus/config/config.py`
  - `tests/unit/test_startup_preflight.py`
- Added ignore for local Valkey snapshot artifact:
  - `.gitignore` (`dump.rdb`)
- Added protobuf-first infrastructure envelope codec and wire parsing:
  - `src/arqonbus/protocol/protobuf_codec.py`
  - `src/arqonbus/protocol/envelope.py`
  - `src/arqonbus/protocol/validator.py`
  - `src/arqonbus/proto/envelope_pb2.py`
  - `src/arqonbus/proto/bus_payload.proto`
  - `src/arqonbus/proto/bus_payload_pb2.py`
- Added protobuf-first storage persistence for infra envelopes:
  - `src/arqonbus/storage/postgres.py` (`envelope_proto` bytea path)
  - `src/arqonbus/storage/redis_streams.py` (`envelope_proto_b64` stream field)
- Added strict preflight policy for protobuf infra in staging/prod:
  - `src/arqonbus/config/config.py`
  - `tests/unit/test_startup_preflight.py`
- Added anti-regression CI/protocol contract guardrails:
  - `scripts/ci/check_protobuf_first.py`
  - `.github/workflows/arqonbus-tests.yml` (`protobuf-contract` job)
  - `tests/unit/test_protobuf_contract_fixture.py`
  - `crates/proto/tests/protobuf_contract_fixture.rs`
  - `crates/proto/tests/fixtures/python_envelope.bin`

## Recent completed work (latest first)
- `fe8a34a` - `hardening: require valkey+postgres stack in prod preflight`
  - Production preflight now requires both Valkey and Postgres URLs by default in `prod`.
  - Added real connectivity checks:
    - `scripts/manual_checks/redis_connection_check.py`
    - `scripts/manual_checks/postgres_connection_check.py`
  - Added real integration test (live Postgres path):
    - `tests/integration/test_continuum_projector_postgres.py`
- `358c27b` - `feat: persist continuum projector state via postgres backend hooks`
  - Added Postgres tables/hooks for Continuum projection/events/DLQ.
  - Wired projector lane to use backend hooks when available.
- `4a888ad` - `feat: add continuum projector lane with dlq and backfill controls`
  - Added `op.continuum.projector.*` command lane:
    - `status`, `project_event`, `get`, `list`
    - `dlq.list`, `dlq.replay`
    - `backfill`
- `776afce` - `plan: add continuum/reflex integration track and update vnext status`
- `2daf648` - `docs: add continuum-bus integration contract and executable stubs`
- `eb7fa43` - `feat: add valkey+postgres backends and tier-omega firecracker runtime`

## Verification evidence (2026-02-20)

User-validated local runtime checks:
- Valkey: `redis://127.0.0.1:6379/0` reachable.
- Postgres: `postgresql://arqonbus:arqonbus@127.0.0.1:5432/arqonbus` reachable.
- Integration: `tests/integration/test_continuum_projector_postgres.py` passed in native environment.

Agent-run test highlights in this session:
- `conda run -n helios-gpu-118 python -m pytest -q tests/unit/test_history_command_lane.py tests/integration/test_history_command_e2e.py tests/performance/test_replay_protobuf_latency_gates.py`
  - Result: passed (6 passed)
- `conda run -n helios-gpu-118 python -m pytest -q tests/unit/test_ids_validation.py tests/unit/test_timekeeper_sequence.py tests/unit/test_vector_clock.py tests/integration/test_history_get_replay.py tests/integration/test_json_adapter_compat.py tests/integration/test_proto_contract_crosslang.py tests/integration/test_time_ordering_e2e.py tests/integration/test_history_replay_e2e.py tests/regression/test_time_envelope_regressions.py tests/regression/test_proto_json_adapter_regressions.py tests/regression/test_proto_evolution_regressions.py`
  - Result: passed (17 passed)
- `conda run -n helios-gpu-118 python -m pytest -q tests/unit/test_ids_validation.py tests/unit/test_timekeeper_sequence.py tests/unit/test_vector_clock.py tests/unit/test_history_command_lane.py tests/integration/test_history_get_replay.py tests/integration/test_json_adapter_compat.py tests/integration/test_proto_contract_crosslang.py tests/integration/test_time_ordering_e2e.py tests/integration/test_history_replay_e2e.py tests/integration/test_history_command_e2e.py tests/regression/test_time_envelope_regressions.py tests/regression/test_proto_json_adapter_regressions.py tests/regression/test_proto_evolution_regressions.py`
  - Result: passed (21 passed)
- `conda run -n helios-gpu-118 python scripts/ci/check_protobuf_first.py`
  - Result: passed
- `conda run -n helios-gpu-118 python -m pytest -q tests/unit/test_continuum_projector_lane.py tests/unit/test_continuum_integration_contract.py tests/unit/test_tier_omega_lane.py tests/unit/test_startup_preflight.py tests/unit/test_postgres_storage.py --maxfail=20`
  - Result: passed
- `conda run -n helios-gpu-118 python -m pytest -q tests/unit/test_startup_preflight.py tests/unit/test_continuum_projector_lane.py tests/unit/test_postgres_storage.py --maxfail=20`
  - Result: passed

## Source-of-truth docs updated
- `docs/ArqonBus/vnext_status.md`
- `docs/ArqonBus/plan/vnext_innovation_execution_plan.md`
- `docs/ArqonBus/spec/continuum_integration_contract.md`
- `docs/ArqonBus/checklist/runbook.md`
- `docs/ArqonBus/runbooks/production_preflight_runbook.md`

## Fast resume checklist
1. `cd /home/irbsurfer/Projects/arqon/ArqonBus`
2. Confirm branch and cleanliness:
   - `git branch --show-current`
   - `git status --short`
3. Export local runtime URLs (if not already set):
   - `ARQONBUS_VALKEY_URL=redis://127.0.0.1:6379/0`
   - `ARQONBUS_POSTGRES_URL=postgresql://arqonbus:arqonbus@127.0.0.1:5432/arqonbus`
4. Run preflight checks:
   - `conda run -n helios-gpu-118 python scripts/manual_checks/redis_connection_check.py`
   - `conda run -n helios-gpu-118 python scripts/manual_checks/postgres_connection_check.py`
5. Run projector integration verification:
   - `conda run -n helios-gpu-118 python -m pytest -q tests/integration/test_continuum_projector_postgres.py`

## Notes
- Unrelated local modification remains: `.codex/config.toml` (left untouched intentionally).
