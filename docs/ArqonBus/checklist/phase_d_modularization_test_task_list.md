# Phase D Test Task List: Modularization and Operator Runtime

Last updated: 2026-02-19  
Scope: decompose `websocket_bus.py` and preserve behavior parity

## Unit Tests

- [ ] Add unit tests for extracted operator modules (`webhook`, `cron`, `store`, `omega`).
  - Proposed files:
    - `tests/unit/test_operator_webhook_service.py`
    - `tests/unit/test_operator_cron_service.py`
    - `tests/unit/test_operator_store_service.py`
    - `tests/unit/test_operator_omega_service.py`
- [ ] Add unit tests for extracted handshake/auth module.
  - Proposed file: `tests/unit/test_transport_handshake_auth.py`
- [ ] Add unit tests for extracted envelope processing/dispatch module.
  - Proposed file: `tests/unit/test_transport_envelope_pipeline.py`

## Integration Tests

- [ ] Add integration tests for modularized transport pipeline with storage and routing coordinator.
  - Proposed file: `tests/integration/test_transport_modular_pipeline.py`
- [ ] Add integration tests for SAM handshake/capability contract validation.
  - Proposed file: `tests/integration/test_sam_handshake_contract.py`
- [ ] Add integration tests for module-level tenant isolation in operator services.
  - Proposed file: `tests/integration/test_operator_module_tenant_isolation.py`

## End-to-End Tests

- [ ] Add parity e2e suite proving no behavior regressions after modularization.
  - Proposed file: `tests/integration/test_transport_parity_e2e.py`
- [ ] Add end-to-end slash-command/operator flow tests through modularized transport path.
  - Proposed file: `tests/integration/test_operator_runtime_e2e.py`

## Regression Tests

- [ ] Add regression tests for previously fixed hot-path bugs in monolith split.
  - Proposed file: `tests/regression/test_transport_modularization_regressions.py`
- [ ] Add regression tests for command auth and stale-closure style state bugs.
  - Proposed file: `tests/regression/test_transport_state_regressions.py`
- [ ] Add regression tests for Tier-Omega lane lifecycle invariants under refactor.
  - Proposed file: `tests/regression/test_omega_modularization_regressions.py`

## Acceptance Gate

- [ ] `src/arqonbus/transport/websocket_bus.py` reduced to orchestration shell.
- [ ] All extracted modules have unit + integration + e2e + regression coverage.
- [ ] Pre-modularization behavior parity proven by e2e and regression suites.

