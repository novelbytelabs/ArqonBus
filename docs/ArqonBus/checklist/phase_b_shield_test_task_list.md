# Phase B Test Task List: Shield Correctness and Safety

Last updated: 2026-02-19  
Scope: `crates/shield/**` hardening and fail-closed correctness

## Unit Tests

- [ ] Add startup wiring tests for `AppState` construction and router assembly.
  - Target: `crates/shield/src/main.rs` (extract testable builders as needed)
- [x] Add JWT edge auth unit tests for missing/invalid/expired token behavior.
  - Target: `crates/shield/src/auth/jwt.rs`
- [ ] Add wasm middleware unit tests for body extraction + pass/deny/error behavior.
  - Target: `crates/shield/src/middleware/wasm.rs`
- [x] Add schema validator strict-mode unit tests (descriptor missing should fail in strict mode).
  - Target: `crates/shield/src/middleware/schema.rs`
- [ ] Replace stub-level protobuf validator cases with descriptor-backed validation tests.
  - Target: `crates/shield/src/registry/validator.rs`

## Integration Tests

- [ ] Add WebSocket auth integration tests against Shield HTTP upgrade path.
  - Proposed file: `crates/shield/tests/ws_auth_integration.rs`
- [ ] Add NATS publish routing tests with tenant-scoped subjects.
  - Proposed file: `crates/shield/tests/nats_subject_routing.rs`
- [ ] Add schema + policy chain integration tests (allow, deny, internal error).
  - Proposed file: `crates/shield/tests/middleware_chain.rs`
- [ ] Add tenant isolation integration tests (cross-tenant publish/subscribe rejection).
  - Proposed file: `crates/shield/tests/tenant_isolation.rs`
- [x] Add auth + schema fail-closed integration coverage.
  - Implemented file: `crates/shield/tests/integration_auth_schema.rs`

## End-to-End Tests

- [ ] Add full handshake + binary payload + echo + policy block e2e test using live Shield + NATS.
  - Proposed file: `crates/shield/tests/e2e_ws_policy_flow.rs`
- [ ] Add end-to-end fail-closed test for policy timeout/crash conditions.
  - Proposed file: `crates/shield/tests/e2e_fail_closed.rs`
- [x] Add policy engine e2e behavior test using real Wasm policy module.
  - Implemented file: `crates/shield/tests/e2e_policy_flow.rs`

## Regression Tests

- [ ] Add regression test for duplicate/invalid state wiring regressions in startup path.
  - Proposed file: `crates/shield/tests/regression_startup_wiring.rs`
- [x] Add regression test for anonymous fallback auth regressions.
  - Implemented file: `crates/shield/tests/regression_fail_closed.rs`
- [ ] Add regression test ensuring placeholder middleware payload path never returns in production code.
  - Proposed file: `crates/shield/tests/regression_payload_extraction.rs`

## Acceptance Gate

- [x] `cargo check -p shield` passes.
- [x] `cargo test -p shield --tests` passes.
- [x] Unit + Integration + E2E + Regression suites are present and green for the implemented Phase B slice.
