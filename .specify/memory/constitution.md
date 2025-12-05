<!-- 
Sync Impact Report - ArqonBus Constitution v2.0.0
=================================================
Version change: 1.2.0 → 2.0.0
Modified principles: Product Identity, Vision and Scope, Architecture Principles, Protocol & Compatibility, Security (Multi-tenant), Governance
Added concepts: Voltron deployment pattern as normative architecture (Shield/Spine/Brain/Storage), Protobuf-first wire protocol with JSON reserved for admin/UI, future-proofing hooks for MAS (capabilities, intents, embeddings), stronger multi-tenant scoping rules
Removed sections: None
Templates requiring updates: Specs and plans that describe protocol format, deployment architecture, or tenant isolation; any Feature 001/002 docs that assumed JSON envelope instead of Protobuf
Follow-up TODOs: Align Feature 001 (core message bus) spec with Protobuf-first envelope and Voltron pattern; ensure Feature 002 (CASIL) spec clarifies Protobuf inspection path and MAS hooks
-->

# ArqonBus Constitution

This document defines the **non-negotiable principles** that govern how ArqonBus is designed, evolved, and maintained.  

It exists to protect ArqonBus from accidental bloat, silent breakage, and “clever” shortcuts that erode trust.

If a decision conflicts with this constitution, **the decision is wrong**.

---

## I. Product Identity

### 1. ArqonBus in One Sentence
> **ArqonBus is a small, sharp, Protobuf-first WebSocket message bus for structured, real-time communication in multi-agent systems, with an optional content-aware safety & inspection layer.**

It is **not** a framework, ESB, or application platform.  
It is **just powerful enough** to be an excellent transport layer and Voltron-style system backbone, and no more.

ArqonBus is designed as the **Spine** of a normative four-part architecture (the “Voltron Pattern”):

- **The Shield (Edge)** – typically Rust or a similarly capable runtime – terminates connections, performs TLS and auth integration, and normalizes incoming protocols. It holds **no business state** and speaks the ArqonBus protocol.  
- **The Spine (Bus)** – ArqonBus itself – carries all structured, high-volume traffic between components over WebSockets using **Protocol Buffers on the wire**.  
- **The Brain (Control)** – typically Elixir/OTP or an actor model runtime – owns long-lived, domain-level state (presence, rooms, authorization, workflows) and interacts exclusively via ArqonBus.  
- **The Storage (State)** – durable stores like PostgreSQL and fast stores like Valkey/Redis – persist configuration and ephemeral counters, accessed by services that themselves are ArqonBus clients.

ArqonBus may include an optional **Content-Aware Safety & Inspection Layer (CASIL)**:

- CASIL inspects Protobuf-encoded messages in-flight in a lightweight, bounded way.
- CASIL applies **transport-level safety and hygiene policies** (classification, redaction, blocking) without embedding business logic.
- CASIL produces metadata and telemetry that help operators understand and control message flows, especially in multi-agent environments.

CASIL is:

- about **content awareness and safety**, not AI reasoning or agent orchestration;
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
Build a WebSocket message bus that:

- Embeds easily into existing stacks and Voltron-style architectures (Shield, Spine, Brain, Storage).
- Plays nicely with modern infra (containers, Kubernetes, managed Redis/Valkey, PostgreSQL, etc.).
- Can be operated by a small team without a dedicated SRE army.
- Is **good enough** to serve as the backbone for serious systems, especially AI-native and multi-agent environments, **without forcing them into our worldview**.
- Treats **Protocol Buffers as the first-class wire format** for all high-volume, internal and agent-to-agent traffic, with JSON reserved for human-facing admin and observability surfaces.
- Offers **built-in, transport-level safety and insight** via CASIL so teams don’t have to bolt on ad-hoc filters and scrubbing layers around ArqonBus.

### 2. In Scope (v1.x and early v2.x)

ArqonBus **shall provide**:

- A **WebSocket server** for bi-directional, real-time messaging.
- First-class support for **rooms** and **channels** as routing primitives.
- A **strict, versioned Protocol Buffers message envelope** on the wire and a **small set of built-in commands**.
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
   - Encodes and decodes **Protocol Buffers envelopes** on the wire.  
   - Knows nothing about domain semantics.

2. **Routing Layer**  
   - Knows about rooms, channels, broadcasts, and private messaging.  
   - Responsible for subscription management and message fan-out.

3. **Command Layer**  
   - Implements built-in commands (status, history, channel management, ping, etc.).  
   - Treats commands as part of a public, versioned protocol defined in `.proto` files.

4. **Storage Layer**  
   - Provides in-memory history by default.  
   - Integrates with Redis Streams or other backends via explicit adapters.  
   - Must be swappable without rewriting routing or commands.

5. **Telemetry Layer**  
   - Emits activity, health, and performance signals.  
   - Must not be able to crash the core bus if misconfigured or offline.

6. **Inspection & Safety Layer (CASIL)**  
   - Optionally inspects structured, Protobuf-based messages at or near the routing/command boundary.  
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

### 1.1 Voltron Deployment Pattern (Architectural Invariance)

ArqonBus is designed to be the **Spine** in a normative deployment pattern for multi-agent and real-time systems:

- **The Shield (Edge)**  
  - Terminates TLS and incoming connections (including non-WebSocket protocols that are upgraded at the edge).  
  - Performs authentication and basic request normalization.  
  - Holds **no domain state** and does not implement business workflows.  
  - Speaks the ArqonBus protocol over WebSockets using Protobuf envelopes to the Spine.

- **The Spine (Bus)**  
  - ArqonBus itself: the sole, authoritative message bus for internal and agent-to-agent traffic.  
  - Enforces the protocol contract, routing semantics, CASIL policies, and telemetry guarantees defined in this constitution.

- **The Brain (Control)**  
  - Runs stateful, domain-level logic (presence, rooms, workflows, authorization decisions) in runtimes such as Elixir/OTP.  
  - Subscribes to rooms/channels on ArqonBus and emits events back; it does **not** bypass the Spine via private backchannels for core flows.

- **The Storage (State)**  
  - Uses durable (PostgreSQL) and ephemeral (Valkey/Redis) stores for configuration, history, and counters.  
  - Access is mediated by services that are themselves ArqonBus clients, ensuring state changes are reflected as bus events when relevant.

This pattern is the **default architectural expectation** for serious deployments. Other topologies must justify themselves in specs and must not violate ArqonBus’ protocol, safety, or observability guarantees.

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

### 1. Envelope as Public Contract (Protobuf-First)

The **Protocol Buffers message envelope** is a **public API and source of truth** for ArqonBus. For each protocol version:

- Required fields, optional fields, and types are defined in `.proto` files that are treated as canonical.  
- Invalid messages (including schema violations, missing required fields, or version mismatches) are rejected with explicit errors.
- Version mismatches are handled predictably (graceful errors, not silent drops).

JSON is reserved for:

- human-facing administrative and debug APIs (HTTP, dashboards, consoles);  
- serialized views of internal state and telemetry for operators.

All high-volume, internal, and agent-to-agent traffic carried by ArqonBus uses **Protobuf on the wire**.

When CASIL is enabled, it may attach **additional, optional metadata** to messages (e.g., classification tags, risk flags, policy result codes). These must:

- be clearly documented as optional fields or substructures in the Protobuf schema;
- never change the meaning of existing fields;
- be safe to ignore for clients that do not understand them.

### 2. Future-Proofing Hooks for Multi-Agent Systems

To support future multi-agent and AI-native capabilities without breaking existing clients:

- **Identity Hooks**  
  - Envelopes and auth metadata must support **capability-style descriptors** (e.g., lists of agent capabilities) alongside traditional roles.  
  - These are represented as optional fields in the Protobuf schema and interpreted by higher-level services, not by the core bus.

- **Routing Hooks**  
  - Envelopes may reserve or define optional fields for **semantic vectors** (embeddings) and **intents**.  
  - These fields are strictly additive, optional, and safe to ignore; they must not change routing semantics unless explicitly configured in higher layers.

- **Middleware Hooks**  
  - The protocol and architecture must support a **chain-of-responsibility** style of inspection and safety, implemented via CASIL within the bus and optional safety middleware at the Shield.  
  - Any such middleware must remain bounded in cost and respect ArqonBus’ guarantees about protocol stability, observability, and failure modes.

### 3. Semantic Versioning for Protocol

- `MAJOR` – breaking changes to envelope, commands, or core behavior.
- `MINOR` – new commands, additive fields, new telemetry, non-breaking logic.
- `PATCH` – bug fixes, performance improvements, and clarifications.

No “stealth” breaking changes in `MINOR` or `PATCH`. Ever.

CASIL-related additions (e.g., new metadata fields, new error codes for blocked messages, new telemetry events) must follow the same rules:

- additive and optional in `MINOR`;
- removal or semantic change requires a `MAJOR` bump.

### 4. Backwards Compatibility Rules

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

## VIII. Observability, Performance & Operations

CASIL is part of the runtime system and must be observable and operable like any other core layer.

### 1. Metrics & Telemetry

ArqonBus must expose enough signals to operate confidently, including CASIL:

- Core bus metrics:
  - Active connections, per-room and per-channel usage.
  - Message throughput and error rates.
  - History usage and Redis health.
  - Latency summaries (e.g. p50/p95/p99 for message handling where feasible).
- CASIL metrics & telemetry:
  - Counts of classified messages by `kind` and `risk_level`.
  - Counts of policy outcomes: `allow`, `allow_with_redaction`, `block`.
  - Counts and rates of:
    - oversize payloads (inspection skipped or blocked),
    - “probable secret” detections,
    - repeated policy violations per client/room/channel.
  - Suspicious pattern events: which clients/rooms are generating most violations, and what actions CASIL is taking (tag/block).

Telemetry must follow the same hygiene guarantees as logs: **no raw payloads**, redacted fields only, and stable schemas for dashboards.

### 2. Performance & Latency Expectations

While exact numbers depend on deployment, the system should:

- Avoid unbounded memory growth in normal operation.
- Handle bursts gracefully via backpressure or rate limiting.
- Make no hidden blocking calls on hot paths that could stall the event loop.
- Keep CASIL overhead:
  - bounded by `max_inspect_bytes` and pattern limits,
  - predictable in the presence of worst-case (but valid) inputs,
  - near-zero when CASIL is disabled.

Performance characteristics and known limits (including CASIL caps and limits) should be **documented**, not guessed.

### 3. Graceful Degradation

- If Redis Streams is unavailable, the system should fall back to in-memory history where feasible.
- Telemetry failures must not crash the bus; CASIL telemetry is allowed to drop events under backpressure, with clear warnings.
- CASIL failures or misconfigurations:
  - must follow the configured `default_decision` (allow/block),
  - must emit explicit logs and telemetry (e.g. `CASIL_INTERNAL_ALLOW/BLOCK`),
  - must never crash the main bus loop.
- Misconfiguration of core or CASIL settings should produce explicit startup errors rather than silent degradation.

### 4. Configuration & Environment Discipline

- All operational settings must be definable through environment variables or config files, including the CASIL block:
  - `casil.enabled`, `casil.default_decision`,
  - `casil.scope.include` / `casil.scope.exclude`,
  - `casil.limits.*` (max_inspect_bytes, max_policies, max_patterns, oversize behavior),
  - `casil.persist_metadata_in_history`,
  - `casil.expose_metadata_to_clients`.
- There should be a **single, documented** configuration resolution order.
- Non-default, production-relevant configuration (including hardened CASIL policies) should be reflected in deployment examples.
- CASIL config changes are **restart-only** in v1; any future live-reload must be designed and documented explicitly.

---

## IX. Documentation

Documentation is a first-class part of ArqonBus, not an afterthought.

If code and behavior change but the docs don’t, the system is effectively **undocumented**.  
This section defines the required documentation set, who it is for, and what “good” looks like for each artifact.

CASIL (Feature 002) is considered part of the core product and must be covered consistently across docs.

---

### 1. Documentation Principles

- **Docs are part of the product.**  
  An operator or developer’s first experience of ArqonBus is through its documentation. Sloppy docs imply sloppy internals.

- **Specs are the source of truth; docs are curated views.**  
  Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`) define behavior. Documentation files present that behavior to different audiences in coherent, opinionated forms.

- **Every change that affects users or operators must be reflected in docs.**  
  This includes protocol changes, CASIL behavior, configuration semantics, telemetry schemas, and operational procedures.

- **Documentation should be as small as possible but no smaller.**  
  Avoid walls of text. Each document should have a tight purpose, clear structure, and pragmatic examples.

- **CASIL must not be a hidden feature.**  
  Its purpose (content-aware safety), limits (64 KiB inspection cap, pattern limits), and trade-offs (default allow vs block, oversize behavior) must be clearly explained wherever relevant.

---

### 2. Required Documentation Set

ArqonBus must maintain and ship, at minimum, the following top-level documentation:

- `README.md` – high-level overview and repo entrypoint, including a short CASIL overview and where to read more.
- `quickstart.md` – “get it running in 10–15 minutes.”
- `architecture.md` – how ArqonBus is built and how the pieces fit together, including where CASIL sits in the pipeline.
- `developers_guide.md` – how to work on ArqonBus itself as a contributor, including how to extend or adjust CASIL safely.
- `runbook.md` – operational guide for running ArqonBus in real environments, including CASIL tuning, incident levers, and error/telemetry interpretation.
- `tutorial.md` – a narrative, end-to-end walkthrough building something small but realistic on top of ArqonBus, ideally showing an example of CASIL in action (e.g., blocking secrets or oversize messages).
- Protocol & command reference (can be in `specs/` or a dedicated doc) – authoritative API documentation, including error codes (`CASIL_POLICY_BLOCKED`, etc.) and any CASIL-related metadata fields.

All of these documents must be discoverable from the `README.md`.

---

### 3. `quickstart.md` – First Contact

**Audience:** New users who want to try ArqonBus with minimal context.

**Goals:**

- Get a working instance running locally or in a simple container environment.
- Demonstrate the *minimum viable flow*: connect client → join room → send and receive a message.
- Optionally show that CASIL can be turned on with a single config flag, without going into deep policy details.

**Must include:**

- Prerequisites (runtime, Python version, Docker optional, Redis optional).
- A minimal “run the server” example.
- A minimal client snippet (JS/TS and/or Python) that:
  - connects,  
  - joins a room,  
  - sends a message,  
  - logs a received message.
- A short “next steps” section pointing to:
  - `architecture.md` for deeper understanding,  
  - `tutorial.md` for a guided build,  
  - `runbook.md` for real deployment,
  - a pointer to CASIL docs (e.g., “see Security & CASIL section in architecture/runbook”).

The quickstart must be **copy-pasteable** and should be re-run whenever the protocol or startup process changes.

---

### 4. `architecture.md` – How ArqonBus Works

**Audience:** Engineers who need to understand ArqonBus internals to operate, extend, or integrate with it at a deeper level.

**Goals:**

- Explain the major components and how they interact.
- Reflect the layered model from the constitution (transport, routing, commands, storage, telemetry, CASIL).
- Make it possible to reason about performance, failure modes, and extension points.

**Must include:**

- A high-level diagram of the core architecture:
  - WebSocket entrypoints  
  - routing core  
  - CASIL inspection & policy layer (between validation and routing/persistence)  
  - command handling  
  - storage adapters  
  - telemetry outputs
- A clear explanation of:
  - connection lifecycle,  
  - message flow from client → server → recipients,  
  - how history works (in-memory vs Redis Streams),  
  - how CASIL affects persistence (blocked vs redacted vs original),  
  - how telemetry is emitted, including CASIL events.
- Description of extension points:
  - how to add a new command,  
  - how to add a new storage backend,  
  - how to hook into telemetry,  
  - how to extend CASIL classification or policy rules safely.
- Explicit notes on:
  - concurrency/async model,  
  - ordering guarantees (or the lack thereof),  
  - persistence guarantees.

`architecture.md` must be updated whenever there are meaningful architectural changes (including CASIL behavior changes).

---

### 5. `developers_guide.md` – Contributing to ArqonBus

**Audience:** Core contributors and external developers working on ArqonBus itself.

**Goals:**

- Make the contributor experience predictable and low-friction.
- Encode the practical application of the constitution, SDD, TDD, and CASIL rules into daily workflow.
- Standardize how features and fixes are added.

**Must include (in addition to existing points):**

- How CASIL is structured in the codebase (package layout, main entrypoints).
- How to:
  - add or modify CASIL policies,
  - add new classification rules,
  - update CASIL telemetry schemas,
  - adjust limits (max_inspect_bytes, oversize behavior) without breaking guarantees.
- Requirements for changes that touch CASIL:
  - tests and docs required,
  - when to update security/observability sections,
  - how to validate that CASIL does not leak sensitive data.

The developers’ guide should make it hard to “accidentally” bypass or weaken CASIL.

---

### 6. `runbook.md` – Operating ArqonBus in the Wild

**Audience:** SREs, ops engineers, and developers on call.

**Goals:**

- Provide step-by-step, low-drama procedures for common situations.
- Document what “normal” looks like and how to recognize “not normal.”
- Reduce guesswork when something breaks at 3 a.m.

**Must include (in addition to existing points):**

- CASIL-specific operational guidance:
  - how to enable/disable CASIL safely,
  - how to tighten or relax policies during an incident,
  - how to interpret CASIL error codes and telemetry events,
  - how to handle oversize payload spikes or secret-detection bursts.
- Example CASIL configs for common scenarios:
  - “never log payloads for secure rooms,”
  - “block probable API keys,”
  - “tag but allow large AI messages” (if enabled).
- Procedures for CASIL-related incidents:
  - misconfigured policies blocking critical traffic,
  - telemetry sinks failing under load,
  - suspected leaks requiring immediate tightening of CASIL settings.

If a production incident reveals missing CASIL instructions, `runbook.md` must be updated as part of the resolution.

---

### 7. `tutorial.md` – A Guided Build

**Audience:** Developers who learn best by building something concrete.

**Goals:**

- Demonstrate how to use ArqonBus to build a small but realistic feature end-to-end.
- Show recommended patterns and avoid anti-patterns.
- Bridge the gap between quickstart snippets and full applications.

**CASIL expectation:**

- At least one tutorial path should showcase CASIL in a realistic scenario (e.g., a chat or AI integration where CASIL:
  - blocks obviously secret-like content,
  - or enforces size limits and shows what the client sees).

---

### 8. Maintenance Rules

- **Docs must change when behavior changes.**  
  Any PR that alters externally visible behavior (protocol, commands, CASIL behavior, config, telemetry, performance characteristics) must update:
  - at least one of: `README.md`, `quickstart.md`, `architecture.md`, `developers_guide.md`, `runbook.md`, `tutorial.md`,  
  - and/or the protocol/reference/specs.

- **Broken docs are bugs.**  
  If something in the docs is wrong, out of date, or misleading (especially around CASIL safety guarantees), it is treated as a defect.

- **Examples must compile (or run).**  
  Code examples, including CASIL examples, should be extractable or validated where practical.

- **Documentation debt is tracked.**  
  If a feature ships with minimal or temporary documentation, a follow-up task must be captured in Spec Kit and the backlog.

---

### 9. Good vs Bad Documentation (ArqonBus Style)

**ArqonBus-style documentation:**

- Shows a complete minimal example, not a half-snippet.
- Explains *why* a feature exists and when to use it, including when to use CASIL and how to configure it safely.
- Points to other documents for deeper understanding instead of repeating content.
- Stays consistent with terminology (rooms, channels, envelope, commands, telemetry, CASIL).

**Not ArqonBus-style documentation:**

- Mentions CASIL (or any feature) in passing without showing how to use it safely.
- Uses terms not found in the protocol or architecture.
- Leaves out critical configuration details needed to reproduce examples.
- Buries important operational caveats (e.g., CASIL limits) in a footnote or not at all.

---

## X. Security & Safety Baseline

ArqonBus is infrastructure. If it is insecure, nothing built on top of it can be trusted.

Security is not a layer sprinkled on later, or a “nice to have.”  
It is a **design constraint** that applies from protocol to code to deployment.

This section defines the minimum, non-negotiable security posture for ArqonBus.

---

### 1. Security by Design

- **Security considerations must be part of every spec and plan.**  
  For any new feature, the specification and plan must answer:
  - What can go wrong if this is abused?  
  - How does this interact with authentication/authorization?  
  - Does this increase the attack surface?

- **Secure by default, configurable by experts.**  
  Defaults must be conservative:
  - reasonable message size limits,  
  - sane rate limits,  
  - safe timeouts,  
  - telemetry that does not leak sensitive content.

- **No feature ships without a security story.**  
  A feature that cannot be secured is either redesigned or rejected.

---

### 2. Least Privilege & Isolation

- **Principle of Least Privilege (PoLP).**
  - The ArqonBus process should run with the minimum OS and network privileges required.
  - Access to Redis, logs, and config must be scoped to exactly what is needed.

- **Separation of concerns at runtime.**
  - Operational concerns (metrics, telemetry, admin endpoints) should be logically isolated from user message flow (e.g., separate ports / paths / roles where appropriate).
  - Admin operations (e.g. shutting down, draining connections, introspecting state) must not be exposed through the same channels and permissions as regular client traffic.

- **Multi-tenant awareness (when applicable).**
  - If ArqonBus is run in a multi-tenant configuration, tenant boundaries must be explicit in the design (e.g. separate namespaces, auth scopes, routing constraints).
  - Every room, channel namespace, and persisted key or row (in Redis/Valkey and PostgreSQL) must be scoped or indexable by a `tenant_id` such that cross-tenant access becomes an explicit, reviewable violation rather than an accident.
  - Wildcard subscriptions and system observers must be tenant-scoped or clearly marked as operator-only views with strong access controls.
  - No tenant should be able to infer or affect the existence, activity, or data of another tenant via timing, error messages, or protocol behavior.

---

### 3. Authentication & Authorization

- **Pluggable but explicit auth.**
  - ArqonBus itself should not hard-code a single auth scheme, but it must:
    - define clear hooks for authentication and authorization, and  
    - document how to integrate with common schemes (JWT, API keys, OIDC-backed gateways, etc.).

- **Auth decisions are centralized and auditable.**
  - Logic that decides “who can connect / join / send / subscribe” must be:
    - centralized (not sprinkled throughout the code),  
    - testable,  
    - observable (with structured logs, not guesswork).

- **No assumptions of implicit trust.**
  - All client connections are untrusted by default.
  - Any operation that changes server state (joining rooms, creating channels, invoking commands) must be guarded by explicit checks.

---

### 4. Input Handling & Protocol Robustness

- **Strict validation at the edge.**
  - All incoming data (handshakes, envelopes, payloads) must be validated before being processed or stored.
  - Invalid or malformed messages must be rejected with clear error semantics, not partially processed.

- **Defensive limits.**
  - Message size limits must be in place and configurable.
  - Per-connection and per-IP rate limiting must be possible (even if implemented via external infra, ArqonBus must support the necessary hooks / signals).
  - Resource-intensive operations (e.g., history retrieval) must have bounded parameters and sane defaults.

- **Robust against malicious patterns.**
  - Known attack vectors (flooding, slowloris-style behavior, repeated malformed messages, room-join abuse) must be considered in design and tests.
  - Where feasible, the system should:
    - temporarily or permanently block abusive clients, and  
    - surface actionable diagnostics to operators.

---

### 5. Secrets, Configuration & Logging

- **Secrets are never hard-coded.**
  - API keys, tokens, passwords, and certificates must not appear in source code or defaults.
  - Secrets are provided via environment variables, secret management systems, or explicitly designated config files.

- **Sensitive data is protected in logs.**
  - No secret material (tokens, passwords, auth headers, private keys) may be logged at INFO or WARN levels.
  - DEBUG logging that may reveal sensitive payloads must:
    - be clearly marked as such, and  
    - be opt-in via configuration.

- **Configuration footprint is explicit and documented.**
  - Every security-impacting configuration option (limits, timeouts, auth hooks, TLS settings) must be:
    - documented,  
    - have clear defaults,  
    - and be safe if misconfigured in common ways.

---

### 6. Transport Security

- **TLS is the expected norm.**
  - ArqonBus must be able to run behind TLS-terminating proxies or with TLS enabled directly.
  - Documentation must clearly spell out secure deployment modes (reverse proxies, trusted networks, mTLS if applicable).

- **No “security through obscurity.”**
  - Relying on “hidden ports” or “nobody will find this endpoint” is not considered acceptable security posture.

---

### 7. Security Testing & Review

- **Security scenarios must be part of tests.**
  - Tests should include:
    - malformed envelopes,  
    - oversized payloads,  
    - high-frequency bursts,  
    - invalid command sequences,  
    - unauthorized access attempts.

- **Security impact is reviewed with changes.**
  - Any PR that:
    - introduces a new external dependency,  
    - changes auth behavior,  
    - modifies routing logic, or  
    - alters how data is persisted  
    must explicitly call out security implications.

- **Dependency hygiene.**
  - Dependencies must be kept up to date with security patches.
  - Known vulnerable versions must not be used.
  - Where possible, supply chain risks (e.g. unmaintained libraries) must be minimized or replaced.

---

### 8. Incident Response & Safety

- **Security incidents are first-class incidents.**
  - If a behavior could lead to data leakage, unauthorized access, or system compromise, it must be treated as a priority issue.

- **Clear operator playbooks.**
  - `runbook.md` must contain:
    - steps for revoking compromised secrets,  
    - steps for tightening configuration in an emergency,  
    - guidance for temporarily restricting access (e.g. disabling certain commands or endpoints).

- **Safe failure modes.**
  - When in doubt, the system should fail **closed** (deny) rather than fail open (allow) for security decisions.

---

Security is **not a bolt-on feature**.  
It is part of what makes ArqonBus a serious piece of infrastructure.

Any feature, change, or optimization that compromises these principles is **not acceptable**, regardless of convenience.

---

## XI. Governance & Scope Protection

### 1. Decision-Making Rules

- Architectural changes must be justified in a spec before implementation.
- Any proposal that pushes ArqonBus outside its defined scope (e.g. turning it into a workflow engine or orchestration layer) must be:
  - rejected from core, or  
  - split into a **separate project** in the Arqon ecosystem.
- Any proposal that changes the **wire protocol model** (away from Protobuf-first) or abandons the **Voltron deployment pattern** as the default must:
  - be treated as a **major architectural shift**,  
  - carry an explicit risk and trade-off analysis, and  
  - be versioned accordingly.

### 2. Scope Protection

- ArqonBus is **transport infrastructure**, not an application runtime.
- Higher-level systems (e.g. ArqonBus Workbench, proto-intelligent agents, etc.) must live in separate repositories or modules built on top of the bus, using ArqonBus as the Spine in the Voltron pattern.

### 3. Constitution Authority

- This constitution is binding for all core work.
- Specs, plans, tasks, and implementations must align with these principles.
- When in doubt, defer to:
  1. Scope boundaries  
  2. Protocol stability  
  3. Simplicity and clarity  

### 4. Amendments

- Changing this constitution requires:
  - A clear motivation (what is broken / missing).  
  - A spec entry describing the impact.  
  - A version bump of this document.  
  - Consensus from maintainers.

---

**Version**: 2.0.0  
**Ratified**: 2025-12-01  
**Last Amended**: 2025-12-05  
**Author**: Mike Young
