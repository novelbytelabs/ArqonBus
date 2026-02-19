# ArqonBus Production Readiness Assessment

Last updated: 2026-02-19  
Branch: `dev/vnext-innovation-execution`  
Scope: `src/**`, `crates/**`, packaging, runtime behavior

## Executive Summary

ArqonBus is not production-ready today. Core capabilities exist and the Shield Phase B work is substantially improved, but there are still critical release blockers in packaging integrity, authentication hardening, dependency completeness, and storage semantics.

## Assessment Method

- Static code scan for production-path anti-patterns (stubs/placeholders/fail-silent branches).
- Line-level review of security/auth, transport, storage, and packaging paths.
- Runtime verification smoke checks (`pytest` collection and targeted build/test commands).

## Findings (Severity Ordered)

### Critical 1: Local package shadowing of `aiohttp` in shipped source tree

Evidence:

- `src/aiohttp/__init__.py:1` defines a local package: "Minimal aiohttp stub for testing..."
- `src/arqonbus/transport/http_server.py:15` imports `from aiohttp import web, web_request, web_response`
- `pyproject.toml` package discovery includes `src/*`, so `aiohttp` is currently discoverable for packaging.

Risk:

- Production runtime can bind against local stub behavior instead of upstream `aiohttp`.
- PyPI artifact can include a top-level `aiohttp` package conflict.

Required closure:

- Remove/relocate the local stub from production package path.
- Keep test doubles under `tests/fixtures` or equivalent non-distributed path.

### Critical 2: Shield JWT fail-open toggles/defaults in runtime config

Evidence:

- `crates/shield/src/auth/jwt.rs:32` default secret fallback: `"arqon-dev-secret"`
- `crates/shield/src/auth/jwt.rs:33` validation bypass toggle from env presence
- `crates/shield/src/auth/jwt.rs:40` bypass path accepts unsigned claim decode path

Risk:

- Misconfiguration can create auth bypass or predictable secret use in production.

Required closure:

- Require explicit `JWT_SECRET` in non-test runs.
- Reject startup if secret absent/weak.
- Hard-disable `skip_validation` outside test profile.

### Critical 3: Runtime dependency contract is incomplete

Evidence:

- `src/arqonbus/server.py:12` imports `dotenv`
- `pyproject.toml` lacks `python-dotenv`
- Test collection failure observed: `ModuleNotFoundError: No module named 'dotenv'`

Risk:

- Clean environment installs/CI fail on import before service boot.

Required closure:

- Add `python-dotenv` as runtime dependency or remove runtime dependency on dotenv.
- Add dependency verification in CI.

### High 1: Redis storage silently degrades durability semantics

Evidence:

- `src/arqonbus/storage/redis_streams.py:137-168` falls back to memory on Redis failures.
- Consumer-group methods in fallback raise `NotImplementedError`:
  - `src/arqonbus/storage/redis_streams.py:509`
  - `src/arqonbus/storage/redis_streams.py:522`
  - `src/arqonbus/storage/redis_streams.py:569`
  - `src/arqonbus/storage/redis_streams.py:577`
  - `src/arqonbus/storage/redis_streams.py:587`

Risk:

- Production can quietly lose persistence/queue guarantees.

Required closure:

- Introduce explicit storage mode:
  - `strict` (fail startup if Redis unavailable)
  - `degraded` (allow fallback with loud telemetry and capability downgrade)

### High 2: Prototype/mock runtime operator path remains

Evidence:

- `src/arqonbus/protocol/synthesis_operator.py:8` states "mocked for now"

Risk:

- Unintended usage in production flows causes non-final behavior.

Required closure:

- Gate by feature flag + explicit non-prod profile, or replace with production implementation.

### High 3: Fail-silent exception handling in operational hot paths

Evidence (representative):

- `src/arqonbus/transport/websocket_bus.py:643-644` swallows non-cancel exceptions
- `src/arqonbus/storage/redis_streams.py:558-559` bare `except` with silent `pass`

Risk:

- Silent operational failures degrade reliability and observability.

Required closure:

- Replace with structured error paths and telemetry counters.

### Medium 1: Hardcoded server bind/port in runtime entrypoint

Evidence:

- `src/arqonbus/server.py:243` binds `0.0.0.0:8080`

Risk:

- Conflicts with operator environment and deployment topology.

Required closure:

- Environment-driven bind and port with preflight validation.

## Positive Baseline (Already Improved)

- Shield test coverage for Phase B is significantly improved and passing:
  - `cargo check -p shield`
  - `cargo test -p shield --tests`
- New integration/e2e/regression tests are present under `crates/shield/tests/**`.

## Exit Criteria for "Production Ready"

1. No test stubs/mocks/placeholders reachable in production runtime paths.
2. No auth-bypass toggles active in production binaries/services.
3. Startup fails closed on missing critical configuration.
4. Storage durability mode is explicit and observable (no silent downgrade).
5. Dependency graph is complete and reproducible from clean environment.
6. CI includes unit/integration/e2e/regression/adversarial gates for critical paths.

## Recommended Next Step

Proceed with Phase 0 from `docs/ArqonBus/plan/productionization_execution_plan.md` immediately after this assessment is committed.
