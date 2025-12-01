# Implementation Plan: Feature 002 – Content-Aware Safety & Inspection Layer (CASIL)

**Branch**: `002-content-aware-safety-inspection` | **Date**: 2026-02-06 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification and clarifications from `/specs/002-content-aware-safety-inspection/spec.md`

## Summary

Implement CASIL as an optional, bounded, content-aware inspection layer inside ArqonBus. CASIL inspects envelopes/payloads, classifies messages, applies simple policies (allow, allow-with-redaction, block), emits structured telemetry, and integrates with logging without changing Feature 001 semantics when disabled. It is configuration-driven, restart-only for v1, with strict performance limits (64 KiB inspect cap, no hot-path network I/O), and additive metadata that clients may ignore.

## Technical Context

- **Language/Runtime**: Python 3.11+ (same as Feature 001)  
- **Existing stack**: websockets transport, Redis Streams optional storage, structured logging utils, config loader, telemetry emitter.  
- **New scope**: CASIL package with classifier, policy evaluation, redaction, config validation, telemetry adapter.  
- **Constraints**: No hot-path network calls; bounded regex/pattern evaluation; restart-only config reload; additive envelope metadata; default availability bias (`default_decision: allow`) but configurable to block.

## Constitution Check (CASIL-specific gates)

✅ **Layered design**: CASIL sits between validation and routing/storage; no leakage into business logic.  
✅ **Config over code**: All CASIL behavior via config (enable flag, scopes, policies, limits).  
✅ **Bounded cost**: Inspect cap, precompiled patterns, no external I/O.  
✅ **Optionality**: Disabled → Feature 001 behavior unchanged.  
✅ **No semantics change**: Envelope additions are optional metadata; blocking is explicit with documented errors.  
✅ **Security/log hygiene**: Redaction before logs/telemetry; no secrets at INFO+.  
✅ **Failure modes**: Configurable default-allow/block; internal errors do not crash bus.  

## Architecture Placement & Boundaries

- **Hot path hook**: After envelope validation, before routing/storage. CASIL receives the parsed envelope/payload, applies scope checks, runs classification, policy evaluation, and redaction decisions, then returns an outcome to the routing layer.  
- **Flow**: validate envelope → CASIL (if enabled + in-scope) → outcome:  
  - `allow`: pass through unchanged (optionally add metadata).  
  - `allow_with_redaction`: apply redaction to payload/logs/telemetry as configured; attach metadata.  
  - `block`: short-circuit; emit error envelope to sender; do not route or persist.  
- **Boundaries**: CASIL does not call external services, does not alter commands or routing semantics, and exposes client-facing effects only via metadata and error envelopes per spec.  

### Module/Package Layout

```
src/arqonbus/casil/
├── __init__.py
├── config.py          # load/validate CASIL config objects
├── classifier.py      # deterministic classification logic
├── policies.py        # policy evaluation engine (allow/redact/block)
├── redaction.py       # redaction utilities (JSON paths, patterns)
├── results.py         # dataclasses for classification & policy outcomes
├── telemetry.py       # CASIL telemetry adapter (emits to existing telemetry layer)
├── pipeline.py        # main entrypoint: inspect_message(message_ctx, casil_config)
└── limits.py          # limit enforcement (size caps, pattern guards)
```

Integration points (existing code):
- `transport/websocket_bus.py` or routing entry: call CASIL pipeline after envelope validation, before fan-out/persistence.
- `storage/*`: respect CASIL outcome for persistence (blocked not stored; redacted stored if configured).
- `telemetry/emitter.py`: accept CASIL telemetry events via adapter.
- `utils/logging.py`: provide structured logging hook for CASIL decisions (with redaction).

## Data Structures & Interfaces

- **ClassificationResult**: `kind`, `risk_level`, `flags`, `inspected: bool`.  
- **PolicyOutcome**: `outcome: allow|redact|block`, `reason_code`, `policy_id`, `redacted_fields`, `default_behavior` (on internal fail), `flags`.  
- **RedactionSpec**: list of JSON paths, pattern IDs; optional mask string.  
- **MessageContext**: envelope, payload (bounded to max_inspect_bytes view), room, channel, client_id, message_id, correlation_id, config snapshot.  
- **CASILResult** (returned to pipeline caller): classification, policy_outcome, redacted_payload (if applied), metadata_for_envelope (optional), error_payload (if blocked), telemetry_events (to emit asynchronously).

Interfaces:
- `inspect_message(ctx: MessageContext, config: CASILConfig) -> CASILResult` (pure, no I/O aside from telemetry/logging hooks that must be non-blocking).  
- Telemetry adapter consumes CASILResult and pushes events to existing telemetry emitter (async-safe, drop-on-backpressure).  
- Config loader returns validated `CASILConfig` with precompiled patterns and limits enforced at startup.

## Configuration Model

- **Global**: `casil.enabled` (bool, default false); `casil.default_decision` (`allow` default, or `block`).  
- **Scope**: `casil.scope.include` [glob patterns], `casil.scope.exclude` [glob patterns]; match on `room:channel`. If include matches and exclude does not, inspect; else skip. Default include `["*"]` when enabled.  
- **Limits**:  
  - `casil.limits.max_inspect_bytes` (default 64 KiB).  
  - `casil.limits.oversize_behavior` (`block` default; options: `block`, `allow`, `allow_and_tag`).  
  - `casil.limits.max_policies` and `max_patterns` (default targets: 50 each; warn/abort on exceed).  
  - Pattern safety checks (no catastrophic regex).  
- **Policies** (list): each `policy_id`, `match` (room/channel pattern, size thresholds, pattern flags like `contains_probable_secret`), `action: allow|redact|block`, `reason_code`, optional `redact_fields` (JSON paths), optional `redact_patterns`, optional `expose_metadata` override.  
- **Metadata exposure**: `casil.expose_metadata_to_clients` (default true).  
- **History metadata**: `casil.persist_metadata_in_history` (lean: true by default; confirm in implementation).  
- **Config loading**: Use existing config system; CASIL config parsed/validated at startup. Invalid config → fail fast with clear logs; malformed regex → follow spec (log + default_decision path) only if non-fatal, else abort startup per severity policy.  
- **Reload**: Restart-only for v1; no live reload to avoid race conditions.

## Error Handling & Client Contract

- CASIL maps `block` outcome to Feature 001 error envelope with `error.code` (`CASIL_POLICY_BLOCKED` or `CASIL_INTERNAL_BLOCK`), `reason`, optional `policy_id`, optional `correlation_id`, timestamp.  
- `allow_with_redaction` attaches `metadata.casil` when exposure enabled; no error envelope.  
- `allow` may attach `metadata.casil` if exposure enabled.  
- Correlation IDs: reuse message ID when available; generate CASIL-specific correlation if absent; propagate into telemetry/logging and error envelope.  
- Internal errors:  
  - If config `default_decision=allow` → emit telemetry (`CASIL_INTERNAL_ALLOW`), continue.  
  - If `default_decision=block` → block with `CASIL_INTERNAL_BLOCK` error envelope.  
  - All internal errors are logged (redacted) and surfaced via telemetry with `default_behavior`.

## Telemetry & Logging Integration

- CASIL telemetry adapter emits events: `casil.classification`, `casil.policy_action`, `casil.suspicious_pattern` with schema from spec.  
- Emission is async/non-blocking; on backpressure/unavailable sinks, drop or buffer minimally with warnings—never block hot path.  
- Logging: use existing structured logger with redaction applied before INFO+; DEBUG may contain more detail but must still respect redaction rules.  
- Operators consume via existing telemetry stream; plan will add runbook pointers (dashboard sections) but no new UI.  

## Performance & Limits

- Apply `max_inspect_bytes` early (slice payload view); set `inspected=false` and flag oversize when exceeded; follow `oversize_behavior`. Default: `block`.  
- Precompile patterns at startup; reject unsafe regex; bound counts (max_policies/patterns).  
- No hot-path network or file I/O.  
- Consider micro-benchmarks for worst-case pattern sets and 64 KiB payloads; add targeted perf tests in CI if feasible.  

## History & Commands Interaction

- Blocked messages: not routed, not persisted.  
- Allow-with-redaction: persisted payload is redacted if policy requires forwarding redaction; else only logs/telemetry redacted.  
- Allow: persisted as-is.  
- `metadata.casil` persisted with messages when `casil.persist_metadata_in_history` is true (default lean yes); optional flag to disable.  
- `history` command returns stored payload and stored metadata. No protocol shape changes. CASIL disabled → Feature 001 behavior unchanged.  

## Testing Strategy

- **Unit** (tests/unit/casil/): classifier rules, pattern matching, redaction functions, policy engine outcomes, limit enforcement.  
- **Integration** (tests/integration/casil/): end-to-end message path with CASIL enabled/disabled; scope include/exclude; allow/redact/block behaviors; oversize handling; metadata exposure; history persistence with redaction.  
- **Failure modes**: malformed policy config, regex errors, telemetry sink unavailable (ensure drop/not crash), internal exceptions with default_decision allow/block.  
- **Contract/compat**: error envelope structure with CASIL codes; optional metadata presence/absence when exposure toggled.  
- **Performance guards**: targeted tests for max_inspect_bytes behavior and pattern count limits.  

## Risks, Trade-offs, Open Decisions

- **Open**: finalize correlation ID format (reuse message id vs new UUID).  
- **Open**: confirm defaults for `max_policies`/`max_patterns` thresholds and whether to warn vs abort on exceed.  
- **Open**: whether `allow_and_tag` oversize behavior is enabled by default or kept as opt-in (current default: block).  
- **Open**: persist `metadata.casil` default (lean: true).  
- **Risk**: over-aggressive policies could block legitimate traffic; mitigated via config examples, safe defaults, telemetry visibility, and restart-only changes.  
- **Risk**: regex backtracking; mitigated via validation and cap on patterns.  
- **Risk**: telemetry sink backpressure; mitigated via non-blocking emission and drop policy with warnings.  

## Implementation Order (High-Level)

1. Add CASIL package scaffolding (config, results, limits, redaction, classifier, policies, telemetry adapter, pipeline).  
2. Implement config parsing/validation with limits, pattern precompilation, and restart-only enforcement.  
3. Implement classifier and policy engine with outcomes and redaction utilities.  
4. Wire CASIL pipeline into message processing path (post-validation, pre-routing/persistence) and handle error envelope generation.  
5. Integrate redacted persistence and metadata handling with history; add config flags for metadata exposure/persistence.  
6. Integrate telemetry/logging adapters with non-blocking emission and redaction.  
7. Add tests (unit, integration, failure/perf guards) covering user stories and clarifications.  
8. Update docs/runbook references (config examples, operator guidance) after tests validate behavior.  
