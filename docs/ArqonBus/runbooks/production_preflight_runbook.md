# Production Preflight Runbook

Last updated: 2026-02-19

## Purpose

Provide operators a deterministic preflight process before starting ArqonBus/Shield in production.

## Mandatory Preconditions

- Python environment is `helios-gpu-118`.
- Rust toolchain pinned to 1.82 for core crates.
- Required services reachable (Redis/Valkey, NATS, Ollama if enabled).

## Configuration Checklist

## ArqonBus

- [ ] `ARQONBUS_SERVER_HOST` set explicitly.
- [ ] `ARQONBUS_SERVER_PORT` set explicitly (no hardcoded defaults relied on).
- [ ] `ARQONBUS_STORAGE_MODE` set (`strict` recommended for production).
- [ ] `ARQONBUS_REDIS_URL` configured and reachable for strict mode.
- [ ] `ARQONBUS_TELEMETRY_HOST` / `ARQONBUS_TELEMETRY_PORT` configured.

## Shield

- [ ] `JWT_SECRET` configured with strong non-default value.
- [ ] `JWT_SKIP_VALIDATION` not set in production.
- [ ] `NATS_URL` configured and reachable.
- [ ] `ARQON_SCHEMA_STRICT=true` unless explicit, approved exception.

## Preflight Commands

Run from repo root (`ArqonBus`):

```bash
conda run -n helios-gpu-118 python -m pip install -e .
conda run -n helios-gpu-118 pytest -q tests/unit tests/integration --maxfail=20
cargo check -p shield
cargo test -p shield --tests
```

If any command fails, do not deploy.

## Runtime Sanity Checks

- [ ] ArqonBus health endpoint returns healthy.
- [ ] Telemetry endpoint accepts connection.
- [ ] Shield websocket upgrade path enforces auth rejection for missing token.
- [ ] Shield valid token path accepts and routes expected payload.

## Fail Conditions (Immediate Stop)

- Missing `JWT_SECRET` or detected default secret value.
- `JWT_SKIP_VALIDATION` present in production environment.
- Storage mode `strict` with Redis unavailable.
- Dependency import errors in clean environment.
- Any failing unit/integration/e2e/regression/adversarial gates.

## Incident Notes

When preflight fails, capture:

- git commit hash
- full failing command and stderr
- environment snapshot (non-secret vars)
- whether failure is config, dependency, or code regression

Route to engineering with severity label (`blocker`, `critical`, `high`).
