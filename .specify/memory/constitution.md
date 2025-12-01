<!-- 
Sync Impact Report - ArqonBus Constitution v1.2.0
=================================================
Version change: 1.1.0 → 1.2.0
Modified principles: Product Identity, Vision and Scope, Architecture Principles, Protocol Guarantees, Code Quality, Development Process, Observability, Security, Governance
Added concepts: CASIL (Content-Aware Safety & Inspection Layer) as an optional inspection & safety layer within ArqonBus
Removed sections: None
Templates requiring updates: Specs and plans for features that introduce or extend CASIL behavior
Follow-up TODOs: Ensure Feature 002 spec and plan explicitly reference CASIL and align with this constitution
-->

# ArqonBus Constitution

This document defines the **non-negotiable principles** that govern how ArqonBus is designed, evolved, and maintained.  

It exists to protect ArqonBus from accidental bloat, silent breakage, and “clever” shortcuts that erode trust.

If a decision conflicts with this constitution, **the decision is wrong**.

---

## I. Product Identity

### 1. ArqonBus in One Sentence
> **ArqonBus is a small, sharp, reliable WebSocket message bus for structured, real-time communication, with an optional content-aware safety & inspection layer.**

It is **not** a framework, ESB, or application platform.  
It is **just powerful enough** to be an excellent transport layer, and no more.

ArqonBus may include an optional **Content-Aware Safety & Inspection Layer (CASIL)**:

- CASIL inspects structured messages in-flight in a lightweight, bounded way.
- CASIL applies **safety and hygiene policies** (classification, redaction, blocking) at the transport level.
- CASIL produces metadata and telemetry that help operators understand and control message flows.

CASIL is:

- about **content awareness**, not AI reasoning or agent orchestration;
- a **layer**, not a platform;
- **optional and configurable** – ArqonBus must function correctly with CASIL disabled.

### 2. Core Promise
ArqonBus promises to application developers:

- A **clear, documented protocol** they can depend on.
- A **predictable runtime** that behaves the same in dev, staging, and prod.
- **Minimal cognitive overhead**: a few well-designed concepts that compose cleanly.
- **No surprises**: breaking changes are intentional, versioned, and rare.
- When CASIL is enabled, **transparent and well-documented safety behavior** (what is inspected, what may be redacted or blocked, and how this is surfaced).

If we ever violate this promise, we have broken ArqonBus.

---

## II. Vision and Scope

### 1. Vision
Build a message bus that:

- Embeds easily into existing stacks.
- Plays nicely with modern infra (containers, Kubernetes, managed Redis, etc.).
- Can be operated by a small team without a dedicated SRE army.
- Is **good enough** to serve as the backbone for serious systems, including AI-native and multi-agent environments, **without forcing them into our worldview**.
- Offers **built-in, transport-level safety and insight** via CASIL so teams don’t have to bolt on ad-hoc filters and scrubbing layers around ArqonBus.

### 2. In Scope (v1.x and early v2.x)

ArqonBus **shall provide**:

- A **WebSocket server** for bi-directional, real-time messaging.
- First-class support for **rooms** and **channels** as routing primitives.
- A **structured JSON message envelope** and a **small set of built-in commands**.
- Optional **Redis Streams integration** for durable history and replay.
- Lightweight **telemetry**: health, metrics, and activity streams suitable for dashboards.
- **CASIL – Content-Aware Safety & Inspection Layer**, optionally enabled, that:
  - inspects messages in a bounded, configurable way;
  - applies basic classification and safety policies (redact / allow / block);
  - emits structured telemetry about classifications and policy events.
- Official **client SDKs**, starting with **JS/TS** and **Python**, that map directly onto the protocol without “magic” and behave predictably whether or not CASIL is enabled.

### 3. Out of Scope (Non-Goals)

ArqonBus core **must not** grow into:

- A full **multi-agent orchestration platform**.
- A **workflow engine**, job scheduler, or ETL system.
- A **UI framework** or dashboarding toolkit inside the core server.
- A **business logic layer** (no domain rules, no domain models).
- A hard dependency on any specific LLM / MCP / agent runtime.
- A **semantic understanding engine** or general AI reasoning system, even with CASIL enabled.

CASIL in particular:

- must not encode business-domain rules or workflows;
- must not make application-level authorization decisions beyond transport-level safety policies;
- must not be positioned or marketed as an “AI agent layer.”

Such capabilities may exist in **separate Arqon projects** that *use* ArqonBus (and CASIL) as transport and safety infrastructure, but may not live in the core.

This boundary is a **hard guardrail**, not a suggestion.

---

## III. Architecture Principles

### 1. Layered Design (No Bleeding Between Layers)

ArqonBus must remain **strictly layered**:

1. **Transport Layer**  
   - Handles WebSocket connections, handshakes, heartbeats, and disconnects.  
   - Knows nothing about domain semantics.

2. **Routing Layer**  
   - Knows about rooms, channels, broadcasts, and private messaging.  
   - Responsible for subscription management and message fan-out.

3. **Command Layer**  
   - Implements built-in commands (status, history, channel management, ping, etc.).  
   - Treats commands as part of a public, versioned protocol.

4. **Storage Layer**  
   - Provides in-memory history by default.  
   - Integrates with Redis Streams or other backends via explicit adapters.  
   - Must be swappable without rewriting routing or commands.

5. **Telemetry Layer**  
   - Emits activity, health, and performance signals.  
   - Must not be able to crash the core bus if misconfigured or offline.

6. **Inspection & Safety Layer (CASIL)**  
   - Optionally inspects structured messages at or near the routing/command boundary.  
   - Applies **content-aware safety & inspection policies**:
     - classification and tagging;
     - redaction/masking;
     - allow/block decisions according to configuration.  
   - Produces metadata and events consumed by Telemetry and logging.  
   - Must be:
     - **bypassable/disabled** without breaking the core bus;  
     - **bounded in cost** (no unbounded parsing, no blocking external calls on the hot path);  
     - **agnostic of business semantics** (only transport- and content-level safety, not domain workflows).

No layer may reach around another “because it’s convenient.”  
CASIL in particular must not:

- reach directly into application logic;
- bypass Transport, Routing, or Command contracts;
- change message semantics in undocumented ways.

### 2. Stateless Where Possible

- Per-process state must be **minimal, explicit, and observable**.
- Long-lived state belongs in Redis or another declared backing store.
- No hidden in-memory caches that cannot be rebuilt on restart.
- Horizontal scaling must be possible without re-architecting the system.
- CASIL-specific state (e.g. counters, rolling stats) must be:
  - clearly scoped and documented;  
  - safe to reconstruct on restart;  
  - exposed via telemetry when relevant.

### 3. Config Over Code

- All operational behavior (rooms, system channels, telemetry endpoints, retention windows, limits) comes from **configuration or environment**, not from “magic” strings embedded in code.
- CASIL behavior (enable/disable, inspected rooms/channels, policies, thresholds) must be:
  - driven by configuration;  
  - documented in the configuration reference and `runbook.md`;  
  - safe in its default state (no surprising blocking or leaking).
- There must be a single, documented precedence order for configuration (e.g. env → config file → defaults), and the code must follow it.

### 4. Minimal Dependencies, Maximum Clarity

- Prefer stdlib plus a **small number of battle-tested libraries**.
- No large frameworks unless they demonstrably reduce complexity and are justified in the spec.
- If a dependency materially affects startup, error handling, performance, or CASIL behavior, it must be clearly documented and tested.
- CASIL must not introduce:
  - heavyweight AI/ML dependencies in the core;  
  - opaque third-party policy engines that are hard to reason about;  
  - background components that violate our simplicity and observability principles.

---

## IV. Protocol & Compatibility Guarantees

### 1. Envelope as Public Contract

The message envelope schema is a **public API**. For each protocol version:

- Required fields, optional fields, and types are clearly defined.
- Invalid messages are rejected with explicit errors.
- Version mismatches are handled predictably (graceful errors, not silent drops).

When CASIL is enabled, it may attach **additional, optional metadata** to messages (e.g., classification tags, risk flags, policy result codes). These must:

- be clearly documented as optional fields or substructures;
- never change the meaning of existing fields;
- be safe to ignore for clients that do not understand them.

### 2. Semantic Versioning for Protocol

- `MAJOR` – breaking changes to envelope, commands, or core behavior.
- `MINOR` – new commands, additive fields, new telemetry, non-breaking logic.
- `PATCH` – bug fixes, performance improvements, and clarifications.

No “stealth” breaking changes in `MINOR` or `PATCH`. Ever.

CASIL-related additions (e.g., new metadata fields, new error codes for blocked messages, new telemetry events) must follow the same rules:

- additive and optional in `MINOR`;
- removal or semantic change requires a `MAJOR` bump.

### 3. Backwards Compatibility Rules

- Once v1.0 is released, **existing fields cannot change meaning**.
- Removal of fields, commands, or behaviors requires:
  - Documentation of deprecation in at least one prior minor version.
  - Clear migration guidance.
  - Major version bump if fully removed.
- CASIL must be designed so that:
  - disabling CASIL restores behavior consistent with previous versions (within the same major version);
  - enabling CASIL does not silently change protocol contracts for existing clients beyond:
    - documented error conditions (e.g., “message blocked by policy”);
    - documented optional metadata fields.

---

## V. Code Quality & Testing (TDD is the Default)

### 1. TDD as Working Standard

For new features and changes to public behavior:

- Define behavior in the **spec**.
- Add or update tests to express that behavior clearly.
- Implement code to satisfy the tests.
- Refactor while keeping tests green.

Where strict TDD is impractical (e.g. small refactors), tests must still exist and be updated before merging.

CASIL-related functionality is **subject to the same standard**, with particular attention to:

- classification logic and policy decisions;
- failure modes (misconfig, unexpected payloads, abuse scenarios).

### 2. Coverage Expectations

- Routing core: high branch coverage, especially for edge cases (empty rooms, reconnection, flood scenarios).
- Command handlers: both unit tests (logic) and integration tests (end-to-end behavior with simulated clients).
- History / Redis Streams: deterministic tests that verify ordering, retention, and replay semantics.
- Envelope validation: tests for valid, invalid, and adversarial payloads.
- Telemetry: tests that assert structure and frequency, not exact values.
- **CASIL:** 
  - tests for classification outcomes given representative payloads and configurations;
  - tests for policy behavior (allow / redact / block) including:
    - size limits,
    - redaction rules,
    - pattern-based detection of obviously unsafe content;
  - tests that exercise CASIL’s behavior when disabled, misconfigured, or under high load.

### 3. Test Discipline

- Unit tests must run quickly and not depend on real external services.
- Integration tests must be clearly separated and runnable in CI with explicit setup.
- Flaky tests are considered bugs in the system (infra or code) and must be fixed, not ignored.
- CASIL must have tests that simulate hostile or malformed inputs and ensure:
  - the system remains stable;
  - behavior is deterministic and logged;
  - security posture (e.g., default-deny vs default-allow) follows configuration.

### 4. Quality Gates

A change may **not** be merged if:

- It alters public protocol behavior without accompanying tests.
- It introduces a new command or field without documentation.
- It reduces coverage in critical subsystems without justification.
- It violates the scope or architecture boundaries in this constitution.
- It introduces or modifies CASIL behavior without:
  - tests for policy outcomes and error conditions;
  - consideration of security implications in the spec/plan;
  - clear documentation of any new configuration or telemetry.

---

## VI. Development Process (Spec-Driven + Incremental)

### 1. Spec Kit as the Spine

For major features, protocol changes, or architectural moves:

- Use `/speckit.constitution` to keep this document current.
- Use `/speckit.specify` to define what and why (requirements, user stories, scenarios).
- Use `/speckit.clarify` to reduce ambiguity before planning.
- Use `/speckit.plan` to detail the implementation approach and stack.
- Use `/speckit.tasks` to break work into atomic, testable units.
- Use `/speckit.implement` to execute tasks in order.

For **CASIL-related features** (including new policies, new inspection modes, new metadata, or new telemetry):

- Specs must explicitly address:
  - security impact and threat considerations;
  - performance and latency implications;
  - failure modes and default behavior (e.g., default-allow vs default-deny on internal errors).
- Plans must describe:
  - how CASIL logic integrates with existing layers without violating layering rules;
  - how configuration is surfaced and validated;
  - how observability is provided (logs + telemetry).
- Tasks must ensure:
  - tests cover both “happy path” and adversarial scenarios;
  - documentation updates are included (config, runbook, developer guide).

### 2. Traceability

Every non-trivial change should be traceable to:

- A spec entry  
- A plan section  
- A task ID  
- One or more tests  

If you cannot explain “why does this code exist?” by pointing to a spec, **that code is suspect.**

For CASIL:

- Each policy, classification rule, or new configuration knob must have a clear lineage from spec → plan → tasks → tests → docs.

### 3. Small, Safe, Reversible Steps

- Avoid “big bang” rewrites.
- Prefer a series of well-scoped changes over a single gigantic PR.
- Maintain the ability to roll back or feature-gate risky behavior.
- CASIL additions should be:
  - guarded behind configuration flags or feature gates when in doubt;
  - able to be disabled cleanly if issues arise in production.

---

## VII. Coding Style & Implementation Conventions

This section defines how ArqonBus code should *feel* to read and work with.  
Anyone familiar with the codebase should be able to look at a new module and immediately recognize it as “ArqonBus code.”

These rules are about **clarity, stability, and maintainability** — not personal aesthetics.

CASIL code is held to the **same standards**, with additional care around clarity of policy decisions and security implications.

---

### 1. Design Philosophy

- **Boring is a feature.**  
  Code should be straightforward, unsurprising, and easy to explain. If a clever trick saves a few lines but would puzzle a new contributor, it is not welcome.

- **Readable first, fast second, clever last.**  
  Optimize only where necessary and only with measurement. Premature optimization that complicates logic is discouraged.

- **Small surface area, strong contracts.**  
  Prefer a small number of well-defined public interfaces over many loosely defined ones. Each public function or method must have a clear purpose.

- **Seams for evolution.**  
  The codebase should have obvious extension points (adapters, hooks, interfaces) for future work without needing deep surgery across unrelated modules.  
  CASIL-specific capabilities (classifiers, policies, telemetry hooks) should be implemented as well-defined seams rather than tightly coupled logic scattered across the codebase.

---

### 2. Module & Package Structure

ArqonBus Python code should follow these structural principles:

- **Packages reflect architecture, not org charts.**  
  Use package boundaries to mirror transport, routing, commands, storage, telemetry, CASIL, and utilities — not arbitrary groupings.

- **Single responsibility per module.**  
  A module should have one main idea:
  - e.g. `routing.py` for routing logic,  
  - `commands/status.py` for status command handling,  
  - `storage/redis_streams.py` for Redis Streams adapter,  
  - `casil/policies.py` for CASIL policy evaluation.

- **Avoid “god modules.”**  
  If a module needs to know about too many layers (e.g. transport + storage + telemetry + CASIL), it is doing too much and should be split.

- **Clear internal vs public APIs.**  
  - Public APIs are explicitly exported (e.g. via `__all__` or clear documentation).  
  - Helper functions internal to a module should be prefixed with `_` if they are not meant for external use.

---

### 3. Functions, Methods, and Public APIs

- **Function length and cohesion.**
  - Functions should fit on a screen without scrolling in a typical editor.  
  - If a function must be long, its structure must be obvious (e.g., clearly separated phases).

- **Naming.**
  - Names must describe *what* the thing does, not *how* it does it.  
  - Avoid abbreviations except for widely understood terms (e.g., `ws`, `id`, `jwt`).
  - CASIL-related names should make policy outcomes explicit, e.g. `evaluate_policy`, `apply_redaction`, `classify_message`.

- **Arguments and return types.**
  - Prefer explicit keyword arguments for booleans and configuration-like parameters.  
  - Return meaningful types (e.g. small dataclasses) instead of overloading tuples or dicts with implicit structure.
  - CASIL functions should return explicit result structures that indicate:
    - classification,
    - policy outcome (allow / redact / block),
    - any error or fallback mode.

- **No hidden global state.**
  - Avoid module-level mutable state that affects behavior.  
  - If state is needed, encapsulate it in a class or context object with clear lifecycle.
  - CASIL counters or rolling statistics must be clearly scoped and safe under concurrency.

---

### 4. Error Handling & Resilience

- **Fail loud on programmer errors.**
  - Cases that indicate a bug (e.g., impossible states, violated invariants) should raise clear exceptions and be logged as errors.

- **Fail soft on external errors.**
  - External issues (Redis offline, DNS failure, misconfig) should:
    - Log clearly with actionable messages.  
    - Trigger graceful fallback where possible.  
    - Avoid crashing the entire process unless continuing would be unsafe or misleading.

- **Guard internal invariants.**
  - Where critical assumptions are made (e.g. a message must have a `type`, a room must exist before broadcasting), assert or validate early.
  - CASIL invariants (e.g., “policy must choose exactly one of allow/redact/block”) should be enforced and tested.

- **No silent swallowing.**
  - `try/except: pass` is forbidden.  
  - Swallowing errors must be justified and logged, with a clear explanation of why ignoring is safe.
  - CASIL must not silently ignore policy evaluation failures; it must:
    - follow a documented default behavior (e.g., default-allow or default-deny configurable), and  
    - log the failure in a way that operators can see.

---

### 5. Concurrency, Async, and I/O

- **Async boundaries are explicit.**
  - I/O-facing functions (WebSocket reads/writes, Redis calls, disk access) must be clearly marked as `async` and isolated where possible.
  - Business logic should be largely synchronous and pure, called by thin async wrappers.

- **Avoid blocking the event loop.**
  - Heavy CPU-bound work must not run directly on the event loop.  
  - If unavoidable, it must be:
    - explicitly called out in the plan/spec, and  
    - offloaded to a thread pool or worker where appropriate.
  - CASIL classification and policy evaluation must be:
    - bounded in time and complexity;  
    - designed to avoid network calls or blocking operations on the hot path.

- **Ordering and consistency.**
  - If message ordering matters, the code must document and enforce the ordering guarantees (or lack thereof).  
  - Race conditions must be treated as bugs, not “edge cases we ignore.”

---

### 6. Logging, Debugging, and Diagnostics

- **Logs serve operators, not the code author’s curiosity.**
  - Log messages must be written from the perspective of someone debugging a system in production:
    - “What failed?”  
    - “For which client/room/channel?”  
    - “What do I do next?”

- **Log levels used consistently.**
  - `DEBUG`: noisy, development-level details, disabled in prod by default.  
  - `INFO`: lifecycle events, state transitions, high-level flow.  
  - `WARN`: recoverable issues worth noticing.  
  - `ERROR`: failures the system couldn’t complete correctly.  
  - `CRITICAL`: unrecoverable failure requiring human attention.

- **No secrets in logs.**
  - Access tokens, passwords, private keys, and sensitive payloads must never be logged at INFO+ levels.  
  - DEBUG logs that may contain sensitive data should be clearly marked and controlled via configuration.
  - CASIL redaction rules must apply consistently to logs and telemetry so that sensitive content is not accidentally exposed.

- **Correlation and context.**
  - Where possible, use correlation IDs or request IDs to tie related events together across logs.  
  - Include client id, room, channel, and command/event type in logs for message-related operations.
  - CASIL-related logs should include:
    - which policy fired,  
    - what the outcome was (allow/redact/block),  
    - high-level reason codes (not raw content).

---

### 7. Legacy Code, Refactors, and Technical Debt

- **Debt must be visible, not hidden.**
  - Known technical debt must be documented with:
    - what the issue is,  
    - why it exists,  
    - and what the intended fix path is.

- **Refactors must not change behavior silently.**
  - Significant refactors require:
    - stable test suites before and after, and  
    - explicit note in the plan/spec if behavior changes.

- **Incremental cleanups are welcome.**
  - Small improvements (naming, minor refactors, docstring updates) are acceptable as long as:
    - they do not blur the history of functional changes, and  
    - they do not bundle unrelated behavior changes.
  - CASIL-specific technical debt (e.g., temporary heuristics, naive classifiers) must be clearly marked as such, with a plan for hardening if relied on in production.

---

### 8. Examples of “ArqonBus-Style” vs “Not ArqonBus-Style”

**ArqonBus-Style:**

- A routing function that:
  - takes a clearly typed envelope,  
  - validates its fields,  
  - logs routing decisions at DEBUG,  
  - and returns an explicit result indicating which subscribers were notified.

- A Redis adapter that:
  - is the only place Redis is imported for history,  
  - clearly documents connection assumptions,  
  - and has tests for failure modes (timeout, connection refused, misconfig).

- A CASIL policy evaluator that:
  - receives a typed message representation and configuration,  
  - deterministically returns `allow`, `redact`, or `block` plus metadata,  
  - logs a concise summary of the decision without leaking sensitive payloads,  
  - is fully covered by tests for normal and adversarial inputs.

**Not ArqonBus-Style:**

- A module that:
  - opens WebSockets, talks directly to Redis, emits telemetry, and implements custom commands all in one file.

- A function that:
  - takes a dict, mutates it in-place, logs nothing, catches all exceptions, and returns `True` or `False` depending on “whether it kind of worked.”

- A CASIL implementation that:
  - performs network calls to external services on the hot path,  
  - swallows exceptions and silently allows messages,  
  - applies ad-hoc regexes inline without tests or documentation.

If new code starts to resemble the “Not ArqonBus-Style” patterns, it should be **rejected in review** or immediately refactored.

---

## IV. Protocol & Compatibility Guarantees

### 1. Envelope as Public Contract

The message envelope schema is a **public API**. For each protocol version:

- Required fields, optional fields, and types are clearly defined.
- Invalid messages are rejected with explicit errors.
- Version mismatches are handled predictably (graceful errors, not silent drops).

When CASIL is enabled, it may attach **additional, optional metadata** to messages (e.g., classification tags, risk flags, policy result codes). These must:

- be clearly documented as optional fields or substructures;
- never change the meaning of existing fields;
- be safe to ignore for clients that do not understand them.

### 2. Semantic Versioning for Protocol

- `MAJOR` – breaking changes to envelope, commands, or core behavior.
- `MINOR` – new commands, additive fields, new telemetry, non-breaking logic.
- `PATCH` – bug fixes, performance improvements, and clarifications.

No “stealth” breaking changes in `MINOR` or `PATCH`. Ever.

CASIL-related additions (e.g., new metadata fields, new error codes for blocked messages, new telemetry events) must follow the same rules:

- additive and optional in `MINOR`;
- removal or semantic change requires a `MAJOR` bump.

### 3. Backwards Compatibility Rules

- Once v1.0 is released, **existing fields cannot change meaning**.
- Removal of fields, commands, or behaviors requires:
  - Documentation of deprecation in at least one prior minor version.
  - Clear migration guidance.
  - Major version bump if fully removed.
- CASIL must be designed so that:
  - disabling CASIL restores behavior consistent with previous versions (within the same major version);
  - enabling CASIL does not silently change protocol contracts for existing clients beyond:
    - documented error conditions (e.g., “message blocked by policy”);
    - documented optional metadata fields.

---

## V. Code Quality & Testing (TDD is the Default)

### 1. TDD as Working Standard

For new features and changes to public behavior:

- Define behavior in the **spec**.
- Add or update tests to express that behavior clearly.
- Implement code to satisfy the tests.
- Refactor while keeping tests green.

Where strict TDD is impractical (e.g. small refactors), tests must still exist and be updated before merging.

CASIL-related functionality is **subject to the same standard**, with particular attention to:

- classification logic and policy decisions;
- failure modes (misconfig, unexpected payloads, abuse scenarios).

### 2. Coverage Expectations

- Routing core: high branch coverage, especially for edge cases (empty rooms, reconnection, flood scenarios).
- Command handlers: both unit tests (logic) and integration tests (end-to-end behavior with simulated clients).
- History / Redis Streams: deterministic tests that verify ordering, retention, and replay semantics.
- Envelope validation: tests for valid, invalid, and adversarial payloads.
- Telemetry: tests that assert structure and frequency, not exact values.
- **CASIL:** 
  - tests for classification outcomes given representative payloads and configurations;
  - tests for policy behavior (allow / redact / block) including:
    - size limits,
    - redaction rules,
    - pattern-based detection of obviously unsafe content;
  - tests that exercise CASIL’s behavior when disabled, misconfigured, or under high load.

### 3. Test Discipline

- Unit tests must run quickly and not depend on real external services.
- Integration tests must be clearly separated and runnable in CI with explicit setup.
- Flaky tests are considered bugs in the system (infra or code) and must be fixed, not ignored.
- CASIL must have tests that simulate hostile or malformed inputs and ensure:
  - the system remains stable;
  - behavior is deterministic and logged;
  - security posture (e.g., default-deny vs default-allow) follows configuration.

### 4. Quality Gates

A change may **not** be merged if:

- It alters public protocol behavior without accompanying tests.
- It introduces a new command or field without documentation.
- It reduces coverage in critical subsystems without justification.
- It violates the scope or architecture boundaries in this constitution.
- It introduces or modifies CASIL behavior without:
  - tests for policy outcomes and error conditions;
  - consideration of security implications in the spec/plan;
  - clear documentation of any new configuration or telemetry.

---

## VI. Development Process (Spec-Driven + Incremental)

### 1. Spec Kit as the Spine

For major features, protocol changes, or architectural moves:

- Use `/speckit.constitution` to keep this document current.
- Use `/speckit.specify` to define what and why (requirements, user stories, scenarios).
- Use `/speckit.clarify` to reduce ambiguity before planning.
- Use `/speckit.plan` to detail the implementation approach and stack.
- Use `/speckit.tasks` to break work into atomic, testable units.
- Use `/speckit.implement` to execute tasks in order.

For **CASIL-related features** (including new policies, new inspection modes, new metadata, or new telemetry):

- Specs must explicitly address:
  - security impact and threat considerations;
  - performance and latency implications;
  - failure modes and default behavior (e.g., default-allow vs default-deny on internal errors).
- Plans must describe:
  - how CASIL logic integrates with existing layers without violating layering rules;
  - how configuration is surfaced and validated;
  - how observability is provided (logs + telemetry).
- Tasks must ensure:
  - tests cover both “happy path” and adversarial scenarios;
  - documentation updates are included (config, runbook, developer guide).

### 2. Traceability

Every non-trivial change should be traceable to:

- A spec entry  
- A plan section  
- A task ID  
- One or more tests  

If you cannot explain “why does this code exist?” by pointing to a spec, **that code is suspect.**

For CASIL:

- Each policy, classification rule, or new configuration knob must have a clear lineage from spec → plan → tasks → tests → docs.

### 3. Small, Safe, Reversible Steps

- Avoid “big bang” rewrites.
- Prefer a series of well-scoped changes over a single gigantic PR.
- Maintain the ability to roll back or feature-gate risky behavior.
- CASIL additions should be:
  - guarded behind configuration flags or feature gates when in doubt;
  - able to be disabled cleanly if issues arise in production.

---

## VII. Coding Style & Implementation Conventions

This section defines how ArqonBus code should *feel* to read and work with.  
Anyone familiar with the codebase should be able to look at a new module and immediately recognize it as “ArqonBus code.”

These rules are about **clarity, stability, and maintainability** — not personal aesthetics.

CASIL code is held to the **same standards**, with additional care around clarity of policy decisions and security implications.

---

### 1. Design Philosophy

- **Boring is a feature.**  
  Code should be straightforward, unsurprising, and easy to explain. If a clever trick saves a few lines but would puzzle a new contributor, it is not welcome.

- **Readable first, fast second, clever last.**  
  Optimize only where necessary and only with measurement. Premature optimization that complicates logic is discouraged.

- **Small surface area, strong contracts.**  
  Prefer a small number of well-defined public interfaces over many loosely defined ones. Each public function or method must have a clear purpose.

- **Seams for evolution.**  
  The codebase should have obvious extension points (adapters, hooks, interfaces) for future work without needing deep surgery across unrelated modules.  
  CASIL-specific capabilities (classifiers, policies, telemetry hooks) should be implemented as well-defined seams rather than tightly coupled logic scattered across the codebase.

---

### 2. Module & Package Structure

ArqonBus Python code should follow these structural principles:

- **Packages reflect architecture, not org charts.**  
  Use package boundaries to mirror transport, routing, commands, storage, telemetry, CASIL, and utilities — not arbitrary groupings.

- **Single responsibility per module.**  
  A module should have one main idea:
  - e.g. `routing.py` for routing logic,  
  - `commands/status.py` for status command handling,  
  - `storage/redis_streams.py` for Redis Streams adapter,  
  - `casil/policies.py` for CASIL policy evaluation.

- **Avoid “god modules.”**  
  If a module needs to know about too many layers (e.g. transport + storage + telemetry + CASIL), it is doing too much and should be split.

- **Clear internal vs public APIs.**  
  - Public APIs are explicitly exported (e.g. via `__all__` or clear documentation).  
  - Helper functions internal to a module should be prefixed with `_` if they are not meant for external use.

---

### 3. Functions, Methods, and Public APIs

- **Function length and cohesion.**
  - Functions should fit on a screen without scrolling in a typical editor.  
  - If a function must be long, its structure must be obvious (e.g., clearly separated phases).

- **Naming.**
  - Names must describe *what* the thing does, not *how* it does it.  
  - Avoid abbreviations except for widely understood terms (e.g., `ws`, `id`, `jwt`).
  - CASIL-related names should make policy outcomes explicit, e.g. `evaluate_policy`, `apply_redaction`, `classify_message`.

- **Arguments and return types.**
  - Prefer explicit keyword arguments for booleans and configuration-like parameters.  
  - Return meaningful types (e.g. small dataclasses) instead of overloading tuples or dicts with implicit structure.
  - CASIL functions should return explicit result structures that indicate:
    - classification,
    - policy outcome (allow / redact / block),
    - any error or fallback mode.

- **No hidden global state.**
  - Avoid module-level mutable state that affects behavior.  
  - If state is needed, encapsulate it in a class or context object with clear lifecycle.
  - CASIL counters or rolling statistics must be clearly scoped and safe under concurrency.

---

### 4. Error Handling & Resilience

- **Fail loud on programmer errors.**
  - Cases that indicate a bug (e.g., impossible states, violated invariants) should raise clear exceptions and be logged as errors.

- **Fail soft on external errors.**
  - External issues (Redis offline, DNS failure, misconfig) should:
    - Log clearly with actionable messages.  
    - Trigger graceful fallback where possible.  
    - Avoid crashing the entire process unless continuing would be unsafe or misleading.

- **Guard internal invariants.**
  - Where critical assumptions are made (e.g. a message must have a `type`, a room must exist before broadcasting), assert or validate early.
  - CASIL invariants (e.g., “policy must choose exactly one of allow/redact/block”) should be enforced and tested.

- **No silent swallowing.**
  - `try/except: pass` is forbidden.  
  - Swallowing errors must be justified and logged, with a clear explanation of why ignoring is safe.
  - CASIL must not silently ignore policy evaluation failures; it must:
    - follow a documented default behavior (e.g., default-allow or default-deny configurable), and  
    - log the failure in a way that operators can see.

---

### 5. Concurrency, Async, and I/O

- **Async boundaries are explicit.**
  - I/O-facing functions (WebSocket reads/writes, Redis calls, disk access) must be clearly marked as `async` and isolated where possible.
  - Business logic should be largely synchronous and pure, called by thin async wrappers.

- **Avoid blocking the event loop.**
  - Heavy CPU-bound work must not run directly on the event loop.  
  - If unavoidable, it must be:
    - explicitly called out in the plan/spec, and  
    - offloaded to a thread pool or worker where appropriate.
  - CASIL classification and policy evaluation must be:
    - bounded in time and complexity;  
    - designed to avoid network calls or blocking operations on the hot path.

- **Ordering and consistency.**
  - If message ordering matters, the code must document and enforce the ordering guarantees (or lack thereof).  
  - Race conditions must be treated as bugs, not “edge cases we ignore.”

---

### 6. Logging, Debugging, and Diagnostics

- **Logs serve operators, not the code author’s curiosity.**
  - Log messages must be written from the perspective of someone debugging a system in production:
    - “What failed?”  
    - “For which client/room/channel?”  
    - “What do I do next?”

- **Log levels used consistently.**
  - `DEBUG`: noisy, development-level details, disabled in prod by default.  
  - `INFO`: lifecycle events, state transitions, high-level flow.  
  - `WARN`: recoverable issues worth noticing.  
  - `ERROR`: failures the system couldn’t complete correctly.  
  - `CRITICAL`: unrecoverable failure requiring human attention.

- **No secrets in logs.**
  - Access tokens, passwords, private keys, and sensitive payloads must never be logged at INFO+ levels.  
  - DEBUG logs that may contain sensitive data should be clearly marked and controlled via configuration.
  - CASIL redaction rules must apply consistently to logs and telemetry so that sensitive content is not accidentally exposed.

- **Correlation and context.**
  - Where possible, use correlation IDs or request IDs to tie related events together across logs.  
  - Include client id, room, channel, and command/event type in logs for message-related operations.
  - CASIL-related logs should include:
    - which policy fired,  
    - what the outcome was (allow/redact/block),  
    - high-level reason codes (not raw content).

---

### 7. Legacy Code, Refactors, and Technical Debt

- **Debt must be visible, not hidden.**
  - Known technical debt must be documented with:
    - what the issue is,  
    - why it exists,  
    - and what the intended fix path is.

- **Refactors must not change behavior silently.**
  - Significant refactors require:
    - stable test suites before and after, and  
    - explicit note in the plan/spec if behavior changes.

- **Incremental cleanups are welcome.**
  - Small improvements (naming, minor refactors, docstring updates) are acceptable as long as:
    - they do not blur the history of functional changes, and  
    - they do not bundle unrelated behavior changes.
  - CASIL-specific technical debt (e.g., temporary heuristics, naive classifiers) must be clearly marked as such, with a plan for hardening if relied on in production.

---

### 8. Examples of “ArqonBus-Style” vs “Not ArqonBus-Style”

**ArqonBus-Style:**

- A routing function that:
  - takes a clearly typed envelope,  
  - validates its fields,  
  - logs routing decisions at DEBUG,  
  - and returns an explicit result indicating which subscribers were notified.

- A Redis adapter that:
  - is the only place Redis is imported for history,  
  - clearly documents connection assumptions,  
  - and has tests for failure modes (timeout, connection refused, misconfig).

- A CASIL policy evaluator that:
  - receives a typed message representation and configuration,  
  - deterministically returns `allow`, `redact`, or `block` plus metadata,  
  - logs a concise summary of the decision without leaking sensitive payloads,  
  - is fully covered by tests for normal and adversarial inputs.

**Not ArqonBus-Style:**

- A module that:
  - opens WebSockets, talks directly to Redis, emits telemetry, and implements custom commands all in one file.

- A function that:
  - takes a dict, mutates it in-place, logs nothing, catches all exceptions, and returns `True` or `False` depending on “whether it kind of worked.”

- A CASIL implementation that:
  - performs network calls to external services on the hot path,  
  - swallows exceptions and silently allows messages,  
  - applies ad-hoc regexes inline without tests or documentation.

If new code starts to resemble the “Not ArqonBus-Style” patterns, it should be **rejected in review** or immediately refactored.

---
