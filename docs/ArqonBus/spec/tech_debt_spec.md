# ArqonBus Technical Debt Specification

**Version:** 1.0.0  
**Scope:** All ArqonBus services, libraries, schemas, and tooling.  
**Goal:** Ensure technical debt is intentional, visible, time-bounded, and continuously reduced — never allowed to silently rot the system.  

---

## 0. First Principles

1. **Debt is inevitable; rot is optional.**
   We accept that technical debt will exist; we do *not* accept untracked, unmanaged debt.

2. **Only intentional debt is allowed.**
   Debt must be explicitly documented, time-bounded, and owned. Anything else is treated as a defect.

3. **Technical debt is a reliability and security risk.**
   Debt is not “just code cleanup.” It threatens correctness, security, and performance in a distributed, multi-tenant infrastructure.

4. **No silent debt.**
   Every known debt item must be visible in both:

   * `technical_debt/` docs, and
   * the issue tracker (Jira/GitHub/etc.).

---

## 1. Taxonomy of Technical Debt

All technical debt MUST be classified into one or more of these types:

### 1.1 Protocol Debt

* Deprecated Protobuf fields not cleaned up
* Duplicate or overlapping message types
* Divergence between `.proto` and actual behavior
* Ad-hoc JSON used where Protobuf should be used

### 1.2 State Machine Debt

* Undocumented states or transitions
* Hidden transitions not represented in diagrams/spec
* Invariants enforced in some paths but not others
* Legacy states preserved “just in case”

### 1.3 Concurrency & Ordering Debt

* Shared mutable state without clear ownership
* Missing backpressure or bounded queues
* Blocking calls in async contexts / schedulers
* Non-deterministic or order-dependent logic without guarantees

### 1.4 Security Debt

* Over-broad permissions or roles
* Missing or partial auth checks
* Unpatched vulnerable dependencies
* Ambiguous input validation

### 1.5 Observability Debt

* Missing metrics for critical paths
* Logs without correlation IDs
* Critical flows without trace spans
* Logs that are unstructured or inconsistent

### 1.6 Tooling & Infrastructure Debt

* Manual steps in deploys or rollbacks
* Flaky tests in CI
* Non-reproducible builds
* Missing or brittle scripts for migration/ops

---

## 2. Severity & Deadlines

Each debt item MUST have a severity and a time-to-live (TTL):

| Level    | Description                                          | Deadline                               |
| -------- | ---------------------------------------------------- | -------------------------------------- |
| Critical | Threatens correctness, security, or tenant isolation | Fix immediately (same sprint / hotfix) |
| High     | Significant architectural or performance risk        | Fix within **1 release cycle**         |
| Medium   | Impacts maintainability, slows development           | Fix within **2 release cycles**        |
| Low      | Minor cleanliness / non-urgent refactor              | Backlog, periodic cleanup cycles       |

**Rule:**
Any debt affecting Shield, Spine, Brain, or Storage *hot paths* starts at **High** and is escalated to **Critical** if it repeatedly impacts incidents or SLOs.

---

## 3. Technical Debt Enforcement Playbook

This section defines **how humans operate** around technical debt.

### 3.1 When You Can Intentionally Take on Debt

Intentional technical debt is allowed **only when all of the following are true**:

1. There is a **clear, immediate benefit** (e.g., shipping a critical feature, meeting a high-impact deadline).
2. The debt is:

     * Documented
     * Owned by a specific person/team
     * Assigned a severity & TTL
     * Recorded in both `technical_debt/` and the issue tracker
  
3. The risk is understood and explicitly stated:

     * Impact on correctness, security, performance, or maintainability

### 3.2 How to Document Technical Debt

Every intentional debt must have:

* **Title**: Short, descriptive (e.g., `TD-012: Legacy Room Presence Path`).
* **Type(s)**: One or more from the taxonomy above.
* **Location**: File(s), module(s), components.
* **Severity**: Critical/High/Medium/Low.
* **Owner**: Individual + team.
* **TTL**: Date by which it must be resolved.
* **Impact**:

     * What can break?
     * Who/what is affected (tenants, internal dev, ops)?

* **Exit Plan**:

     * Steps required to eliminate the debt.
     * Extra validation/tests required.

**Suggested file structure:**

```text
technical_debt/
  README.md
  protocol.md
  state_machines.md
  concurrency.md
  security.md
  observability.md
  tooling_infra.md
```

Each file holds a list of current debt items, linking to issues.

### 3.3 PR-Level Rules for Developers

When submitting a PR:

* **If you introduce debt**:

     * Add an entry in the appropriate `technical_debt/*.md` file.
     * Create/attach an issue (e.g., `TD-###`) with TTL & owner.
     * Reference the debt in the PR description.

* **If you touch an area with existing debt**:

     * Prefer to pay it down if feasible.
     * If not, confirm the existing TTL is still valid.

* **Forbidden:**

     * Adding `TODO`, `FIXME`, `HACK`, or similar without a linked debt/ticket ID.
     * Adding comments that imply future work without entering formal debt.
     * “Temporary” shortcuts with no clear timeline.

### 3.4 Reviewers’ Checklist

For every PR, reviewers MUST:

1. **Detect untracked debt**:

     * Do you see shortcuts, duplication, hacks, or commented-out logic?
     * Is it documented as debt?
     * If not, request either:

             * A proper fix now, or
             * A formal debt entry with TTL.

2. **Verify intentional debt**:

     * Does the justification make sense?
     * Is the severity correct?
     * Is the TTL realistic and soon enough?
     * Is the owner clearly assigned?

3. **Refuse accidental/hidden debt**:

     * No silent layering violations (Shield talking directly to DB, etc.).
     * No new magic numbers or config in code.
     * No quick hacks in core paths without documentation.

4. **Enforce “leave it cleaner” principle**:

     * If the PR modifies a debt-heavy module, does it at least not make it worse?
     * Prefer small cleanups opportunistically.

### 3.5 SRE / Lead Responsibility

Per iteration (sprint, release, etc.):

* Review all **Critical** and **High** debt.
* Ensure expired TTLs are addressed:
 
     * Either fixed, or consciously re-evaluated (with justification).

* Incorporate debt reduction into planning:

     * Reserve a fixed percentage of capacity (e.g., 10–20%) for debt work.

Quarterly:

* Review debt burndown:

     * Number of items
     * Risk-weighted “Debt Score”
     * Impact on incidents and SLOs

---

## 4. Technical Debt Scanner Spec (Policy-as-Code)

This section defines the **automated, policy-as-code enforcement** of the above rules — the “Technical Debt Scanner.”

The scanner exists to catch **objective, mechanical** indicators of debt or violations that human reviewers might miss.

### 4.1 Goals of the Scanner

* Detect untracked or dangerous technical debt patterns.
* Enforce conventions around:

     * TODO/FIXME usage
     * Architecture layering
     * Configuration discipline
     * Unsafe code patterns
     * Deprecated APIs and protocols

* Integrate with CI/CD as a blocking gate.

### 4.2 Implementation Overview

You can implement this with any Policy-as-Code framework (e.g., OPA/Conftest, custom lints, GitHub Actions). The spec is tool-agnostic.

The scanner should:

1. Run on every PR and main-branch push.
2. Scan:
  
     * Source code (Rust, Elixir, config)
     * `.proto` files
     * `technical_debt/` entries

3. Emit:

     * **Errors** (block merge)
     * **Warnings** (visible but not blocking, for now)
  
4. Produce a report as a CI artifact + comment on PR.

### 4.3 Scannable Patterns (Rules)

#### 4.3.1 TODO / FIXME / HACK Discipline

**Rule:** Any TODO-like comment must reference a debt ticket/ID.

**Pattern:**

* Match comments containing `TODO`, `FIXME`, `HACK`, `XXX`, etc.

**Enforcement:**

* Error if matched comment does **not** also contain a pattern like:

  * `TD-###`, `#<issue_number>`, or equivalent.

Example (valid):

```rust
// TODO TD-123: Replace this temp routing shortcut with semantic router
```

Example (invalid – blocks CI):

```elixir
# TODO: clean this up later
```

---

#### 4.3.2 Layering / Architecture Violations

Derived from the “Voltron Pattern” and Bypass Ban.

**Rules:**

* Shield/Edge code must not:

  * Import DB access modules
  * Access storage-layer clients directly
* Brain/Control must not:

  * Handle raw TCP/WS directly
* Any service must not:

  * Bypass Spine for inter-service communication (no direct HTTP/RPC except allowed control planes)

**Scanner Implementation:**

* Module import graph analysis:

  * Forbidden dependency edges (e.g., `shield` → `db`)
* Directory-based heuristics:

  * `shield/*` cannot import `storage/*`
  * `brain/*` cannot import `edge/*` socket crates

**Enforcement:**

* Violations are **errors** (hard block).

---

#### 4.3.3 Config vs. Code (Magic Numbers)

**Rules:**

* Operational thresholds (timeouts, retries, rate limits, buffer sizes) must not be hardcoded.

**Scanner Approach:**

* Detect “magic constants” patterns in hot-path modules:

  * Small integer or duration literals not declared in config modules.
  * Heuristic threshold: e.g., `1000`, `5000`, `60 * 1000`, etc.

* Allowlist:

  * Known harmless values (0, 1, -1, small offsets, etc.)
  * Constants specially marked as safe.

**Enforcement:**

* Warning on first iteration → upgrade to error once baseline is clean.

---

#### 4.3.4 Unsafe Error Handling Patterns

**Rules:**

* No `unwrap`/`expect` in non-startup code.
* No generic `catch-all` where typed errors are possible.
* No logging-and-swallowing errors.

**Scanner Patterns:**

* Rust:

  * Disallow `unwrap()`, `expect()` outside allowed modules.
  * Scan for `match`/`if let` branches that drop errors.
* Elixir:

  * Detect `rescue` / `try` blocks returning generic error atoms without context.

**Enforcement:**

* In hot paths: **error**.
* In non-critical paths: can be **warning** initially, with plan to tighten.

---

#### 4.3.5 Deprecated APIs & Protocol Debt

**Rules:**

* Deprecated `.proto` fields kept longer than allowed TTL.
* Deprecated functions/modules still used in new code.

**Scanner Implementation:**

* Parse `.proto` for fields marked `deprecated = true`.

  * Track deprecation date/version in comment or annotation.
  * If older than 1 MINOR version → flag.
* Search codebase for usage of deprecated fields/APIs.

**Enforcement:**

* Usage of deprecated APIs in new code: **error**.
* Expired deprecated fields not removed: **warning → error**, depending on policy.

---

#### 4.3.6 Tenant Isolation & Namespacing

**Rules:**

* All NATS subjects, Valkey keys, and DB rows must be tenant-namespaced.

**Scanner Patterns:**

* Inspect code where keys/subjects are constructed:

  * Ensure presence of `TenantID` or equivalent prefix.
* Flag any occurrence of bare subjects/keys in certain modules.

**Enforcement:**

* Missing tenant prefix in new code = **error**.

---

#### 4.3.7 Observability Debt

**Rules:**

* New public-facing behavior must produce:

  * Metrics
  * Logs (structured)
  * Traces (where applicable)

**Scanner Approach (two layers):**

1. Static:

   * If a new handler or endpoint is added:

     * Look for adjacent metric/log/trace calls in the same module.
2. Dynamic:

   * As part of integration tests:

     * Send test traffic, then assert presence of expected metrics/log fields.

**Enforcement:**

* No observability on new major behavior = **error**.

---

### 4.4 Technical Debt Scanner Configuration

**Config file (example):**

```yaml
rules:
  todo_ticket_required: true
  forbid_layer_bypass:
    shield_to_db: true
    brain_to_tcp: true
    direct_http_between_services: true
  magic_numbers:
    enabled: true
    allowed_values: [0, 1, -1, 2, 3]
  unwrap_forbidden:
    allow_in_modules:
      - bootstrap
      - tests
  deprecated_usage:
    fail_on_new_usage: true
    warn_on_overdue_cleanup: true
  tenant_prefix_required: true
  observability_required_for_new_handlers: true
```

This can be used by a custom tool, OPA/Conftest, or lint framework.

---

### 4.5 Integration with CI/CD

* The Technical Debt Scanner runs as its own CI job:
  `technical_debt_scan`

* It must:

  * Run on every PR and main-branch push.
  * Exit non-zero on **errors** (blocking).
  * Produce a human-readable summary + machine-readable artifact (JSON).

* For each rule, define:

  * `severity: error | warning`
  * `owner: team or role`
  * `link: doc or playbook entry`

---

## 5. Governance & Evolution

* This spec is versioned under SemVer.
* Tightening rules (more debt detection) = MINOR bump.
* Changing behavior of existing rules = MAJOR bump.
* Tooling, patterns, and heuristics must be revisited quarterly to:

  * Reduce false positives
  * Expand coverage
  * Align with evolving architecture

---

## 6. Summary

This Technical Debt Spec ensures:

* Debt is **explicit**, **owned**, and **time-bounded**.
* Reviewers know exactly what to look for.
* CI has concrete patterns to detect hidden or accidental debt.
* Protocol, state machine, security, and observability debt are treated as first-class risks.
* Over time, the codebase gets **cleaner**, **safer**, and **faster to work with**, not worse.