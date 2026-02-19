# The ArqonBus SOTA Engineering Doctrine

**Version:** 1.0.0  
**Scope:** All ArqonBus codebases, services, and tooling.  

ArqonBus is the nervous system for humans, devices, and agents. This doctrine defines *how* we build it.

This is a **lifecycle doctrine**: each stage produces artifacts that feed the next. Skipping a stage is a *constitutional violation*.

---

## 0. The Lifecycle at a Glance

For any non-trivial feature:

1. **Specification-Driven Design (SDD)**
   → write contracts, behaviors, invariants first
2. **Formal State Machines + Protobuf Schemas**
   → freeze how state changes and how messages look
3. **TDD for core logic + Integration Tests for everything else**
   → encode behavior into tests
4. **Continuous Verification Pipeline (security + perf + chaos)**
   → CI/CD enforces non-negotiables
5. **Secure-by-Design + Zero Trust**
   → every boundary authenticates, everything fails closed
6. **Observability-First Development (OFD)**
   → metrics, logs, traces wired in with the feature, not after
7. **Strict Code Quality (“Boring Code Manifesto”)**
   → readability, consistency, predictability
8. **API Stability & Compatibility Discipline**
   → evolution without breaking clients or tenants
9. **Resilience Engineering (SRE practices)**
   → SLOs, error budgets, graceful degradation
10. **Deployment Safety Nets (canary, shadow, rollback)**
    → safe rollout or safe rollback, never YOLO deploys

---

## 1. Specification-Driven Design (SDD)

### Purpose

Prevent “let’s just hack it in” from ever reaching production. All behavior is intentional, documented, and reviewable *before* code.

### Required Artifacts (per feature)

* **One-pager spec** with:

     * Problem statement & “Why now”
     * Inputs / outputs (shape + constraints)
     * Failure modes and how they surface
     * Security constraints (authn/z, tenant isolation)
     * Performance constraints (latency, throughput, fan-out limits)
* **Contract**:

     * For protocols: Protobuf envelope draft
     * For APIs: HTTP/REST/GraphQL/CLI contract (even if internal)
* **Acceptance criteria**:

     * Bulletproof, testable statements: “Given X, when Y, then Z”

### Hard Rules

* No code merged until a spec exists and is approved.
* Specs live in version control and are part of code review context.
* If you can’t explain the feature in one page, you don’t understand it yet.

---

## 2. Formal State Machines + Protobuf Schemas

### Purpose

Make state & protocol evolution safe and predictable.

### Required Artifacts

* **State Machine Definition** for each relevant domain:

     * States, events, transitions, invariants
     * Invalid transitions explicitly called out
  
* **Protobuf Schema**:

     * Messages, commands, envelopes, error types
     * Versioning rules applied (reserved tags, deprecated fields)


### Hard Rules

* All cross-service communication uses the Protobuf schema. No ad-hoc JSON.
* State transitions may only occur through well-defined handlers.
* Any change to a state machine or `.proto`:

     * must update docs
     * must add regression tests (golden vectors, compatibility tests)

---

## 3. TDD Selectively + Integration Tests for Everything Else

### Purpose

Use tests as *executable specifications* without drowning in useless test noise.

### Where TDD is Required

* Pure business logic (e.g., presence rules, routing decisions).
* State transition logic (state machine step function).
* Protocol transformations (e.g., mapping input → internal envelope).

### Where Integration Tests Rule

* Cross-service flows (Shield ↔ Spine ↔ Brain ↔ Storage).
* Multi-tenant behavior and isolation.
* Failure handling: timeouts, partial outages, degraded dependencies.

### Required Artifacts

* **Unit tests**:

     * Fast, deterministic, no I/O
* **Integration tests**:

     * Use real components: NATS/Valkey/Postgres test harness
     * Run under load scenarios where appropriate

### Hard Rules

* No bug fix without a regression test.
* No change to protocol/state machines without golden test vectors.
* No test may depend on unbounded sleeps or real time; use controlled clocks/notifications.

---

## 4. Continuous Verification Pipeline (Security + Perf + Chaos)

### Purpose

CI/CD as a *guardian*, not a suggestion.

### What CI Must Enforce (per PR)

* Build + format + lint (Rust + Elixir)
* Unit tests + integration tests
* Security checks:

     * Dependency audits
     * Static analysis for unsafe patterns

* Performance checks:

     * Benchmarks on hot paths with thresholds

* Chaos/adversarial checks:

     * Fuzz tests for message handlers and parsers
     * Malformed payload tests
     * Flood/DoS simulation on non-prod infra

### Hard Rules

* No bypassing CI. No “admin merges.”
* Red build blocks merges. No exceptions.
* Any newly added tool/check eventually becomes “must pass,” never “best effort.”

---

## 5. Secure-by-Design + Zero Trust

### Purpose

Treat the system as permanently under attack.

### Principles

* **Zero Trust**:

     * No component trusts any other by default.
     * Mutual auth between services.

* **Least Privilege**:

     * NATS subjects, DB roles, and Wasm policies scoped per tenant & capability.

* **Fail Closed**:

     * If a security dependency fails (e.g. safety Wasm, auth service), the default is *deny*, not allow.

### Required Artifacts

* Threat model per major feature.
* AuthN/AuthZ matrix:

     * Which principal can perform which actions on which resources.

* Secure defaults:

     * No default passwords
     * TLS on by default
     * Minimal open ports

### Hard Rules

* Secrets never live in code or logs.
* No “temporary” bypasses to auth or safety in production.
* Any known security compromise = immediate incident + hotfix cycle.

---

## 6. Observability-First Development (OFD)

### Purpose

You can’t debug what you can’t see. Observability is part of the feature, not afterthought.

### Required Artifacts (for each feature)

* Metrics:

     * Counters for success/failure
     * Histograms for latency
     * Gauges for load levels / queue depths

* Traces:

     * Spans for major operations (Edge → Spine → Brain → Storage)
     * Correlation IDs (TenantID, RequestID, trace_id)

* Logs:

     * Structured only (JSON/kv)
     * With log level discipline
     * Without sensitive data (PII, PHI, tokens, raw payloads in higher levels)

### Hard Rules

* No new hot-path feature is “done” without metrics, logs, and traces.
* Observability must prove or refute SLO adherence.
* No plaintext PII, PHI, or secrets in logs. Ever.

---

## 7. Strict Code Quality Standards (“Boring Code Manifesto”)

### Purpose

Keep ArqonBus readable, consistent, and safer to change under pressure.

### Core Tenets

* **Clarity > Cleverness**:

  * Boring, explicit code wins.
* **Consistency > Individual Style**:

  * Automated formatting + strict lint rules
* **Explicit over Implicit**:

  * No magic, monkey-patching, global mutable state, or reflection tricks in hot paths.

### Tooling

* Rust:

  * `rustfmt`, `clippy` (pedantic), `cargo deny` / `cargo audit`
* Elixir:

  * `mix format`, `credo` (strict), `sobelow` (for web/security if applicable)

### Hard Rules

* No `unwrap()` / `expect()` in non-startup paths.
* No TODOs in production paths without linked issue.
* New code must leave the touched module **cleaner** than before.

---

## 8. API Stability & Compatibility Discipline

### Purpose

Evolve quickly without betraying users or tenants.

### Principles

* Strict SemVer:

  * MAJOR for breaking protocol changes
  * MINOR for additions
  * PATCH for fixes only
* Backward compatibility:

  * New servers must accept old clients when within the same MAJOR.
* Graceful deprecation:

  * Fields marked deprecated for at least one MINOR before removal.

### Required Artifacts

* Compatibility tests:

  * Old client ↔ new server
  * New client ↔ old server (within policy)
* Deprecation docs:

  * What’s changing, why, migration path

### Hard Rules

* No “stealth” breaking change in MINOR/PATCH.
* No removal of fields/commands without a deprecation cycle.
* Any protocol change must have a rollback plan.

---

## 9. Resilience Engineering (SRE Practices)

### Purpose

Design for failure, not for “happy-path-only” demos.

### Core Concepts

* SLOs & SLIs:

  * Latency targets (p95, p99)
  * Availability
  * Error rates
* Error Budgets:

  * Allow faster feature shipping until budget spent
  * When spent, focus on reliability work

### Required Artifacts

* SLO definitions per major surface (e.g., connect, publish, subscribe).
* Degradation strategies:

  * Shed load
  * Drop non-critical features before core features
* Runbooks:

  * For common failure modes: DB slowness, NATS outage, spike in connect churn

### Hard Rules

* SLO violations trigger investigation, not finger-pointing.
* No feature may ship without a defined failure mode: “How does this degrade?”
* Error budgets are visible and respected in planning.

---

## 10. Deployment Safety Nets (Canary, Shadow, Rollback)

### Purpose

Never bet the whole system on a single deploy.

### Deployment Patterns

* **Canary Releases**:

  * New version to small slice of traffic/tenants first.
* **Shadow Traffic**:

  * Mirror real traffic to new version for observation only.
* **Rollbacks**:

  * Single-command, well-tested rollbacks.

### Required Artifacts

* Per-service deployment plan:

  * Canary strategy
  * Shadow plan (if used)
  * Rollback playbook
* Health checks:

  * Liveness & readiness
  * Tenant-aware health signals where relevant

### Hard Rules

* No “big bang” deploys for core components.
* Rollback must be tested regularly, not assumed.
* Deploys are boring, routine, and reversible—or they are not allowed.

---
