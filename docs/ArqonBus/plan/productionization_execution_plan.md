# ArqonBus Productionization Execution Plan

Last updated: 2026-02-19  
Branch: `dev/vnext-innovation-execution`  
Primary input: `docs/ArqonBus/plan/production_readiness_assessment.md`

## Objective

Close all known production-readiness gaps with test-gated, fail-closed engineering changes and no behavior regressions.

## Principles

- Fail closed for security and durability-critical controls.
- No hidden runtime stubs/mocks in production paths.
- No silent semantic downgrades (explicit modes only).
- Tests first for high-risk changes; tests immediately after each risky move.

## Phase Plan

## Phase 0: Baseline Lockdown (Critical Blockers)

Scope:

- Remove package shadowing risk from local `src/aiohttp/**`.
- Close dependency contract (`dotenv` package mismatch).
- Add production preflight checks for critical env vars.

Target files:

- `src/aiohttp/__init__.py`
- `src/arqonbus/transport/http_server.py`
- `src/arqonbus/server.py`
- `pyproject.toml`
- `docs/ArqonBus/runbooks/production_preflight_runbook.md`

Test gate:

- `conda run -n helios-gpu-118 pytest -q tests/unit tests/integration --maxfail=20`
- Packaging smoke:
  - `conda run -n helios-gpu-118 python -m pip install -e .`
  - import smoke for `arqonbus.server` and `arqonbus.transport.http_server`

Exit criteria:

- No `src/aiohttp` shipped as runtime package.
- Fresh env imports succeed without missing runtime modules.

## Phase 1: Auth/Security Hardening

Scope:

- Enforce strict JWT secret requirements in Shield.
- Prohibit skip-validation in non-test runs.

Target files:

- `crates/shield/src/auth/jwt.rs`
- `crates/shield/src/handlers/socket.rs`
- `crates/shield/src/main.rs`

Test gate:

- `cargo check -p shield`
- `cargo test -p shield --tests`
- New regression tests for:
  - missing `JWT_SECRET` startup failure
  - skip-validation rejected in non-test profile

Exit criteria:

- Production profile cannot start with default/predictable auth secret.
- No auth bypass path outside tests.

## Phase 2: Storage Semantics Hardening

Scope:

- Add explicit storage mode (`strict` vs `degraded`).
- Ensure consumer-group capability signaling is explicit.

Target files:

- `src/arqonbus/storage/redis_streams.py`
- `src/arqonbus/config/config.py`
- `src/arqonbus/server.py`

Test gate:

- Integration tests for Redis unavailable behavior in both modes.
- Regression tests for consumer-group operations under each mode.

Exit criteria:

- No silent durability downgrade in strict mode.
- Degraded mode emits explicit telemetry and health status.

## Phase 3: Runtime Integrity and Error Discipline

Scope:

- Remove/feature-gate prototype synthesis operator path.
- Replace fail-silent exception blocks in hot loops with structured handling.

Target files:

- `src/arqonbus/protocol/synthesis_operator.py`
- `src/arqonbus/transport/websocket_bus.py`
- `src/arqonbus/storage/redis_streams.py`

Test gate:

- Unit + integration tests for cancellation/error semantics.
- Regression tests for no-silent-fail behavior.

Exit criteria:

- No untracked silent exception swallow in hot paths.

## Phase 4: Config/Deployment Hardening

Scope:

- Remove hardcoded runtime ports where still present.
- Require validated env config for all external interfaces.

Target files:

- `src/arqonbus/server.py`
- `src/arqonbus/config/config.py`

Test gate:

- Startup tests across env profiles (`dev`, `staging`, `prod`).

Exit criteria:

- Deploy profile controls bind/port/critical service URLs.

## Phase 5: Final Validation and Release Readiness

Scope:

- Run full matrix: unit, integration, e2e, regression, adversarial.
- Ensure docs/runbooks/checklists match code behavior.

Test gate (minimum):

- Python: unit + integration + targeted e2e + regression + adversarial suite
- Rust: `cargo check -p shield` + `cargo test -p shield --tests`

Exit criteria:

- All gates green in CI.
- Runbook and operator docs complete.

## Sequencing and Cadence

1. Commit Phase 0 independently.
2. Run tests after each high-risk change batch.
3. Commit each phase with explicit checkpoint notes.
4. Do not proceed to next phase if current phase gates are red.
