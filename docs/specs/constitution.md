<!-- 
Sync Impact Report - ArqonBus Constitution v1.0.0
=================================================
Version change: Template → 1.0.0
Modified principles: Initial constitution establishment
Added sections: Core Principles, Vision and Scope, Architecture Principles, Code Quality and Testing, Development Process, Coding Style, Observability and Operations, Documentation, Governance
Removed sections: Template placeholders
Templates requiring updates: ✅ All templates verified to align with new constitution
Follow-up TODOs: None - all placeholders filled
-->

# ArqonBus Constitution

## Core Principles

### I. Vision and Scope
Build a small, sharp, reliable message bus that developers can drop into their systems to handle real-time, structured communication without adopting a heavy framework.

### II. Architecture Principles
Layered Design: Transport layer handles WebSocket connections; Routing layer manages rooms, channels, private messaging, broadcasts; Command layer processes status, channel management, history, ping; Storage layer provides in-memory history by default with pluggable Redis Streams adapter; Telemetry layer emits activity events and telemetry streams for observability. Stateless Where Possible: Per-process state kept minimal and explicit; Any persistent state goes into Redis or other defined storage. Config over Code: Rooms, telemetry rooms, and system channels configurable via env/config file; No magic names buried in logic. Minimal Dependencies: Prefer standard library and small number of well-understood libraries; No heavy frameworks unless they clearly reduce complexity. Public Protocol First: Message envelope and commands treated as public API; Changes require clear versioning and migration notes.

### III. Code Quality and Testing (TDD) (NON-NEGOTIABLE)
Test-Driven Development as Default: For new features, write or update tests before implementation where practical; At minimum, every new public behavior gets test coverage. Test Coverage Expectations: Core routing logic must be tested; All commands must have unit tests; Telemetry and activity event behavior covered; Redis Streams integration requires integration tests. Testing Stack: Use pytest for tests; Prefer small, focused tests over large ones; No reliance on real external services in unit tests; Integration tests clearly separated. Quality Gates: No new feature merged without tests; No silent behavior changes to public protocol without updated tests and documentation.

### IV. Development Process (Spec-Driven + TDD)
Spec-Driven Workflow: Use Spec Kit for major changes and new features: speckit.specify for requirements and scenarios; speckit.plan for technical breakdown and architecture impact; speckit.tasks for concrete implementation steps; speckit.implement for guided implementation. TDD Inside SDD: For each task derived from spec, capture/refine behavior in spec; Add/update tests to express behavior; Implement code to satisfy tests; Refactor keeping tests green. Small, Incremental Changes: Avoid big bang refactors without specs; Each change traceable back to spec entry or task.

### V. Coding Style and Conventions
General Style: Python 3.11+ style with type hints where they add clarity; Keep functions small and focused; Routing, commands, storage adapters should not become god-functions. Error Handling: Fail loudly and clearly on programmer errors; Fail gracefully on external errors with clear logs. Logging: Use structured, consistent logging; Always include enough context: client id, room, channel, command, and error where relevant. Backwards Compatibility: Once released as v1.0, protocol and behavior changes should be additive or versioned, not breaking, unless clearly marked as a major version change.

### VI. Observability and Operations
Metrics and Telemetry: Track core metrics: active connections, active rooms/channels, messages processed, errors; Telemetry messages follow simple, documented schema. Graceful Degradation: If Redis Streams unavailable, ArqonBus functions in memory-only mode where feasible; Telemetry failure must not crash main bus. Configuration: All operational settings from environment variables or config files, not hard-coded constants.

### VII. Documentation
Minimum Docs: README describing ArqonBus, how to run it, basic usage; Protocol specification for message envelope and built-in commands; Configuration documentation; Basic examples for client SDK usage. Truth Source: Specifications in Spec Kit are source of truth for behavior; README and other docs align with specs and updated when behavior changes.

## Vision and Scope

### Vision
Build a small, sharp, reliable message bus that developers can drop into their systems to handle real-time, structured communication without adopting a heavy framework.

### In Scope (v1.x)
WebSocket server for real-time, bidirectional messaging. Rooms and channels as first-class routing concepts. Structured JSON message envelope and command protocol. Optional Redis Streams integration for history and durable messaging. Lightweight telemetry and stats suitable for dashboards and monitoring. Official client SDKs starting with JS/TS and Python.

### Out of Scope (Non-goals)
Full multi-agent orchestration platform. Workflow engines, job schedulers, or full-blown ESB. UIs or dashboards baked into core server. Tight coupling to any specific LLM or MCP implementation. Business-domain logic (ArqonBus is infrastructure, not app logic). All future work must respect this boundary; Higher-level products build on ArqonBus, not inside it.

## Development Process

### Spec-Driven Workflow
Use Spec Kit for major changes and new features: speckit.specify for requirements and scenarios; speckit.plan for technical breakdown and architecture impact; speckit.tasks for concrete implementation steps; speckit.implement for guided implementation.

### TDD Inside SDD
For each task derived from spec: Capture/refine behavior in spec; Add/update tests to express behavior; Implement code to satisfy tests; Refactor keeping tests green.

### Small, Incremental Changes
Avoid big bang refactors without specs; Each change traceable back to spec entry or task.

## Governance

### Decision-Making
Architectural changes must be reflected in spec before implementation; Any change pushing ArqonBus outside defined scope must be rejected or moved to separate Arqon project.

### Scope Protection
ArqonBus remains focused message bus; Higher-level systems build on ArqonBus and belong in separate repos or modules; This constitution is binding for all future work on ArqonBus; All specs, plans, tasks, implementations align with these principles.

**Version**: 1.0.0 | **Ratified**: 2025-11-30 | **Last Amended**: 2025-11-30