# ArqonBus vNext Innovation Execution Plan

Last updated: 2026-02-20  
Branch: `dev/vnext-innovation-execution`  
Status: Executing (through Continuum projector operational hardening)

## 1) Objective

Deliver the full vNext ambition in a phased, test-gated way:

- Close the gap between vNext vision/spec and running behavior.
- Preserve stability while increasing capability.
- Keep packaging/PyPI/release work out-of-scope until engineering gates are green.

## 2) Non-Negotiable Constraints

- JSON is only for human-facing surfaces (CLI/debug/UI/HTTP views).
- Protobuf is mandatory for infrastructure and machine-to-machine paths.
- Rust 1.82 is the core runtime standard for performance-critical infrastructure.
- No untracked technical debt in hot paths (`TODO`/`FIXME` without debt ID and owner).
- Fail-closed behavior for safety-critical controls (auth/policy/schema/governance).

Reference docs:

- `docs/ArqonBus/spec/00_master_spec.md`
- `docs/ArqonBus/plan/00_master_plan.md`
- `docs/ArqonBus/vnext_status.md`
- `docs/ArqonBus/spec/tech_debt.md`
- `docs/ArqonBus/constitution/constitution_v2.md`

## 3) Current State Deep Dive (Fact-Based)

### 3.1 Delivery strengths already present

- Broad Python-side test taxonomy and CI lanes are in place:
  - `pytest.ini`
  - `.github/workflows/arqonbus-tests.yml`
- Epoch 2 operator pack and Tier-Omega command lane are implemented in Python:
  - `src/arqonbus/transport/websocket_bus.py`
  - `tests/unit/test_standard_operator_pack.py`
  - `tests/unit/test_tier_omega_lane.py`
  - `tests/integration/test_tier_omega_lane_e2e.py`

### 3.2 High-risk gaps blocking full vNext ambition

- Shield compile/runtime correctness issues in startup wiring:
  - Duplicate fields and duplicate initialization in `crates/shield/src/main.rs`
- Edge auth path currently allows anonymous fallback in invalid/missing JWT cases:
  - `crates/shield/src/handlers/socket.rs`
- Wasm middleware body inspection is placeholder-only:
  - `crates/shield/src/middleware/wasm.rs`
- Policy engine currently validates with empty pointer/len payload path:
  - `crates/shield/src/policy/engine.rs`
- Schema validation can be silently disabled if descriptor file missing:
  - `crates/shield/src/middleware/schema.rs`
- Protobuf validation in registry is still stub-level:
  - `crates/shield/src/registry/validator.rs`
- Python WebSocketBus has grown to a monolithic hot path (1809 LOC):
  - `src/arqonbus/transport/websocket_bus.py`

### 3.3 Environment limitation discovered during assessment

- Rust compile verification could not be completed in this sandbox due offline crate resolution (`crates.io` not reachable), so compile health must be the first execution gate in a network-enabled environment.

## 4) Promise vs Delivered Matrix

| Capability | Promise Source | Current State | Gap Class |
| --- | --- | --- | --- |
| Edge fail-closed auth/policy/schema | `docs/ArqonBus/spec/00_master_spec.md` | Partial and inconsistent in Shield | Critical |
| Protobuf-first infra path | `docs/ArqonBus/spec/00_master_spec.md` | Mixed JSON-first operational core in Python | High |
| Rust Shield correctness as production edge | `docs/ArqonBus/plan/00_master_plan.md` | Scaffold exists, correctness unresolved | Critical |
| SAM/operator runtime standardization | `docs/ArqonBus/spec/00_master_spec.md` | Partial (Python path), contract not fully formalized end-to-end | High |
| TTC/timekeeper/vector clock semantics | `docs/ArqonBus/spec/00_master_spec.md` | Largely planned, not fully implemented | High |
| Observability/governance/audit depth | `docs/ArqonBus/spec/00_master_spec.md` | Medium maturity in Python, thin in Rust Shield | Medium |
| Performance targets (<5ms p99, high TPS) | `docs/ArqonBus/spec/00_master_spec.md` | Not yet proven by reproducible benchmark gates | High |

## 5) Execution Phases (Comprehensive)

### Phase A: Truth Alignment and Hard Gate

Goal: establish one executable truth before adding capabilities.

Implementation:

- Freeze roadmap claims and map each claim to test evidence.
- Add a requirement-to-test index document.
- Define mandatory “no merge” gates for critical paths.
- Phase A artifacts created:
  - `docs/ArqonBus/plan/phase_a_requirement_test_traceability.md`
  - `docs/ArqonBus/checklist/phase_a_truth_alignment_checklist.md`

Primary files:

- `docs/ArqonBus/vnext_status.md`
- `docs/ArqonBus/plan/00_master_plan.md`
- `docs/ArqonBus/spec/00_master_spec.md`
- `docs/ArqonBus/checklist/engineering_checklist.md`

Exit criteria:

- Every critical claim maps to at least one automated test.
- Contradictions between status/spec/plan resolved.

Test gate:

- Documentation lint + CI policy checks.

### Phase B: Shield Correctness and Safety Closure

Goal: make Rust Shield production-correct before expanding feature scope.

Implementation:

- Fix compile-time struct/init defects in `crates/shield/src/main.rs`.
- Enforce strict JWT behavior (reject missing/invalid tokens by default).
- Replace placeholder wasm middleware payload path with real body handling.
- Make schema descriptor enforcement explicit and fail-closed in strict mode.
- Replace stub protobuf validator with descriptor-based validation path.

Primary files:

- `crates/shield/src/main.rs`
- `crates/shield/src/handlers/socket.rs`
- `crates/shield/src/middleware/wasm.rs`
- `crates/shield/src/middleware/schema.rs`
- `crates/shield/src/registry/validator.rs`
- `crates/shield/src/policy/engine.rs`

Exit criteria:

- `cargo check -p shield` and `cargo test -p shield` pass.
- Missing/invalid auth and policy failures are fail-closed.
- Schema and policy behavior are deterministic and tested.

Test gate:

- Rust unit + integration + adversarial policy tests.

### Phase C: Protocol and Time Semantics Closure

Goal: enforce protobuf-first infra contract and start TTC semantics as real behavior.

Implementation:

- Align Python envelope and Rust protobuf envelope contract.
- Add sequence/time metadata contract and vector-clock extension points.
- Define replay/history APIs around strict causal semantics.
- Keep JSON views as adapters only.

Primary files:

- `crates/proto/src/envelope.proto`
- `crates/proto/build.rs`
- `src/arqonbus/protocol/envelope.py`
- `src/arqonbus/protocol/validator.py`
- `docs/ArqonBus/spec/api.md`

Exit criteria:

- Cross-language envelope contract tests green.
- Protobuf path is default for infra flows.
- JSON interfaces documented as human-facing adapters.

Test gate:

- Contract tests, regression tests for timestamp/sequence handling, compatibility fixtures.

### Phase D: Operator Runtime and Modularization Upgrade

Goal: reduce monolith risk and formalize SAM/operator lifecycle.

Implementation:

- Decompose `src/arqonbus/transport/websocket_bus.py` into modules:
  - operator_webhook service
  - operator_cron service
  - operator_store service
  - omega_lane service
  - handshake/auth and envelope processing service
- Keep transport shell thin and orchestration-only.
- Formalize SAM capability registration and handshake validation.

Primary files:

- `src/arqonbus/transport/websocket_bus.py`
- `src/arqonbus/routing/router.py`
- `src/arqonbus/protocol/operator.py`
- `tests/unit/test_standard_operator_pack.py`
- `tests/unit/test_tier_omega_lane.py`
- `tests/integration/test_tier_omega_lane_e2e.py`

Exit criteria:

- Hot-path file size and complexity reduced materially.
- Module-level ownership and tests for each operator path.
- Behavior parity preserved via regression tests.

Test gate:

- Unit + integration + e2e + regression on refactor branch before merge.

### Phase E: Performance, Governance, and Operational Hardening

Goal: validate “vNext” claims with objective performance and safety evidence.

Implementation:

- Add repeatable benchmark gates (latency, throughput, backpressure).
- Add debt budget tracking and CI rejection for untracked debt.
- Harden audit trail for governance/control commands.
- Add failure-injection/adversarial tests for safety boundaries.

Primary files:

- `tests/performance/test_load_testing.py`
- `tests/performance/test_casil_benchmarks.py`
- `docs/ArqonBus/checklist/sentinel_rules.yml`
- `docs/ArqonBus/checklist/runbook.md`
- `.github/workflows/arqonbus-tests.yml`

Exit criteria:

- Published benchmark baselines and drift thresholds.
- Adversarial suite stable.
- Governance actions traceable in logs/telemetry.

Test gate:

- Performance, adversarial, and regression suites all green.

### Phase F: Packaging/Release Readiness (Deferred by request)

Goal: only after A-E are green, execute PyPI/release flow with confidence.

Implementation:

- Package metadata, signing, SBOM/provenance, release automation.
- Operator docs for deployment and upgrade compatibility.

Primary files:

- `pyproject.toml`
- `.github/workflows/*publish*.yml`
- `docs/ArqonBus/checklist/runbook.md`

Exit criteria:

- Reproducible build artifacts and tagged release.
- PyPI publish pipeline validated.

### Phase G: Continuum/Reflex Integration Track (Active)

Goal: formalize and implement cross-product boundaries and event contracts without violating local hot-path ownership.

Implementation:

- Finalize and enforce the Continuum <-> Bus contract:
  - Topic contract: `continuum.episode.v1`
  - Projection contract: Bus -> Postgres
  - Coordination contract: tenant-scoped Valkey keys only for shared hot state
- Add integration adapters:
  - Continuum event producer contract tests/fixtures
  - Bus-side projector skeleton and idempotency guards (`event_id`, upsert key)
  - Replay/backfill controls with DLQ (`continuum.episode.dlq.v1`)
- Add Reflex integration boundary tests:
  - Reflex hot-path remains local (`RAM/Sled`)
  - Bus interaction is async publish/subscribe and cache-coordination only

Primary files:

- `docs/ArqonBus/spec/continuum_integration_contract.md`
- `docs/ArqonBus/spec/00_master_spec.md`
- `src/arqonbus/storage/postgres.py`
- `src/arqonbus/storage/redis_streams.py`
- `src/arqonbus/config/config.py`
- `tests/unit/test_continuum_integration_contract.py`
- `tests/integration/` (new projector/replay integration suites)

Exit criteria:

- Continuum/Reflex/Bus ownership boundaries codified and referenced from status + runbook.
- Idempotent projection path implemented with stale-update guard.
- Replay/backfill and DLQ paths are tested with failure injection.
- Tenant-scoping for Valkey keys and Postgres row namespaces is enforced by tests.

Test gate:

- Contract + integration + regression suites for:
  - event schema validation
  - projector idempotency
  - stale event rejection
  - replay/backfill correctness
  - tenant-isolation key/row checks
- Operational gate additions:
  - Postgres-backed socket command-lane e2e projector test
  - CI Postgres integration stage without mocks
  - Migration + backup/restore runbook and validation path

## 6) Test Strategy and Quality Gates

Required suites per phase:

- Unit: fast module correctness checks.
- Integration: storage/network/component interaction.
- End-to-end: realistic WebSocket + command + operator flows.
- Regression: previously fixed defects remain fixed.
- Adversarial: malformed payloads, auth abuse, policy bypass attempts.
- Performance: latency/throughput/backpressure budgets.

Existing baseline references:

- `pytest.ini`
- `.github/workflows/arqonbus-tests.yml`
- `tests/regression/`
- `tests/performance/`

Additions required:

- Rust Shield integration and adversarial suites.
- Cross-language protobuf contract tests.
- Refactor parity tests for modularized transport modules.

## 7) Gotchas and Risk Register

- Network-isolated CI/dev shells can hide Rust compile/runtime drift if crates are missing; always run connected compile gate before milestone signoff.
- `websocket_bus.py` is business-critical and monolithic; refactors here can silently break command paths without broad e2e coverage.
- Mixed JSON/protobuf behavior creates migration hazards; dual-mode periods need explicit compatibility tests and clear deprecation windows.
- Fail-open defaults in edge security paths can create production exposure if not explicitly locked down per environment.
- Status docs can overstate maturity if not tightly tied to automated evidence.

## 8) Execution Order (Recommended)

1. Phase A (truth alignment and gating).
2. Phase B (Shield correctness and fail-closed safety).
3. Phase C (protocol/time semantics closure).
4. Phase D (modularization and operator runtime formalization).
5. Phase E (performance/governance hardening).
6. Phase G (Continuum/Reflex integration track).
7. Phase F (packaging/PyPI/releases).

## 9) Definition of Done for “Full vNext Ambition”

- Shield edge path is compile-clean, fail-closed, and tested.
- Protobuf-first infra contract is enforced across core paths.
- Time semantics and replay contract are implemented and tested.
- Operator/Tier-Omega runtime is modular, maintainable, and covered.
- Performance and safety claims are backed by repeatable CI evidence.
- Documentation, runbook, and status files reflect tested reality.
