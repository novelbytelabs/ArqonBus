# Implementation Plan: Epoch 2 - The Platform (Detailed)

**Branch**: `004-epoch-2-platform`
**Spec**: `specs/004-epoch-2-platform/spec.md` (RFC-002)
**Objective**: Transform ArqonBus into a Programmable Logic Bus.

## Summary

This plan executes the "Platform Layer" upgrade defined in RFC-002. It involves three distinct workstreams executed in parallel where possible, converging on a unified Shield release.

1.  **Workstream A (Wasm)**: Implement `wasmtime` integration with Fuel limits and Host ABI.
2.  **Workstream B (Mirroring)**: Implement Coherent Shadowing middleware.
3.  **Workstream C (Governance)**: Implement Schema Registry and Enforcer.

## Technical Context

*   **Shield Core**: Expanding the Axum/Tower service stack.
*   **Wasm Engine**: Using `wasmtime` 16.0.
*   **Protobuf**: Using `prost` and `prost-reflect` for dynamic schema validation.
*   **NATS**: Using `async-nats` JetStream KV for schema storage.

## Constitution Invariants Checklist (Pre-Flight)

*   [x] **Fail Closed (II.7)**: Wasm engine must default to blocking if fuel runs out.
*   [x] **No "Swallow" (III.3)**: Shadowing errors (failed mirror) must be logged, but must NOT fail the primary request (Best Effort for Shadow, Atomic for Primary).
*   [x] **Observability (IX.1)**: New middlewares must emit `shield_` metrics.

## Execution Steps

### Phase 1: The Overseer (Rich Wasm Host)
*Goal: Enable programmable policy at the edge.*

1.  **Define ABI (`crates/shield/src/policy/abi.rs`)**:
    *   Define `Linker` extensions for `host_log`, `host_get_header`.
2.  **Implement Engine (`crates/shield/src/policy/engine.rs`)**:
    *   Add `wasmtime::Config` for Fuel consumption.
    *   Implement `validate_with_context(ctx)` method.
3.  **Implement Middleware (`crates/shield/src/middleware/wasm.rs`)**:
    *   Wrap Axum handlers.
    *   Extract Headers/IP -> Pass to Wasm -> Enforce Decision.
4.  **Verification**: Unit test with a compiled `.wasm` fixture that calls `host_log`.

### Phase 2: Traffic Mirroring (Shadowing)
*Goal: Enable safe testing of new consumers.*

1.  **Implement Hashing (`crates/shield/src/utils/hashing.rs`)**:
    *   Implement consistent hashing (e.g., `xxhash`) on TraceID string.
    *   Return `u64`.
2.  **Implement Logic (`crates/shield/router/nats_bridge.rs`)**:
    *   Modify `publish` function.
    *   Check `config.mirror_rules`.
    *   If `hash(trace_id) % 100 < percent`: Clone message, add `x-arqon-shadow`, publish to `shadow.{subject}`.
3.  **Verification**: Python script sending 100 requests with fixed TraceIDs, asserting deterministic mirroring.

### Phase 3: Schema Governance
*Goal: Reject bad data early.*

1.  **Schema Cache (`crates/shield/src/schema/registry.rs`)**:
    *   Implement NATS KV Watcher.
    *   Cache `FileDescriptorSet` in `Arc<RwLock<Map>>`.
2.  **Validator (`crates/shield/src/schema/validator.rs`)**:
    *   Use `prost-reflect` to validate bytes against descriptor.
3.  **Integration**:
    *   Hook into `ws_handler`. On message receive -> Validate -> Ack/Nack.
4.  **Verification**: Send invalid JSON payload vs valid Protobuf payload.

## Verification Plan (The "Definition of Done")

### 1. Automated Unit Tests (Rust)
*   [ ] `wasm::test_fuel_exhaustion`: Verify Wasm times out deterministically.
*   [ ] `hashing::test_consistency`: Verify same TraceID always produces same Hash.
*   [ ] `schema::test_malformed`: Verify `prost` rejects truncated bytes.

### 2. Integration Suite (`verification/epoch2_suite.py`)
*   [ ] **Wasm Block**: Upload policy that denies requests with header `X-Block-Me`. verify 403.
*   [ ] **Shadow Coherence**: Send 1 request. Verify it appears on both primary and shadow subjects.
*   [ ] **Schema Reject**: Publish invalid structure. Verify NATS Ack is Negative (or Connection Close).

### 3. Observability Audit
*   [ ] Verify `shield_wasm_execution_duration_seconds` appears in `/metrics`.
*   [ ] Verify Shadowed messages have `x-arqon-shadow: true` header.
