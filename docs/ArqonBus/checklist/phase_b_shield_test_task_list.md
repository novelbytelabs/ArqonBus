# Phase B Test Task List: Shield Correctness and Safety

Last updated: 2026-02-19  
Scope: `crates/shield/**` hardening and fail-closed correctness

## Unit Tests

- [x] Add startup wiring tests for `AppState` construction and router assembly.
  - Implemented in `crates/shield/src/lib.rs` and `crates/shield/tests/regression_startup_wiring.rs`
- [x] Add JWT edge auth unit tests for missing/invalid/expired token behavior.
  - Target: `crates/shield/src/auth/jwt.rs`
- [x] Add wasm middleware unit tests for body extraction + pass/deny/error behavior.
  - Implemented in `crates/shield/src/middleware/wasm.rs`
- [x] Add schema validator strict-mode unit tests (descriptor missing should fail in strict mode).
  - Target: `crates/shield/src/middleware/schema.rs`
- [x] Replace stub-level protobuf validator cases with descriptor-backed validation tests.
  - Implemented in `crates/shield/src/registry/validator.rs`

## Integration Tests

- [x] Add WebSocket auth integration tests against Shield HTTP upgrade path.
  - Implemented file: `crates/shield/tests/ws_auth_integration.rs`
- [x] Add NATS publish routing tests with tenant-scoped subjects.
  - Implemented file: `crates/shield/tests/nats_subject_routing.rs`
- [x] Add schema + policy chain integration tests (allow, deny, internal error).
  - Implemented file: `crates/shield/tests/middleware_chain.rs`
- [x] Add tenant isolation integration tests (cross-tenant publish/subscribe rejection).
  - Implemented file: `crates/shield/tests/tenant_isolation.rs`
- [x] Add auth + schema fail-closed integration coverage.
  - Implemented file: `crates/shield/tests/integration_auth_schema.rs`

## End-to-End Tests

- [x] Add full handshake + binary payload + echo + policy block e2e test using live Shield + NATS.
  - Implemented with deterministic in-memory NATS bridge in `crates/shield/tests/e2e_ws_policy_flow.rs`
- [x] Add end-to-end fail-closed test for policy timeout/crash conditions.
  - Implemented file: `crates/shield/tests/e2e_fail_closed.rs`
- [x] Add policy engine e2e behavior test using real Wasm policy module.
  - Implemented file: `crates/shield/tests/e2e_policy_flow.rs`

## Regression Tests

- [x] Add regression test for duplicate/invalid state wiring regressions in startup path.
  - Implemented file: `crates/shield/tests/regression_startup_wiring.rs`
- [x] Add regression test for anonymous fallback auth regressions.
  - Implemented file: `crates/shield/tests/regression_fail_closed.rs`
- [x] Add regression test ensuring placeholder middleware payload path never returns in production code.
  - Implemented file: `crates/shield/tests/regression_payload_extraction.rs`

## Acceptance Gate

- [x] `cargo check -p shield` passes.
- [x] `cargo test -p shield --tests` passes.
- [x] Unit + Integration + E2E + Regression suites are present and green for the implemented Phase B slice.
