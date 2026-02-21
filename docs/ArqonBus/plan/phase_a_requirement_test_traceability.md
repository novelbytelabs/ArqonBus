# Phase A Requirement-to-Test Traceability

Last updated: 2026-02-19  
Branch: `dev/vnext-innovation-execution`

## Purpose

Provide a fact-based mapping from vNext requirements to automated test evidence and highlight gaps that block "full vNext ambition".

Status key:

- `GREEN`: requirement has direct automated evidence in current repo.
- `AMBER`: partial evidence exists, but requirement is only partly implemented/verified.
- `RED`: no credible automated evidence in current repo yet.

Test type legend:

- `U`: unit
- `I`: integration
- `E2E`: end-to-end
- `R`: regression

## A) Master Spec Requirements (`docs/ArqonBus/spec/00_master_spec.md`)

| Req ID | Requirement (short) | Current Evidence | Coverage (U/I/E2E/R) | Status | Gap / Next Action | Target Phase |
| --- | --- | --- | --- | --- | --- | --- |
| FR-CORE-01 | Secure WebSocket + TCP connectivity | `tests/integration/test_epoch1_gate.py`, `tests/integration/test_e2e_messaging.py` | Y/Y/Y/N | AMBER | Add explicit TCP listener contract tests and WSS acceptance tests. | B |
| FR-CORE-02 | TLS 1.3 for non-local traffic | No direct TLS test evidence found. | N/N/N/N | RED | Add TLS termination tests (handshake/protocol/cipher policy) and config enforcement tests. | B |
| FR-CORE-03 | Backpressure / slow-consumer handling | `tests/integration/test_telemetry.py` (telemetry backpressure), `tests/performance/test_load_testing.py` | N/Y/N/N | AMBER | Add core bus slow-consumer backpressure tests (not telemetry-only). | E |
| FR-MSG-01 | Protobuf on control and data plane | Protobuf assets exist (`crates/proto/src/envelope.proto`), but Python runtime path is JSON-heavy (`src/arqonbus/transport/websocket_bus.py`). | N/N/N/N | RED | Implement protobuf-first infra path and add cross-language contract tests. | C |
| FR-MSG-02 | Canonical envelope fields | `src/arqonbus/protocol/envelope.py`, `tests/regression/test_envelope_timestamp_z_regression.py` | Y/N/N/Y | AMBER | Align full envelope contract to spec fields and add schema conformance tests. | C |
| FR-MSG-03 | Differential messaging / delta-only topics | No direct feature or tests found. | N/N/N/N | RED | Define delta semantics + add unit/integration/e2e/regression tests. | C |
| FR-OPS-01 | Wasm operator hosting with memory/CPU caps | Shield policy engine fuel tracking exists (`crates/shield/src/policy/engine.rs`), no full operator-host tests. | Y/N/N/N | AMBER | Implement/validate caps in operator runtime; add adversarial cap-exhaustion tests. | D |
| FR-OPS-02 | Native proxy sidecar support | No first-party sidecar contract tests found. | N/N/N/N | RED | Define sidecar protocol and add integration/e2e tests. | D |
| FR-OPS-03 | SAM handshake with capability/input/output schema | `tests/test_operator_sam.py`, `tests/test_dispatch_e2e.py`, `src/arqonbus/protocol/operator.py` | Y/N/Y/N | AMBER | Add explicit handshake schema validation and regression tests for capability contracts. | D |
| FR-TIME-01 | Monotonic sequence per reality | No monotonic sequence tests found. | N/N/N/N | RED | Add sequence generator + deterministic ordering tests. | C |
| FR-TIME-02 | Vector clocks for causal ordering | No vector-clock tests found. | N/N/N/N | RED | Add vector-clock model + causal merge tests + e2e partition scenarios. | C |
| FR-TIME-03 | `history.get` strict time-bounded replay API | History tests exist (`tests/integration/test_redis_storage.py`, `tests/integration/test_e2e_messaging.py`), but strict time-bounded replay contract is not fully covered. | N/Y/N/N | AMBER | Implement `history.get` contract and add e2e + regression replay tests. | C |
| FR-SAFE-01 | CASIL inspects every edge message | CASIL coverage exists in Python path: `tests/integration/casil/test_*`, `tests/unit/casil/test_*`. | Y/Y/Y/Y | AMBER | Enforce equivalent coverage on Rust Shield edge path. | B |
| FR-SAFE-02 | Policy fail-closed on error/timeout | Enforce mode tests exist (`tests/integration/test_epoch1_gate.py`, `tests/integration/casil/test_hot_reload_e2e.py`) but strict fail-closed guarantees across edge paths remain partial. | Y/Y/Y/Y | AMBER | Add explicit fail-closed timeout/crash tests in Shield runtime. | B |
| FR-SAFE-03 | Immutable governance audit log | No immutable-audit specific tests found. | N/N/N/N | RED | Define immutable audit sink and governance event verification tests. | E |
| FR-EMERG-01 | Spectral metadata as first-class headers | No spectral metadata tests found. | N/N/N/N | RED | Add envelope/header fields and full lifecycle tests. | D |
| FR-EMERG-02 | Authorized control parameter broadcast | No direct control-parameter broadcast tests found. | N/N/N/N | RED | Add command/control path with auth gating and replay-safe semantics. | D |
| NFR-PERF-01 | p99 latency target | Performance suites exist (`tests/performance/test_casil_benchmarks.py`, `tests/performance/test_load_testing.py`), no enforced p99 release gate yet. | N/Y/N/N | AMBER | Add CI benchmark thresholds and baseline drift policy. | E |
| NFR-PERF-02 | Throughput target | Load tests exist, no hard throughput gate in CI. | N/Y/N/N | AMBER | Add reproducible throughput harness + release gate. | E |
| NFR-PERF-03 | Connection density target | No automated high-density gate proving target in CI. | N/N/N/N | RED | Add large-scale connection density test harness and publish baselines. | E |
| NFR-REL-01 | Deterministic replay | No deterministic replay verification found. | N/N/N/N | RED | Add replay determinism tests with fixture logs. | C |
| NFR-REL-02 | Tenant bulkhead/isolation | `tests/regression/test_operator_store_tenant_isolation.py`, `tests/test_dispatch_integration.py` | Y/Y/N/Y | AMBER | Add adversarial noisy-tenant isolation tests under load. | E |
| NFR-SEC-01 | Zero trust between components | JWT/auth tests exist (`tests/unit/test_jwt_auth.py`, `tests/integration/test_epoch1_gate.py`), but full component mutual-auth not covered. | Y/Y/Y/N | AMBER | Add service-to-service auth contract tests for gateway/engine/store. | B |
| NFR-SEC-02 | Encryption at rest/in transit | No direct encryption-at-rest/transport policy tests found. | N/N/N/N | RED | Add storage encryption + transport TLS enforcement tests. | E |

## B) Core Spine Requirements (`docs/ArqonBus/spec/01_core_spine.md`)

| Req ID | Requirement (short) | Current Evidence | Coverage (U/I/E2E/R) | Status | Gap / Next Action | Target Phase |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Voltron layering (Shield -> Spine -> Brain) | Architectural docs exist; no end-to-end layering conformance suite found. | N/N/N/N | RED | Add architecture conformance checks and integration tests across layers. | B |
| FR-002 | Shield Rust edge + JWT validation | Rust JWT unit tests exist (`crates/shield/src/auth/jwt.rs`), Python edge integration tests exist (`tests/integration/test_epoch1_gate.py`). | Y/Y/Y/N | AMBER | Complete Shield edge wiring and add Shield integration/e2e suites. | B |
| FR-003 | NATS routing by tenant/room subject | NATS bridge exists (`crates/shield/src/router/nats_bridge.rs`), no complete routing integration tests found in Rust. | N/N/N/N | RED | Add NATS tenant-subject routing integration tests. | B |
| FR-004 | Presence state via Brain layer | Python room/channel state tests exist; Elixir Presence CRDT coverage not present in this repo. | Y/Y/N/N | AMBER | Define cross-repo Brain contract and integration checks. | D |
| FR-005 | Protobuf protocol usage | Protobuf schema exists, runtime path not protobuf-first. | N/N/N/N | RED | Execute protocol migration and add compatibility tests. | C |
| FR-006 | Wasm middleware chains | Wasm policy plumbing exists (`crates/shield/src/policy/*`), middleware payload path is placeholder in `crates/shield/src/middleware/wasm.rs`. | Y/N/N/N | AMBER | Implement request payload extraction and chain behavior tests. | B |
| FR-007 | Twist/time headers in envelope | Partial timestamp coverage (`tests/regression/test_envelope_timestamp_z_regression.py`), no twist/header conformance tests. | Y/N/N/Y | AMBER | Add header-level protocol tests and enforce in validator. | C |
| FR-008 | Tenant isolation at publish/subscribe | Store isolation regression exists (`tests/regression/test_operator_store_tenant_isolation.py`), not yet proven on NATS pub/sub path. | Y/Y/N/Y | AMBER | Add NATS path isolation tests and adversarial cross-tenant attempts. | B |

## C) Mandatory Test Buildout (Hard Gate)

Every new capability or high-risk refactor in Phases B-E must ship with all suites:

- Unit tests
- Integration tests
- End-to-end tests
- Regression tests

No merge to `main` for vNext innovation work if any suite category is missing for affected code paths.

