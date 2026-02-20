# Phase C Test Task List: Protocol and Time Semantics

Last updated: 2026-02-20  
Scope: protobuf-first contract, sequence/time semantics, replay APIs

## Unit Tests

- [x] Add envelope field conformance tests for spec-required headers and identifiers.
  - Targets: `src/arqonbus/protocol/envelope.py`, `src/arqonbus/protocol/validator.py`
- [x] Add monotonic sequence generator unit tests (per-reality ordering).
  - Proposed file: `tests/unit/test_timekeeper_sequence.py`
- [x] Add vector clock merge/compare unit tests.
  - Proposed file: `tests/unit/test_vector_clock.py`
- [x] Add protobuf schema encode/decode unit tests for canonical envelope.
  - Targets: `crates/proto/src/envelope.proto`, `crates/proto/src/lib.rs`

## Integration Tests

- [x] Add cross-language contract tests (Rust protobuf <-> Python adapter fixtures).
  - Proposed file: `tests/integration/test_proto_contract_crosslang.py`
- [x] Add integration tests for `history.get` time-bounded replay semantics.
  - Proposed file: `tests/integration/test_history_get_replay.py`
- [x] Add integration tests for backward-compatible JSON view adapters on top of protobuf payloads.
  - Proposed file: `tests/integration/test_json_adapter_compat.py`

## End-to-End Tests

- [x] Add end-to-end causal ordering scenario with partitioned operators and clock metadata.
  - Proposed file: `tests/integration/test_time_ordering_e2e.py`
- [x] Add end-to-end replay scenario validating strict time-window behavior.
  - Proposed file: `tests/integration/test_history_replay_e2e.py`

## Regression Tests

- [x] Add regression suite for timestamp parsing/format normalization and sequence continuity.
  - Proposed file: `tests/regression/test_time_envelope_regressions.py`
- [x] Add regression tests for protobuf schema evolution compatibility.
  - Proposed file: `tests/regression/test_proto_evolution_regressions.py`
- [x] Add regression tests for adapter drift (protobuf payload rendered as JSON view).
  - Proposed file: `tests/regression/test_proto_json_adapter_regressions.py`

## Acceptance Gate

- [x] Protobuf-first infra path enabled for target command/data surfaces.
- [x] Unit + Integration + E2E + Regression suites are present and green before merge.
- [x] Compatibility fixtures are versioned and reproducible.
