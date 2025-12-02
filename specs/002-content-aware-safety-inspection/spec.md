# Feature Specification: CASIL (Content-Aware Safety & Inspection Layer)

**Feature Branch**: `002-content-aware-safety-inspection`  
**Created**: 2025-12-01  
**Status**: Draft  
**Input**: Add an optional, bounded Content-Aware Safety & Inspection Layer (CASIL) to ArqonBus that can inspect envelopes/payloads, apply configurable safety and hygiene policies (classify, redact, block), emit structured telemetry, and remain bypassable with negligible overhead when disabled.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scoped Activation with Monitor/Enforce Modes (Priority: P1)

Developers and operators can enable CASIL globally but only inspect specified rooms/channels, with a mode switch between monitor-only and enforcing behavior.

**Why this priority**: Without scoped activation and clear modes, CASIL cannot be safely rolled out or limited to sensitive traffic; this is foundational for adoption.

**Independent Test**: Start the bus with CASIL enabled in monitor mode and scope `secure-*`; verify messages in `secure-payments` emit classification telemetry without blocking, while messages in `public-chat` bypass CASIL entirely. Switch to enforce mode and confirm scoped messages now evaluate policies.

**Acceptance Scenarios**:

1. **Given** CASIL is enabled with scope `["secure-*"]` and mode `monitor`, **When** a message is sent to `secure-billing:updates`, **Then** CASIL runs classification/telemetry but delivers the message unchanged.  
2. **Given** CASIL is enabled with scope `["secure-*"]` and mode `enforce`, **When** a message is sent to `public-lobby:chat`, **Then** CASIL is bypassed and the message is delivered without CASIL metadata or overhead.  
3. **Given** CASIL is disabled via configuration, **When** any message is sent, **Then** no CASIL logic executes and runtime overhead is negligible.

---

### User Story 2 - Hygiene Policies for Secrets and Oversize Payloads (Priority: P1)

Security-conscious integrators can configure CASIL to detect probable secrets and enforce payload size limits, choosing between allow, redact, or block outcomes.

**Why this priority**: Protecting against obvious leaks and runaway payloads is the primary safety value CASIL provides; it must be deterministic and bounded.

**Independent Test**: Configure `block_on_probable_secret=true` and `max_payload_bytes=262144` for `secure-*`. Send a message with a token-looking string and another exceeding the size limit; verify CASIL blocks both with reason codes while allowing normal-sized, non-secret messages.

**Acceptance Scenarios**:

1. **Given** CASIL enforce mode with secret detection enabled, **When** a message payload includes an API-key-shaped string within `secure-vault:ops`, **Then** CASIL returns `BLOCK` with reason `CASIL_POLICY_BLOCKED_SECRET` and the sender receives a structured error.  
2. **Given** CASIL enforce mode with `max_payload_bytes=262144`, **When** a `secure-vault:ops` message exceeds that size, **Then** CASIL blocks the message, emits telemetry with `oversize_payload` flag, and prevents persistence/delivery.  
3. **Given** CASIL monitor mode with the same policies, **When** the above messages are sent, **Then** CASIL emits telemetry with classification/flags but delivers the messages unchanged.

---

### User Story 3 - Safe Logging and Telemetry Redaction (Priority: P2)

Developers can ensure payloads on sensitive channels never appear unredacted in logs or telemetry while still receiving delivery.

**Why this priority**: Preventing leakage of secrets/PII into observability sinks is a key hygiene requirement and must work independently of blocking.

**Independent Test**: Configure `never_log_payload_for=["pii-*"]` with redaction patterns. Send payloads containing passwords/tokens to `pii-payroll:updates`; verify logs/telemetry show metadata and redacted tokens while delivered messages remain intact (unless transport redaction is explicitly enabled).

**Acceptance Scenarios**:

1. **Given** CASIL redaction enabled for `pii-*` logs/telemetry, **When** a message to `pii-payroll:updates` includes `password` and `token` fields, **Then** logs/telemetry mask those fields with `***REDACTED***` and do not store raw payloads.  
2. **Given** transport-level redaction is disabled, **When** the same message is delivered, **Then** the client receives the original payload while logs/telemetry remain redacted.  
3. **Given** transport-level redaction is enabled for a channel, **When** a message triggers redaction, **Then** the forwarded payload stays well-formed JSON and matches the configured masking.

---

### User Story 4 - Operator Insight and Incident Controls (Priority: P2)

Operators can observe CASIL activity and tighten/relax policies during incidents without application code changes.

**Why this priority**: CASIL must provide actionable observability and safe levers to respond to leaks or abuse.

**Independent Test**: Enable CASIL telemetry emission and switch from monitor to enforce during a simulated incident; verify metrics/logs show inspected counts, allow/redact/block tallies, and reason codes by room/channel/client.

**Acceptance Scenarios**:

1. **Given** CASIL telemetry is configured, **When** messages are inspected, **Then** metrics/logs report counts of inspected vs allowed/redacted/blocked by room/channel/client and include classification summaries (`kind`, `risk_level`, flags).  
2. **Given** an incident runbook step toggles CASIL to enforce with stricter policies, **When** config is reloaded/applied, **Then** CASIL behavior changes accordingly, logging the change and applying new outcomes without code modifications.  
3. **Given** telemetry sinks are under backpressure, **When** CASIL emits events, **Then** the bus continues operating, possibly dropping non-critical telemetry but not crashing or blocking message flow.

### Edge Cases

- What happens when CASIL configuration is invalid at startup or reload (e.g., bad patterns, out-of-range limits)?  
- How does CASIL behave when `max_inspect_bytes` is lower than the payload size (partial inspection)?  
- What is returned when CASIL encounters an internal error during inspection (default allow vs block)?  
- How are messages handled when redaction patterns would produce malformed JSON (ensure safe output or fallback)?  
- How is telemetry/logging handled when sinks are unavailable or slow (backpressure strategy)?  
- What occurs when a message is out of scope (no CASIL inspection) but telemetry is globally enabled?  
- How do repeated violations from the same client/room influence logging/telemetry (rate-limiting or aggregation)?  
- How is history/Redis persistence handled for blocked messages (ensure they are never persisted)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: CASIL MUST be globally toggleable via configuration flag (e.g., `casil.enabled`) and default to disabled with negligible overhead.  
- **FR-002**: CASIL MUST support scoped inspection by room/channel names and simple patterns (prefix or glob-like) with bypass for out-of-scope traffic.  
- **FR-003**: CASIL MUST provide operational modes: `monitor` (never block) and `enforce` (apply allow/redact/block).  
- **FR-004**: CASIL MUST generate deterministic classification per inspected message with fields `kind`, `risk_level`, and `flags`, bounded by `casil.limits.max_inspect_bytes` and without unbounded parsing or external I/O.  
- **FR-005**: CASIL MUST expose configuration to optionally attach classification metadata to logs/telemetry and, when enabled, to outgoing envelopes in a backwards-compatible, optional structure.  
- **FR-006**: CASIL MUST support policy rules for payload size limits, probable-secret detection, field-path redaction, and pattern-based masking, all configured without code changes.  
- **FR-007**: CASIL MUST yield exactly one outcome per inspected message: `ALLOW`, `ALLOW_WITH_REDACTION`, or `BLOCK`, and apply redaction consistently to the configured targets (logs/telemetry and optionally forwarded payloads).  
- **FR-008**: CASIL MUST provide a configurable `casil.default_decision` controlling fail-open vs fail-closed behavior on internal errors or invalid per-message configuration, and emit reasoned telemetry/logs when invoked.  
- **FR-009**: CASIL MUST block delivery/persistence on `BLOCK` and return a structured client error with machine-readable reason code (e.g., `CASIL_POLICY_BLOCKED_SECRET`, `CASIL_POLICY_OVERSIZE`) and a safe human-readable message.  
- **FR-010**: CASIL MUST ensure redaction never produces malformed data for clients; when transport redaction is disabled, delivery payload remains unmodified while observability targets stay redacted.  
- **FR-011**: CASIL telemetry MUST emit counts for inspected messages, classification summaries, policy outcomes (allow/redact/block), internal errors, and repeated violations by room/channel/client, obeying the same redaction rules as logs.  
- **FR-012**: CASIL logging MUST record configuration load/validation results, scope changes, mode switches, and policy outcomes at appropriate log levels without leaking sensitive payloads.  
- **FR-013**: CASIL MUST validate configuration at startup (and reload, if supported), failing fast on critical errors or entering a safe default mode with warnings when partial configs are applied.  
- **FR-014**: CASIL MUST honor a single precedence order for configuration sources (env → config file → defaults) and document all `casil.*` knobs (enable, mode, scope, limits, default_decision, redaction policies).  
- **FR-015**: CASIL MUST maintain bounded performance impact: near-zero when disabled, and predictable limits when enabled (documented defaults and recommended upper bounds for inspection size and pattern counts).  
- **FR-016**: CASIL MUST integrate with existing history behavior so that blocked messages are never persisted; redaction of persisted messages must be explicit and documented if enabled.

### Key Entities

- **CASIL Configuration**: Structured settings controlling enablement, scope, mode, limits, default decision, redaction/policy definitions, and exposure of metadata.  
- **Classification Metadata**: Deterministic, bounded summary per inspected message (`kind`, `risk_level`, `flags`) optionally attached to telemetry/logs/envelopes.  
- **Policy Outcome**: Enum capturing CASIL decision (`ALLOW`, `ALLOW_WITH_REDACTION`, `BLOCK`) plus reason codes and optional redacted payload snapshot for observability.  
- **Telemetry Event**: Structured, redaction-safe observability record capturing counts, outcomes, reason codes, and offending room/channel/client identifiers without leaking payload content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With CASIL disabled, message throughput and latency remain within ±1% of baseline (no measurable overhead).  
- **SC-002**: With CASIL enabled in monitor mode and `max_inspect_bytes` at default, p99 inspection overhead adds <5ms per inspected message.  
- **SC-003**: 100% of in-scope messages receive deterministic classification (`kind`, `risk_level`, flags) that is reproducible given identical inputs/config.  
- **SC-004**: 100% of blocked messages return structured client errors with correct reason codes and are not delivered or persisted.  
- **SC-005**: Redaction policies prevent any payload field named in configuration from appearing unmasked in logs/telemetry across all tested channels.  
- **SC-006**: Telemetry emits counts of inspect/allow/redact/block per room/channel/client with <1% discrepancy when cross-checked against message flow in integration tests.  
- **SC-007**: Configuration validation fails fast on invalid scopes/policies in automated tests, with documented default_decision applied on runtime CASIL errors.  
- **SC-008**: Enabling transport-level redaction (when configured) preserves well-formed payloads in 100% of contract tests covering JSON inputs with nested fields and pattern matches.  
- **SC-009**: Incident drill can switch CASIL from monitor to enforce and tighten policies via configuration reload/restart in <2 minutes without code changes, verified in runbook tests.  
- **SC-010**: Default limits and recommended upper bounds are documented and enforce bounded inspection (no unbounded parsing or I/O) in load tests.
