<!-- 
Sync Impact Report - ArqonBus Constitution v1.1.0
=================================================
Version change: 1.0.0 → 1.1.0
Modified principles: Vision and Scope, Architecture, Code Quality, Development Process, Observability, Governance
Added sections: Product Identity, Protocol Guarantees, Performance & Latency Expectations, Configuration & Environment Discipline, Security & Safety Baseline, Contribution Rules
Removed sections: Redundant wording, vague statements from v1.0.0
Templates requiring updates: None (constitution-compatible)
Follow-up TODOs: Ensure new performance and protocol guarantees are reflected in relevant specs & plans for future features
-->

# ArqonBus Constitution

This document defines the **non-negotiable principles** that govern how ArqonBus is designed, evolved, and maintained.  
It exists to protect ArqonBus from accidental bloat, silent breakage, and “clever” shortcuts that erode trust.

If a decision conflicts with this constitution, **the decision is wrong**.

---

## I. Product Identity

### 1. ArqonBus in One Sentence
> **ArqonBus is a small, sharp, reliable WebSocket message bus for structured, real-time communication.**

It is **not** a framework, ESB, or application platform.  
It is **just powerful enough** to be an excellent transport layer, and no more.

### 2. Core Promise
ArqonBus promises to application developers:

- A **clear, documented protocol** they can depend on.
- A **predictable runtime** that behaves the same in dev, staging, and prod.
- **Minimal cognitive overhead**: a few well-designed concepts that compose cleanly.
- **No surprises**: breaking changes are intentional, versioned, and rare.

If we ever violate this promise, we have broken ArqonBus.

---

## II. Vision and Scope

### 1. Vision
Build a message bus that:

- Embeds easily into existing stacks.
- Plays nicely with modern infra (containers, Kubernetes, managed Redis, etc.).
- Can be operated by a small team without a dedicated SRE army.
- Is **good enough** to serve as the backbone for serious systems, including AI-native and multi-agent environments, **without forcing them into our worldview**.

### 2. In Scope (v1.x and early v2.x)

ArqonBus **shall provide**:

- A **WebSocket server** for bi-directional, real-time messaging.
- First-class support for **rooms** and **channels** as routing primitives.
- A **structured JSON message envelope** and a **small set of built-in commands**.
- Optional **Redis Streams integration** for durable history and replay.
- Lightweight **telemetry**: health, metrics, and activity streams suitable for dashboards.
- Official **client SDKs**, starting with **JS/TS** and **Python**, that map directly onto the protocol without “magic”.

### 3. Out of Scope (Non-Goals)

ArqonBus core **must not** grow into:

- A full **multi-agent orchestration platform**.
- A **workflow engine**, job scheduler, or ETL system.
- A **UI framework** or dashboarding toolkit inside the core server.
- A **business logic layer** (no domain rules, no domain models).
- A hard dependency on any specific LLM / MCP / agent runtime.

Such capabilities may exist in **separate Arqon projects** that *use* ArqonBus as transport, but may not live in the core.

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

No layer may reach around another “because it’s convenient.”

### 2. Stateless Where Possible

- Per-process state must be **minimal, explicit, and observable**.
- Long-lived state belongs in Redis or another declared backing store.
- No hidden in-memory caches that cannot be rebuilt on restart.
- Horizontal scaling must be possible without re-architecting the system.

### 3. Config Over Code

- All operational behavior (rooms, system channels, telemetry endpoints, retention windows, limits) comes from **configuration or environment**, not from “magic” strings embedded in code.
- There must be a single, documented precedence order for configuration (e.g. env → config file → defaults), and the code must follow it.

### 4. Minimal Dependencies, Maximum Clarity

- Prefer stdlib plus a **small number of battle-tested libraries**.
- No large frameworks unless they demonstrably reduce complexity and are justified in the spec.
- If a dependency materially affects startup, error handling, or performance, it must be clearly documented and tested.

---

## IV. Protocol & Compatibility Guarantees

### 1. Envelope as Public Contract

The message envelope schema is a **public API**. For each protocol version:

- Required fields, optional fields, and types are clearly defined.
- Invalid messages are rejected with explicit errors.
- Version mismatches are handled predictably (graceful errors, not silent drops).

### 2. Semantic Versioning for Protocol

- `MAJOR` – breaking changes to envelope, commands, or core behavior.
- `MINOR` – new commands, additive fields, new telemetry, non-breaking logic.
- `PATCH` – bug fixes, performance improvements, and clarifications.

No “stealth” breaking changes in `MINOR` or `PATCH`. Ever.

### 3. Backwards Compatibility Rules

- Once v1.0 is released, **existing fields cannot change meaning**.
- Removal of fields, commands, or behaviors requires:
  - Documentation of deprecation in at least one prior minor version.
  - Clear migration guidance.
  - Major version bump if fully removed.

---

## V. Code Quality & Testing (TDD is the Default)

### 1. TDD as Working Standard

For new features and changes to public behavior:

- Define behavior in the **spec**.
- Add or update tests to express that behavior clearly.
- Implement code to satisfy the tests.
- Refactor while keeping tests green.

Where strict TDD is impractical (e.g. small refactors), tests must still exist and be updated before merging.

### 2. Coverage Expectations

- Routing core: high branch coverage, especially for edge cases (empty rooms, reconnection, flood scenarios).
- Command handlers: both unit tests (logic) and integration tests (end-to-end behavior with simulated clients).
- History / Redis Streams: deterministic tests that verify ordering, retention, and replay semantics.
- Envelope validation: tests for valid, invalid, and adversarial payloads.
- Telemetry: tests that assert structure and frequency, not exact values.

### 3. Test Discipline

- Unit tests must run quickly and not depend on real external services.
- Integration tests must be clearly separated and runnable in CI with explicit setup.
- Flaky tests are considered bugs in the system (infra or code) and must be fixed, not ignored.

### 4. Quality Gates

A change may **not** be merged if:

- It alters public protocol behavior without accompanying tests.
- It introduces a new command or field without documentation.
- It reduces coverage in critical subsystems without justification.
- It violates the scope or architecture boundaries in this constitution.

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

### 2. Traceability

Every non-trivial change should be traceable to:

- A spec entry  
- A plan section  
- A task ID  
- One or more tests  

If you cannot explain “why does this code exist?” by pointing to a spec, **that code is suspect.**

### 3. Small, Safe, Reversible Steps

- Avoid “big bang” rewrites.
- Prefer a series of well-scoped changes over a single gigantic PR.
- Maintain the ability to roll back or feature-gate risky behavior.

---

## VII. Coding Style & Implementation Conventions

### 1. General Style

- Python 3.11+ with type hints used where they clarify intent.
- Small, focused functions; avoid large multi-purpose methods.
- Explicit, readable control flow is preferred over cleverness.

### 2. Error Handling

- **Programmer errors** (bad assumptions, misuse of internal APIs) should fail loudly with clear exceptions.
- **External/environmental errors** (Redis down, network glitch) should fail gracefully:
  - Log clearly.
  - Degrade behavior where possible.
  - Never crash the entire bus due to a non-core subsystem.

### 3. Logging & Diagnostics

- Use structured logging (e.g. JSON or key=value lines) where possible.
- Logs must include, when relevant:
  - client id  
  - room  
  - channel  
  - command or operation  
  - error type / message  
- Avoid logging sensitive data (tokens, secrets, full payloads) unless explicitly configured for debugging.

---

## VIII. Observability, Performance & Operations

### 1. Metrics & Telemetry

ArqonBus must expose enough signals to operate confidently:

- Active connections, per-room and per-channel usage.
- Message throughput and error rates.
- History usage and Redis health.
- Latency summaries (e.g. p50/p95/p99 for message handling where feasible).

### 2. Performance & Latency Expectations

While exact numbers depend on deployment, the system should:

- Avoid unbounded memory growth in normal operation.
- Handle bursts gracefully via backpressure or rate limiting.
- Make no hidden blocking calls on hot paths that could stall the event loop.

Performance characteristics and known limits should be **documented**, not guessed.

### 3. Graceful Degradation

- If Redis Streams is unavailable, the system should fall back to in-memory history where feasible.
- Telemetry failures must not crash the bus.
- Misconfiguration should produce explicit startup errors rather than silent degradation.

### 4. Configuration & Environment Discipline

- All operational settings must be definable through environment variables or config files.
- There should be a **single, documented** configuration resolution order.
- Non-default production-relevant configuration should be reflected in deployment examples.

---

## IX. Documentation

### 1. Minimum Documentation Set

ArqonBus must include, at minimum:

- A **README** that explains what ArqonBus is, how to run it, and why it exists.
- A **protocol specification** describing the message envelope, message types, and commands.
- A **configuration reference** covering all relevant environment variables and config fields.
- **Quickstart examples** for JS/TS and Python SDK usage, mirroring real-world patterns.

### 2. Spec as Source of Truth

- Spec Kit artifacts (`spec.md`, `plan.md`, etc.) are the **canonical description** of behavior.
- README and other docs are views derived from the spec and must be updated when behavior changes.

---

## X. Security & Safety Baseline

ArqonBus is infrastructure and must not be careless about safety:

- Authentication/authorization hooks must be pluggable and clearly documented.
- No secret material should ever be logged at info or warn levels.
- Protocol should be robust against malformed and malicious payloads:
  - size limits  
  - type checks  
  - rate limits per connection  

Security is **not a future feature**; it is a baseline expectation.

---

## XI. Governance & Scope Protection

### 1. Decision-Making Rules

- Architectural changes must be justified in a spec before implementation.
- Any proposal that pushes ArqonBus outside its defined scope (e.g. turning it into a workflow engine or orchestration layer) must be:
  - rejected from core, or  
  - split into a **separate project** in the Arqon ecosystem.

### 2. Scope Protection

- ArqonBus is **transport infrastructure**, not an application runtime.
- Higher-level systems (e.g. ArqonBus Workbench, proto-intelligent agents, etc.) must live in separate repositories or modules built on top of the bus.

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

**Version**: 1.1.0  
**Ratified**: 2025-12-01  
**Last Amended**: 2025-12-01
**Author**: Mike Young