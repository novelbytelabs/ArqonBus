# Implementation Plan: CASIL (Content-Aware Safety & Inspection Layer)

**Branch**: `002-content-aware-safety-inspection` | **Date**: 2025-12-01 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-content-aware-safety-inspection/spec.md`

## Summary

Introduce an optional, bounded CASIL layer that sits between message validation and routing/commands/history. CASIL is fully config-driven, runs only for in-scope rooms/channels, performs deterministic classification within `max_inspect_bytes`, evaluates safety/hygiene policies (size limits, probable secret detection, field/path and pattern redaction), produces a single outcome (`ALLOW`, `ALLOW_WITH_REDACTION`, `BLOCK`), and emits redaction-safe telemetry/logs. When disabled or out-of-scope, CASIL must impose negligible overhead and leave message semantics untouched.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: stdlib (`re`, `json`, `dataclasses/typing`), existing ArqonBus modules; avoid new heavy deps (no AI/ML, no external network I/O on hot path)  
**Storage**: Existing in-memory and Redis Streams history; CASIL must never persist blocked messages  
**Testing**: pytest (unit for classifier/policies/redaction, integration for monitor vs enforce, adversarial payloads/oversize/probable secrets)  
**Target Platform**: Existing ArqonBus server runtime (Linux, WebSocket server)  
**Project Type**: Single server application with layered architecture  
**Performance Goals**: Near-zero overhead when disabled; <5ms p99 inspection overhead in monitor mode at default limits; bounded by `max_inspect_bytes` and pattern counts  
**Constraints**: No blocking I/O in CASIL hot path; deterministic classification; safe redaction; optional metadata exposure; single configuration precedence (env → config file → defaults)  
**Scale/Scope**: Applied selectively to scoped rooms/channels; must scale with existing bus throughput targets

## Constitution Check

✅ Layered design: CASIL added as its own package and invoked after validation, before routing/commands/history; no coupling to application logic.  
✅ Config over code: All behavior via `casil.*` config (enable, mode, scope, limits, redaction/policies, default_decision, metadata exposure).  
✅ Minimal dependencies: Stdlib + existing stack; no heavy/AI/remote calls in hot path.  
✅ Public protocol discipline: Optional CASIL metadata added without changing existing envelope semantics; clients can ignore it.  
✅ Reliability/observability: Fail-safe via `default_decision`; telemetry/logging redaction-safe and cannot crash the bus.

## Project Structure

### Documentation (this feature)

```text
specs/002-content-aware-safety-inspection/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (protocol/error code additions)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/arqonbus/
├── casil/
│   ├── __init__.py
│   ├── config.py            # Config model, validation, defaults, precedence hooks
│   ├── scope.py             # Room/channel scoping and pattern matching
│   ├── classifier.py        # Deterministic classification (kind, risk_level, flags)
│   ├── policies.py          # Policy definitions (size, probable secret, rule evaluation)
│   ├── redaction.py         # Field/path and pattern-based redaction helpers
│   ├── outcome.py           # Outcome model (allow/redact/block, reason codes, metadata)
│   ├── engine.py            # Orchestrates scope → classify → policy → redaction
│   ├── telemetry.py         # CASIL event/metric schemas + emitters (redaction-safe)
│   ├── errors.py            # CASIL-specific exceptions and reason codes
│   └── integration.py       # Integration glue to server/routing/history hooks
├── ... existing modules ...
└── tests/
    ├── unit/casil/          # Classifier, policies, redaction, config validation
    └── integration/casil/   # Monitor vs enforce behavior, pipeline effects, history
```

**Structure Decision**: Extend existing single-project layout with a dedicated `casil` package and targeted test suites; integrate via `integration.py` hooks into validation → CASIL → routing/commands/history.

## Architecture Overview

- **Config surface**: `casil.enabled`, `casil.mode` (`monitor`|`enforce`), `casil.scope.include/exclude`, `casil.limits.max_inspect_bytes`, `casil.limits.max_patterns`, policy toggles (`max_payload_bytes`, `block_on_probable_secret`, redaction paths/patterns), `casil.default_decision` (`allow`/`block`), metadata exposure controls (logs/telemetry/envelope). Single precedence: env → config file → defaults.
- **Invocation seam**: After envelope validation, before routing/commands/history. Out-of-scope traffic returns immediately with a no-op outcome to ensure near-zero overhead.
- **Classification**: Deterministic classifier bounded by `max_inspect_bytes`; sets `kind`, `risk_level`, `flags` (e.g., `contains_probable_secret`, `oversize_payload`, `from_untrusted_client` if context available). No external I/O.
- **Policy evaluation**: Rules for payload size, probable secret detection (bounded regex/pattern set), redaction rules (field paths, patterns), mode-aware outcomes (`monitor` → never block). Single outcome per message with reason code.
- **Redaction mechanics**: Apply to observability targets by default (logs/telemetry). Optional transport-level redaction must preserve well-formed payloads. Pattern and path operations must be bounded and deterministic.
- **Telemetry/logging**: Emit CASIL metrics/events with redaction applied; counts by room/channel/client, outcomes, classification summaries, internal errors using `default_decision`. Avoid payload logging unless masked.
- **History behavior**: Blocked messages are never persisted. Redaction of persisted messages only when explicitly configured and documented; CASIL metadata storage rules defined (likely optional metadata on persisted records or none for first iteration).
- **Failure modes**: Internal errors follow `casil.default_decision` and emit reasoned telemetry/logs without crashing the loop.

## Implementation Phases

1. **Config & Validation**
   - Implement `casil.config` with defaults, env/config-file precedence, validation (scope patterns, limits bounds, modes, default_decision).
   - Document required knobs and safe defaults; wire into existing config loader.

2. **Scope & Classification Primitives**
   - Build `scope` matcher (include/exclude, prefix/glob-like).
   - Implement `classifier` with bounded inspection respecting `max_inspect_bytes`; deterministically set `kind/risk_level/flags`.

3. **Policy Engine & Redaction**
   - Implement `policies` (size limit, probable secret detection with bounded regex set, redaction rules).
   - Build `redaction` helpers for field-path and pattern masking; ensure JSON remains well-formed; shared redaction targets (logs/telemetry, optional transport).
   - Define `outcome` model with reason codes and redacted snapshot for observability.

4. **CASIL Engine Orchestration**
   - Implement `engine` to orchestrate scope → classify → policy → redaction; honor `mode` (monitor/enforce) and `default_decision` on internal errors.
   - Add guardrails for near-zero overhead when disabled or out-of-scope.

5. **Pipeline Integration**
   - Add `integration` hook post-validation, pre-routing/commands/history. Ensure blocked messages are not delivered or persisted; allow/redact outcomes propagate to logging/telemetry and optional envelope metadata.
   - Ensure history writer respects CASIL decisions (no persist on block; redaction only if configured).

6. **Telemetry & Logging Schemas**
   - Define CASIL telemetry event schema (counts, outcomes, flags, reason codes) and metrics counters/gauges/histograms as appropriate.
   - Integrate with existing telemetry/logging emitters; enforce redaction on observability surfaces.

7. **Failure Modes & Backpressure Handling**
   - Implement `default_decision` paths with reason codes for internal errors; ensure telemetry/logging still emitted safely.
   - Handle telemetry backpressure (drop/limit non-critical events) without impacting message flow.

8. **Testing & Contract Coverage**
   - Unit: config validation, scope matcher, classifier determinism, policy evaluation, redaction correctness/well-formedness, probable secret detection bounds.
   - Integration: monitor vs enforce behavior, scoped vs out-of-scope traffic, oversize and secret cases, block semantics (no delivery/persistence), telemetry emission and redaction.
   - Adversarial: malformed payloads, extreme sizes near limits, regex backtracking avoidance, transport redaction preserving JSON.

9. **Docs & Runbook Updates**
   - Update architecture docs with CASIL layer and pipeline seam.
   - Add config reference (`casil.*`), protocol/error codes for CASIL blocks, telemetry schema, history behavior, and runbook incident steps (monitor → enforce).

## Risks / Complexity & Mitigations

- **Performance overhead**: Keep CASIL short-circuited when disabled/out-of-scope; bound inspection by `max_inspect_bytes` and pattern counts; avoid allocations and deep copies.  
- **Regex/path redaction pitfalls**: Use bounded, precompiled patterns; cap matches; ensure fallback to safe masking to avoid malformed JSON.  
- **Failure mode ambiguity**: Strict `default_decision` handling with explicit reason codes and telemetry to avoid silent pass/block.  
- **Telemetry backpressure**: Design emitters to drop/limit non-critical CASIL events when sinks are slow; never block main loop.  
- **Metadata exposure**: Default to observability-only metadata; make envelope exposure opt-in and documented to avoid client surprises.  
- **History interaction**: Explicitly gate CASIL metadata persistence; ensure blocked messages never reach history.

## Documentation Updates

- `docs/architecture.md`: Insert CASIL layer, pipeline position, and integration seam.  
- `docs/runbook.md` / ops guide: CASIL enable/disable, monitor → enforce switch, incident tightening, interpreting reason codes.  
- `docs/configuration.md` (or existing config ref): Document `casil.*` knobs, defaults, precedence.  
- `docs/protocol.md` / contracts: New CASIL error codes, optional envelope metadata fields, and behavior on `BLOCK`.  
- `docs/telemetry.md` or telemetry reference: CASIL metrics/events schema and redaction rules.  
- `specs/002-content-aware-safety-inspection/contracts/`: Add/update protocol contracts and error code references as needed.  
- `specs/002-content-aware-safety-inspection/quickstart.md`: Examples for monitor vs enforce configs and expected behaviors.***
