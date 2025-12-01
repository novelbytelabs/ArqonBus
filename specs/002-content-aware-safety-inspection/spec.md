# Feature Specification: Feature 002 – Content-Aware Safety & Inspection Layer (CASIL)

**Feature Branch**: `002-content-aware-safety-inspection`  
**Created**: 2026-02-06  
**Status**: Draft  
**Input**: `/speckit.specify` – add an optional, configuration-driven content-aware inspection and safety layer that stays within the message bus scope

## User Scenarios & Testing *(mandatory)*

### User Story 1 – Configurable Inspection for App Developers (Priority: P1)

Application developers can enable CASIL via configuration and receive predictable behavior without changing application code.

**Independent Test**: Start ArqonBus with CASIL enabled for selected rooms/channels; send valid messages through the bus; verify routing is unchanged when no policy triggers.

**Acceptance Scenarios**:
1. **Given** CASIL is enabled and scoped to `chat:*`, **When** a developer sends normal chat messages, **Then** messages deliver unchanged and classification metadata is attached only where configured.
2. **Given** CASIL is disabled, **When** the same messages are sent, **Then** the bus behaves exactly as Feature 001 without CASIL metadata or policy actions.
3. **Given** a developer toggles CASIL on in config, **When** the bus restarts, **Then** inspection activates without code changes or client updates.

### User Story 2 – Policy Enforcement & Redaction for Security-Conscious Integrators (Priority: P1)

Security-focused teams can define simple policies that block, redact, or allow messages based on deterministic rules.

**Independent Test**: Configure policies for size limits, secret-pattern blocking, and JSON field redaction; send messages that trigger each rule; validate responses, logs, and telemetry reflect the policy result without leaking sensitive data.

**Acceptance Scenarios**:
1. **Given** a policy that blocks messages containing probable API keys, **When** a client sends a payload with a key-shaped string, **Then** the message is rejected, the sender receives a structured error, and no sensitive payload is logged.
2. **Given** a policy that redacts `payload.credentials` for telemetry, **When** a JSON message includes that field, **Then** forwarded messages (if allowed) contain redacted content where configured, and telemetry/logs contain masked values.
3. **Given** a size threshold policy for `ai:*` channels, **When** a message exceeds the limit, **Then** the bus responds with an explicit “blocked by policy” error code and emits a policy-violation telemetry event.

### User Story 3 – Operator Visibility & Incident Control (Priority: P2)

Operators need structured visibility into classifications and policy outcomes, plus quick levers for incident response.

**Independent Test**: Enable telemetry export; generate traffic across rooms/channels with mixed classifications and policy hits; verify counters, per-channel breakdowns, and violation summaries are available without exposing payloads.

**Acceptance Scenarios**:
1. **Given** telemetry is enabled, **When** messages are classified as `control`, `chat`, and `data`, **Then** operators can view counts and trends per class and per room/channel via structured events.
2. **Given** repeated violations from a client, **When** thresholds are crossed, **Then** CASIL emits a “suspicious pattern” telemetry event with client and channel identifiers (no sensitive payloads) and optional policy escalation (e.g., temporary block) if configured.
3. **Given** an incident requiring stricter hygiene, **When** an operator tightens patterns/thresholds via config and reloads, **Then** the bus enforces new policies immediately and reports the resulting increase in redaction/block events.

### User Story 4 – Predictable Failure Modes (Priority: P2)

CASIL failures or misconfigurations must not crash the bus and must follow documented defaults (fail-open or fail-closed).

**Independent Test**: Inject malformed policies, force classifier errors, and simulate telemetry sinks being unavailable; verify the configured default behavior (allow or block) is applied, errors are logged, and CASIL can be disabled without affecting core routing.

**Acceptance Scenarios**:
1. **Given** a malformed regex in policy config, **When** CASIL loads, **Then** the bus logs the issue, applies the configured default (allow/block), and continues running.
2. **Given** telemetry export is unavailable, **When** policy events occur, **Then** CASIL buffers minimally or drops telemetry safely without blocking message flow or crashing the process.
3. **Given** CASIL is disabled at runtime, **When** messages flow, **Then** no classification or policy side effects occur and message behavior matches Feature 001.

---

## Functional Requirements *(mandatory)*

- **FR-201 Configurable Activation & Scope**: CASIL can be globally enabled/disabled via configuration and scoped to specific rooms/channels (explicit list or pattern). Defaults must be safe and predictable.
- **FR-202 Deterministic Classification**: Inspected messages receive optional metadata (`kind`, `risk_level`, `flags`) based on bounded, deterministic rules. Classification must be fast, optional, and safe to ignore by clients.
- **FR-203 Policy Evaluation Outcomes**: For each inspected message, policies produce exactly one outcome: allow, allow-with-redaction, or block. Outcomes are logged and emitted as telemetry with reason codes.
- **FR-204 Redaction/Masking**: Support redaction by JSON path and by generic patterns (e.g., obvious secrets). Redaction applies consistently to logs, telemetry, and optionally forwarded payloads when configured.
- **FR-205 Error Signaling**: Blocked messages return a defined error event/response with a reason code and minimal metadata so clients can handle gracefully. Behavior is documented and predictable.
- **FR-206 Telemetry Emission**: Emit structured events for classifications, policy actions, and suspicious patterns (e.g., repeated violations per client/room/channel). Telemetry must avoid leaking sensitive payloads.
- **FR-207 Configurable Thresholds**: Policies can enforce size limits, rate/abuse thresholds (lightweight), and channel-specific rules without introducing workflow or business logic.
- **FR-208 Logging Hygiene**: Logging obeys redaction settings; sensitive content is never logged at INFO+; DEBUG logs that might contain sensitive data are clearly gated by config.
- **FR-209 Reliability & Safety Defaults**: On CASIL internal errors or misconfig, apply a configurable default (fail-open or fail-closed), emit an explicit log/telemetry event, and avoid crashing the main bus loop.
- **FR-210 Compatibility & Envelope Integrity**: CASIL metadata is additive/optional and does not change existing envelope semantics. Disabling CASIL restores Feature 001 behavior within the same protocol version.
- **FR-211 Config Reference & Examples**: Document all CASIL configuration knobs with examples (e.g., “never log payloads for `secure-*`”, “block probable API keys”, “redact fields in telemetry”). Include performance considerations and safe defaults.

---

## Behavioral Rules & Scope

- **Inspection Boundaries**: CASIL operates at the transport/routing boundary; it does not reach into application/business logic or perform semantic/AI reasoning. No external network calls on the hot path.
- **Classification Taxonomy**: Default categories include `control`, `chat`, `data`, `telemetry`, `system`; risk levels include `low`, `medium`, `high`; flags may include `contains_probable_secret`, `contains_large_payload`, `from_untrusted_source`, `policy_violation`.
- **Policy Semantics**:
  - Allow: message passes unchanged; metadata may be attached if enabled.
  - Allow-with-redaction: message is forwarded with configured fields masked; logs/telemetry use redacted payloads.
  - Block: message is not forwarded; sender receives structured error; logs/telemetry record the policy and reason without sensitive content.
- **Redaction Scope**: Redaction can target JSON paths and regex/pattern matches. Redaction applies to outbound logs/telemetry and, when configured, to forwarded payloads on specific rooms/channels.
- **Telemetry Shape**: Events carry timestamp, message identifiers, room/channel, client id (if available), classification result, policy outcome, and reason codes. Payload content is excluded or redacted by default.
- **Observability Views**: Operators can aggregate counts per category, per room/channel, per client, plus violation trends and top offenders. Telemetry must be usable for dashboards without additional parsing.
- **Configuration Surfaces**: All behavior is driven by configuration (env/config file) with a documented precedence order. Changes apply on restart or live-reload if supported by the runtime.
- **Performance Constraints**: Classification/policy evaluation must be bounded and fast; no unbounded parsing; defaults should add minimal overhead when enabled and near-zero overhead when disabled.
- **Failure Modes**: CASIL must degrade gracefully. Telemetry sink failures or classifier errors cannot crash the bus. Default allow/block behavior must be explicit and testable.
- **Security & Privacy**: No secrets in logs; redaction precedes emission; policies cannot bypass existing auth/authz; CASIL is transport-level hygiene, not access control or business decisions.

---

## Success Criteria *(measurable where possible)*

- **SC-201**: CASIL-enabled routing adds negligible latency (target ≤ single-digit ms per message in local tests) and zero added overhead when disabled.
- **SC-202**: 100% of messages in scoped rooms/channels receive deterministic classification metadata without altering delivery semantics when policies allow.
- **SC-203**: 100% of policy hits produce the correct outcome (allow/redact/block) with matching logs/telemetry entries and redaction applied where configured.
- **SC-204**: Blocked messages always return a defined, documented error code and reason consumable by client SDKs.
- **SC-205**: Telemetry covers classifications, policy actions, and suspicious patterns with no sensitive payload leakage in INFO-level outputs.
- **SC-206**: CASIL can be toggled off to restore Feature 001 behavior with no protocol or routing regressions.
- **SC-207**: Misconfiguration or internal errors trigger the configured default (allow/block) and generate operator-visible diagnostics without crashing the bus.

---

## Constraints & Non-Goals

- CASIL is optional, transport-level, and configuration-driven. It must **not** become an AI engine, workflow/orchestration layer, or business-rule system.
- No GUI/dashboard changes are included; outputs are logs, telemetry, and optional envelope metadata.
- No dependence on external AI/LLM or third-party policy engines on the hot path.
- Policies remain simple and transparent; no complex DSL beyond documented knobs and patterns.
- CASIL must not change message semantics beyond optional metadata, redaction, and explicit blocking with errors.

---

## Clarifications & Decisions

### Error Model (Client-Facing)

- **Error codes/names**:
  - `CASIL_POLICY_BLOCKED`: message blocked by configured policy (e.g., secret pattern, oversize).
  - `CASIL_REDACTED`: redaction applied; not an error, but may appear in metadata/telemetry (no client error envelope).
  - `CASIL_INTERNAL_ALLOW`: internal CASIL error occurred; default-allow applied; surfaced via telemetry/logs, not as client error.
  - `CASIL_INTERNAL_BLOCK`: internal CASIL error occurred; default-block applied; client receives error envelope.
- **Error envelope fields to clients (for block cases)**:
  - `type: "error"` (consistent with Feature 001 error handling).
  - `error.code`: one of the codes above (only `CASIL_POLICY_BLOCKED` or `CASIL_INTERNAL_BLOCK` reach clients).
  - `error.reason`: short, non-sensitive reason code (e.g., `probable_secret`, `oversize_payload`, `policy_violation`).
  - `error.policy_id`: optional stable identifier for the policy that fired (if configured).
  - `error.correlation_id`: optional, matches server-side log/telemetry correlation.
  - `timestamp`.
- **Not exposed to clients**: raw payloads, matched regex patterns, redaction masks, internal stack traces, config details.
- **Redaction signaling to clients**: if allow-with-redaction, no error envelope; optional `metadata.casil` block may include `redaction_applied: true`, `redacted_fields` (names/paths only), `policy_id`.

### Telemetry Event Schema (No raw payloads)

- Common fields for all CASIL telemetry events:
  - `event_type` (see below), `timestamp`, `message_id`, `room`, `channel`, `client_id` (if available), `correlation_id` (if available), `node_id/instance_id`, `protocol_version`.
- **Classification events** (`event_type: casil.classification`):
  - `kind`, `risk_level`, `flags` (list).
  - `inspected: true/false` (e.g., out-of-scope or skipped due to size limit).
- **Policy actions** (`event_type: casil.policy_action`):
  - `policy_id`, `outcome: allow|redact|block`, `reason_code`, `matched_flags` (e.g., `contains_probable_secret`, `oversize_payload`).
  - `redaction_fields` (names/paths only) when outcome is `redact`.
  - `default_behavior` when triggered by fail-open/fail-closed due to internal error.
- **Suspicious patterns** (`event_type: casil.suspicious_pattern`):
  - `pattern_type` (e.g., `repeated_policy_violation`, `oversize_abuse`, `untrusted_source_spam`).
  - `subject` (client_id and/or room/channel), `count`, `window_seconds`.
  - `action_taken` (none|notify|temp_block|rate_limit) if configured at the CASIL level.
- **Payload handling**: No raw payloads or regex captures are emitted. Paths/field names may be emitted; values are redacted/masked.

### Configuration Behavior

- **Global enable/disable**: `casil.enabled` (default: `false`). When `false`, CASIL is bypassed entirely and Feature 001 behavior is unchanged.
- **Default allow/block on CASIL failure**: `casil.default_decision` with values `allow` or `block` (default: `allow` for availability; operators can harden to `block`).
- **Scopes**:
  - `casil.scope.include`: list of room:channel patterns (glob-style, `*` and `?`; evaluated against `room:channel` string). Default: `["*"]` when CASIL is enabled.
  - `casil.scope.exclude`: list of patterns to skip even if included. Default: `[]`.
  - Precedence: if a message matches any include and no exclude, CASIL inspects; otherwise, CASIL skips.
- **Live reload**: Not supported in v1 of CASIL. Changes require restart/reload of the process to avoid race conditions and to ensure deterministic policy application. Future support could add a guarded, atomic reload path.
- **Example config sketch** (format-agnostic):
  - `casil.enabled: true`
  - `casil.default_decision: allow`
  - `casil.scope.include: ["chat:*", "ai:*"]`
  - `casil.scope.exclude: ["public:general"]`
  - `casil.policies`: list with `policy_id`, `match` (patterns/size), `action` (allow|redact|block), `redact_fields`, `reason_code`.

### Performance Constraints

- **No network calls on hot path**: CASIL classification and policies must be pure, CPU-bound, deterministic, and bounded.
- **Default inspected payload size cap**: `casil.limits.max_inspect_bytes` default 64 KiB. Above this cap:
  - Mark `inspected: false`, add flag `payload_too_large`.
  - Apply `casil.limits.oversize_behavior` (default: `block`; options: `block`, `allow`, `allow_and_tag` (allow with `flags: [contains_large_payload]` and optional redaction of logs/telemetry)).
- **Pattern complexity**: Regex/patterns must be precompiled; count and complexity must be bounded to worst-case linear scans on the capped payload size. Prohibit catastrophic backtracking patterns.
- **Resource safeguards**: Limit number of active policies and regexes (plan to set practical defaults, e.g., ≤50 patterns per deployment; to be validated in plan). Telemetry emission must be non-blocking and shed load safely.

### Interaction with Feature 001 (Compatibility)

- **Envelope metadata**: CASIL adds an optional `metadata.casil` object (when `casil.expose_metadata_to_clients` is true). Fields: `classification` (`kind`, `risk_level`, `flags`), `policy_outcome`, `redaction_applied`, `redacted_fields`, `policy_id`, `reason_code`. Absent when CASIL is disabled or exposure is off.
- **Routing & delivery**: Classification metadata is additive; delivery semantics from Feature 001 stay unchanged unless a policy blocks the message or redacts it per configuration.
- **History/telemetry/logs**:
  - Blocked messages are neither delivered nor persisted.
  - Allow-with-redaction stores/forwards the redacted payload when the policy specifies forwarding redaction; otherwise, only logs/telemetry are redacted.
  - Allow (no redaction) stores/forwards the original payload as in Feature 001.
  - History retrieval returns whatever payload was persisted (redacted or original) and may include `metadata.casil` if stored with the message; defaults to including metadata unless disabled via configuration.
- **Commands**: Existing commands (e.g., `history`) operate normally. CASIL decisions affect payloads stored/replayed (redacted vs original) but do not change command protocol shapes. Errors from blocked messages use the error model above.

### Remaining Ambiguities (to finalize in /speckit.plan)

- Correlation ID source and format (reuse existing request/message IDs vs. generate CASIL-specific IDs).
- Exact defaults for limits such as maximum number of patterns/policies before startup warning/refusal.
- Whether to support an `allow_and_tag` oversize behavior by default or keep oversize as block-only.
- Whether `metadata.casil` should be persisted by default in history or be opt-in to minimize storage overhead (current lean: include by default; confirm in plan).
