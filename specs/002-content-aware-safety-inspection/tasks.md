---
description: "Task list for Feature 002 – Content-Aware Safety & Inspection Layer (CASIL)"
---

# Tasks: Feature 002 – Content-Aware Safety & Inspection Layer (CASIL)

**Input**: `/specs/002-content-aware-safety-inspection/spec.md` and `/specs/002-content-aware-safety-inspection/plan.md`  
**Prerequisites**: Feature 001 core bus foundation operational (transport, routing, commands, storage, telemetry)  
**Defaults (from clarifications)**: `max_inspect_bytes=64KiB`, `oversize_behavior=block`, `persist_metadata_in_history=true`, `max_policies/max_patterns≈50` (fail-fast/warn as specified), `default_decision=allow` unless hardened  

## Format
- `[ID] [P] Area Description (paths)`  
- `[P]` means parallelizable if dependencies satisfied  
- Include dependencies where ordering matters

## Area 1: CASIL Core Package Scaffolding

- [ ] T201 [P] Create CASIL package structure with placeholders (src/arqonbus/casil/__init__.py, config.py, classifier.py, policies.py, redaction.py, results.py, telemetry.py, pipeline.py, limits.py)
- [ ] T202 [P] Implement CASIL data classes/results (ClassificationResult, PolicyOutcome, RedactionSpec, MessageContext, CASILResult) in src/arqonbus/casil/results.py
- [ ] T203 [P] Implement limits enforcement utilities (max_inspect_bytes=64KiB, oversize_behavior=block default, pattern count guards ~50, regex safety checks) in src/arqonbus/casil/limits.py
- [ ] T204 [P] Implement redaction utilities (JSON path and pattern masking, no payload logging) in src/arqonbus/casil/redaction.py
- [ ] T205 [P] Implement deterministic classifier (kind/risk/flags) in src/arqonbus/casil/classifier.py using bounded, deterministic rules only (no I/O)
- [ ] T206 [P] Implement policy engine (allow/allow_with_redaction/block with reason_code, policy_id, redacted_fields) in src/arqonbus/casil/policies.py; enforce single outcome; integrate limits/flags
- [ ] T207 [P] Implement CASIL telemetry adapter (non-blocking emit of casil.classification, casil.policy_action, casil.suspicious_pattern) in src/arqonbus/casil/telemetry.py; drop-on-backpressure with warnings
- [ ] T208 [P] Implement CASIL pipeline entrypoint (inspect_message) in src/arqonbus/casil/pipeline.py orchestrating scope check, limits, classifier, policy engine, redaction, telemetry events assembly

## Area 2: Configuration Loading & Validation

- [ ] T209 Validate/load CASIL config (casil.enabled, default_decision, scope include/exclude globs, limits, policies, metadata exposure, history persistence) in src/arqonbus/casil/config.py; precompile patterns; fail fast on invalid regex/policy counts
- [ ] T210 Integrate CASIL config into main config loader (src/arqonbus/config.py) and ensure restart-only behavior (no live reload)
- [ ] T211 Add safe defaults and precedence (env/config/defaults) with examples in config tests

## Area 3: Integration into Message Pipeline

- [ ] T212 Wire CASIL pipeline into message processing (post-envelope-validation, pre-routing/persistence) in src/arqonbus/transport/websocket_bus.py (or routing entry) without creating god modules
- [ ] T213 Map CASIL block outcomes to Feature 001 error envelopes (error.code CASIL_POLICY_BLOCKED/CASIL_INTERNAL_BLOCK, reason, policy_id?, correlation_id?, timestamp) in pipeline integration code
- [ ] T214 Attach metadata.casil for allow/allow_with_redaction when casil.expose_metadata_to_clients is true; ensure absence when disabled

## Area 4: History & Commands Integration

- [ ] T215 Apply CASIL outcomes to persistence: blocked → not stored; allow_with_redaction → store redacted payload when policy says; allow → store original in storage backends (src/arqonbus/storage/*, router integrations)
- [ ] T216 Ensure history retrieval returns stored payload plus metadata.casil when casil.persist_metadata_in_history is true (default) in history handling (commands/history path)
- [ ] T217 Confirm Feature 001 behavior unchanged when CASIL disabled (bypass CASIL path cleanly)

## Area 5: Telemetry & Logging Integration

- [ ] T218 Hook CASIL telemetry adapter to existing telemetry emitter (src/arqonbus/telemetry/emitter.py) ensuring non-blocking/drop-on-backpressure semantics
- [ ] T219 Add structured logging for CASIL decisions with redaction applied before INFO+ (src/arqonbus/utils/logging.py or CASIL wrappers)
- [ ] T220 Emit telemetry for internal errors with default_behavior (CASIL_INTERNAL_ALLOW/BLOCK) and suspicious patterns

## Area 6: Testing

- [ ] T221 [P] Unit tests for classifier, redaction, limits, policy engine (tests/unit/casil/)
- [ ] T222 [P] Integration tests for CASIL in message path (enable/disable, scope include/exclude, allow/redact/block, oversize_behavior=block default) in tests/integration/casil/
- [ ] T223 [P] Tests for history persistence behavior (redacted vs original, metadata.casil persistence flag) in tests/integration/casil_history.py
- [ ] T224 [P] Failure-mode tests: malformed policies/regex, telemetry sink unavailable (drop/not crash), internal errors with default_decision allow vs block in tests/unit|integration/casil_failures.py
- [ ] T225 [P] Contract tests for error envelopes and metadata.casil exposure toggles (tests/contract/casil_protocol.py)
- [ ] T226 [P] Perf guard tests for max_inspect_bytes cap and pattern count limits (bounded runtime) in tests/unit/casil_limits.py

## Area 7: Documentation

- [ ] T227 Update README.md with CASIL overview, enable flag, scope include/exclude, defaults (64KiB cap, oversize_behavior=block, default_decision=allow, persist_metadata_in_history=true)
- [ ] T228 Update architecture.md / docs/specs/constitution.md if needed to restate CASIL under Security & Safety and layering; ensure consistency with constitution note
- [ ] T229 Update runbook.md and developers_guide.md with config examples and operational guidance (error codes, telemetry events, restart-only changes)
- [ ] T230 Add CASIL config reference/examples (patterns, redaction fields, policy examples) in specs/002-content-aware-safety-inspection/quickstart or config section (format aligned with repo docs)

## Dependencies Overview

- Core scaffolding (T201–T208) precedes integration tasks (T212–T214).  
- Config loading (T209–T211) required before full pipeline wiring and tests.  
- Persistence/command integration (T215–T217) depends on pipeline wiring.  
- Telemetry/logging integration (T218–T220) depends on telemetry adapter (T207) and pipeline (T208/T212).  
- Tests (T221–T226) depend on corresponding implementation areas.  
- Documentation (T227–T230) comes after behavior is validated but can draft in parallel once interfaces are stable.  
