# Tasks: CASIL (Content-Aware Safety & Inspection Layer)

**Input**: Design documents from `/specs/002-content-aware-safety-inspection/`  
**Prerequisites**: plan.md (required), spec.md (required)

## Phase 1: Foundational (Shared Infrastructure)

- [X] T001 [P] Create `src/arqonbus/casil/` package with stubs for `config.py`, `scope.py`, `classifier.py`, `policies.py`, `redaction.py`, `outcome.py`, `engine.py`, `telemetry.py`, `errors.py`, `integration.py`, and `__init__.py`.
- [X] T002 Wire `src/arqonbus/config/config.py` to load `casil.*` settings (enabled, mode, scope include/exclude, limits, default_decision, redaction/policy knobs) with precedence env → config → defaults.
- [X] T003 Add CASIL reason codes and enums in `src/arqonbus/casil/errors.py` and `outcome.py` (ALLOW, ALLOW_WITH_REDACTION, BLOCK; reason constants like CASIL_POLICY_BLOCKED_SECRET, CASIL_POLICY_OVERSIZE, CASIL_INTERNAL_ERROR_*).

## Phase 2: User Story 1 - Scoped Activation with Monitor/Enforce Modes (Priority: P1) 🎯

**Goal**: CASIL can be enabled, scoped by room/channel patterns, and operate in monitor vs enforce modes with near-zero overhead when disabled/out-of-scope.

**Independent Test**: Messages in scoped rooms trigger CASIL classification/telemetry; out-of-scope bypasses CASIL; mode switch from monitor to enforce changes outcomes without code changes.

### Tests
- [X] T010 [P] Add scope matcher unit tests in `tests/unit/casil/test_scope.py` for include/exclude patterns and bypass cases.
- [X] T011 Integration test in `tests/integration/casil/test_modes_and_scope.py` covering disabled, monitor, enforce, scoped vs out-of-scope traffic.

### Implementation
- [X] T020 Implement scope matcher in `src/arqonbus/casil/scope.py` (prefix/glob-like, include/exclude, fast bypass).
- [X] T021 Implement `src/arqonbus/casil/classifier.py` deterministic classification (kind/risk_level/flags) bounded by `max_inspect_bytes`, no external I/O.
- [X] T022 Build `src/arqonbus/casil/engine.py` orchestration: guard for disabled/out-of-scope, run classify→policy placeholder, respect `mode` (monitor never blocks), return outcome.
- [X] T023 Integrate CASIL hook in pipeline (post-validation, pre-routing) via `src/arqonbus/casil/integration.py` and call site in `src/arqonbus/server.py` (or routing entrypoint); ensure bypass cost is negligible.
- [X] T024 Ensure blocked outcome short-circuits delivery/persistence; allow outcomes proceed unchanged when CASIL disabled/out-of-scope.

## Phase 3: User Story 2 - Hygiene Policies for Secrets and Oversize Payloads (Priority: P1)

**Goal**: Enforce size limits and probable-secret detection with configurable allow/redact/block outcomes.

**Independent Test**: Oversize or secret-looking messages in scoped channels are blocked in enforce mode; only telemetry in monitor mode; normal traffic allowed.

### Tests
- [X] T030 [P] Unit tests in `tests/unit/casil/test_policies.py` for size limit and probable-secret detection (bounded regex set, `max_inspect_bytes` respected).
- [X] T031 Integration tests in `tests/integration/casil/test_hygiene_policies.py` for enforce vs monitor outcomes and reason codes (`CASIL_POLICY_OVERSIZE`, `CASIL_POLICY_BLOCKED_SECRET`).

### Implementation
- [X] T040 Implement policy evaluation in `src/arqonbus/casil/policies.py` (max payload bytes, probable secret patterns with bounds, rule composition).
- [X] T041 Extend `engine.py` to apply policies after classification, map to outcomes with reason codes, and honor `default_decision` on policy errors.
- [X] T042 Add structured client error mapping for `BLOCK` outcomes with CASIL reason codes (surface via protocol error path).

## Phase 4: User Story 3 - Safe Logging and Telemetry Redaction (Priority: P2)

**Goal**: Ensure sensitive payloads are redacted in logs/telemetry per config, with optional transport-level redaction that preserves well-formed JSON.

**Independent Test**: Configured fields/patterns are masked in logs/telemetry for sensitive channels; delivery payload remains intact unless transport redaction is enabled; redaction never produces malformed JSON.

### Tests
- [X] T050 [P] Unit tests in `tests/unit/casil/test_redaction.py` for field-path masking, pattern masking, JSON well-formedness, and max match bounds.
- [X] T051 Integration test in `tests/integration/casil/test_redaction_behavior.py` for log/telemetry redaction vs transport redaction toggles on sensitive channels.

### Implementation
- [X] T060 Implement redaction helpers in `src/arqonbus/casil/redaction.py` (field/path redaction, pattern-based masking, bounded operations).
- [X] T061 Wire redaction into `engine.py` outcomes: `ALLOW_WITH_REDACTION` for observability targets by default; optional transport-level redaction gated by config.
- [X] T062 Ensure telemetry/log emitters use redacted snapshots and never log raw payloads when redaction rules apply.

## Phase 5: User Story 4 - Operator Insight and Incident Controls (Priority: P2)

**Goal**: Provide telemetry/logging for CASIL activity and support incident-time tightening via config without code changes; ensure blocked messages never persist.

**Independent Test**: CASIL emits metrics/events (inspect/allow/redact/block counts, reason codes) by room/channel/client; switching monitor → enforce via config is reflected; blocked messages not delivered or persisted; backpressure handled safely.

### Tests
- [X] T070 [P] Unit tests in `tests/unit/casil/test_telemetry.py` for event schema construction and redaction safety.
- [X] T071 Integration tests in `tests/integration/casil/test_operator_controls.py` for telemetry counts, mode switch effects, and history behavior (blocked messages not stored).

### Implementation
- [X] T080 Implement telemetry schema and emitters in `src/arqonbus/casil/telemetry.py` with counters for inspected/allow/redact/block, classification summaries, internal errors; apply redaction.
- [X] T081 Integrate CASIL telemetry with existing telemetry/logging infrastructure (`src/arqonbus/telemetry/` and logging utils) ensuring non-blocking behavior under backpressure.
- [X] T082 Enforce history behavior in `src/arqonbus/storage/` integration: blocked messages never persisted; optional CASIL metadata persistence clearly gated by config.
- [X] T083 Add config-driven mode/scope reload handling (restart or config reload path) and log/telemetry change events when toggled for incident response.

## Phase 6: Failure Modes, Backpressure, and Defaults

- [X] T090 Implement `default_decision` handling in `engine.py` for internal errors and invalid per-message config, emitting `CASIL_INTERNAL_ERROR_*` telemetry/logs.
- [X] T091 Add safeguards against regex/path explosion (limits on patterns, match counts, and max_inspect_bytes enforcement) with documented fallbacks.
- [X] T092 Ensure CASIL hook cannot crash the bus loop; wrap integration call sites with safe error handling and metrics.
- [X] T093 Add performance regression tests/benchmarks comparing ArqonBus baseline with CASIL disabled vs CASIL enabled (monitor mode, default `max_inspect_bytes`); target ±1% throughput/latency when disabled and <5ms p99 added overhead when enabled. Document measured results in CASIL runbook/performance note.

## Phase 7: Documentation & Contracts

- [X] T100 Update `docs/architecture.md` with CASIL layer position and pipeline seam (validation → CASIL → routing/commands/history).
- [X] T101 Update config reference (e.g., `docs/configuration.md`) documenting `casil.*` knobs, defaults, precedence.
- [X] T102 Update protocol/contracts in `specs/002-content-aware-safety-inspection/contracts/` for CASIL error codes, optional envelope metadata exposure, and block response shape.
- [X] T103 Update telemetry reference (e.g., `docs/telemetry.md`) with CASIL metrics/events and redaction rules.
- [X] T104 Update runbook/ops docs (e.g., `docs/runbook.md`) with incident steps (monitor → enforce), tightening policies, interpreting reason codes.
- [X] T105 Add `specs/002-content-aware-safety-inspection/quickstart.md` examples for monitor vs enforce configs and expected behaviors.
- [X] T106 Document CASIL default values and recommended upper bounds (enabled=false, mode=monitor, default_decision=allow, default max_inspect_bytes, pattern limits) in configuration docs and runbook; align docs with validated tests/benchmarks.

## Dependencies & Execution Order

- Phase 1 foundational tasks precede all story work.  
- User Stories 1 and 2 (P1) depend on Phase 1; User Stories 3 and 4 (P2) depend on prior phases but can run in parallel after P1 foundations exist.  
- Phases 6–7 depend on core engine/integration completion; documentation updates follow finalized behaviors.
