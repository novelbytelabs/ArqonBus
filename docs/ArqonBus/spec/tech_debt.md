# **ArqonBus Technical Debt Doctrine (SOTA 2025)**

**Status:** Mandatory
**Purpose:** Prevent unstable foundations, velocity decay, and correctness erosion over time.
**Scope:** All services, modules, protocols, state machines, schemas, and tooling.

---

# **I. First Principles**

### **1. Technical Debt Exists — Rot is Optional**

All codebases accumulate debt.
Mature systems prevent *rot* through governance, not heroics.

### **2. Intentional Over Accidental**

The only acceptable form of technical debt is **intentional, documented, time-bounded debt**.
Accidental/untracked debt is treated as an operational hazard.

### **3. Debt Is a Security and Reliability Risk**

Unmanaged debt:

* introduces ambiguous behavior
* obscures invariants
* breaks ordering guarantees
* increases attack surface
* causes catastrophic regressions

Debt must be treated like a *defect*, not an inconvenience.

---

# **II. Types of Technical Debt (ArqonBus-Specific)**

### **1. Protocol Debt**

* Deprecated `.proto` fields not removed
* Versioning inconsistencies
* Multiple representations of similar data
* Drift between code and schema

**Impact:** Client incompatibilities, routing failures, silent corruption.

---

### **2. State Machine Debt**

* Undefined transitions
* Hidden transitions not captured in spec
* Invariants not enforced everywhere
* Legacy states kept for convenience

**Impact:** Presence corruption, inconsistent permissions, partition divergence.

---

### **3. Concurrency / Ordering Debt**

* Shared mutable data without clear ownership
* Missing backpressure
* Rust async blocking / Elixir scheduler starvation
* Non-deterministic handlers

**Impact:** Deadlocks, unexpected ordering, partial outages.

---

### **4. Security Debt**

* Missing auth checks
* Excessive permissions
* Deprecated crypto
* Missing validation on boundaries
* Unpatched dependencies

**Impact:** Breach, tenant leakage, escalation of privilege.

---

### **5. Observability Debt**

* Missing metrics
* Uncorrelated logs
* No trace spans for critical paths

**Impact:** Outages become invisible until critical.

---

### **6. Tooling & Infrastructure Debt**

* Manual processes
* Missing rollback scripts
* Flaky CI tests
* Unreproducible builds

**Impact:** Deployment failures, slow recovery, unknown regressions.

---

# **III. Technical Debt Lifecycle**

Debt has a **formal lifecycle**:

1. **Identification**
   Detected during coding, review, incident, or protocol evolution.

2. **Classification**

   * Critical (Fix immediately)
   * Major (Fix within 1 cycle)
   * Minor (Backlog)

3. **Documentation**
   All debt must be captured with:

   * Location
   * Type
   * Impact
   * Risk
   * Estimated cost
   * Time-to-live (TTL)

4. **Tracking & Visibility**
   Debt is tracked in `/technical_debt/<area>.md` *and* in issue tracker.

5. **Resolution**
   Debt is removed via:

   * Refactor
   * Rewrite
   * Protocol cleanup
   * Schema migration
   * Architectural correction

6. **Validation**
   Every debt removal must update:

   * Specs
   * State machines
   * Tests
   * Observability instrumentation

---

# **IV. Technical Debt Enforcement in CI/CD**

This integrates directly with the **CI/CD Enforcement Spec**.

CI/CD MUST enforce:

### **1. No debt may be merged without:**

* a documented justification
* time-to-live (TTL)
* owner
* exit plan

### **2. Forbidden in PRs:**

The pipeline rejects:

* TODO/FIXME without linked ticket
* Deprecated API usage without migration plan
* Unbounded backpressure or memory constructs
* Untyped errors or catch-all handlers
* Disabling lint/tests to “get something in”

### **3. TTL Expiry Enforcement**

CI fails a build if:

* TTL has passed
* Orphaned debt tickets
* Deprecated fields older than one MINOR version

### **4. Architectural Debt Scanner (optional, SOTA)**

CI scans for:

* Layers bypass violations
* Business logic in the Shield
* DB access outside Storage layer
* Hardcoded configuration
* Forbidden blocking patterns
* Duplicate logic across services

### **5. Technical Debt Budgets**

Exactly like error budgets.

* Feature work allowed as long as debt budget not exceeded
* When exceeded:

  * Freeze new features
  * Focus on remediation

This ensures velocity *improves*, not decays.

---

# **V. Technical Debt Severity Levels**

| Level        | Description                                           | Action               |
| ------------ | ----------------------------------------------------- | -------------------- |
| **Critical** | Endangers correctness, security, or tenants           | Fix immediately      |
| **High**     | Causes architectural drift or performance degradation | Fix within the cycle |
| **Medium**   | Causes maintainability issues                         | Fix within 2 cycles  |
| **Low**      | Minor code cleanliness                                | Backlog, but tracked |

Any debt in **Shield, Brain, Spine, Storage core loops** is automatically **Critical**.

---

# **VI. Technical Debt Governance**

### **The Debt Triad:**

Every cycle, three roles review debt:

1. **Architect Maintainer** — determines architectural risk
2. **Tech Lead** — ensures development flow isn’t slowed
3. **SRE Lead** — evaluates operational cost

Decisions require **unanimous agreement**.

### **Quarterly Debt Reduction Cycle**

Every quarter:

* Review outstanding debt
* Recalculate severity
* Close resolved items
* Reprioritize high-risk areas
* Allocate a fixed % of engineering time (Spotify uses 20%)

### **Debt Burn-down Metric (DBM)**

ArqonBus must maintain a visible debt metric using:

* number of items
* weighted risk
* operational impact

---

# **VII. Philosophy**

### **“Technical debt is not shame.”**

Debt is a strategic tool when intentionally used.

### **“But technical debt is never silent.”**

Undocumented debt is a form of rot.
Rot is forbidden in ArqonBus.

### **“We refactor as we go, not someday.”**

Every PR must leave the subsystem **cleaner** than it was found.

### **“We optimize for long-term velocity, not short-term delivery.”**

This is the defining trait of elite engineering organizations.

---

# **VIII. Should You Add This Section?

YES — and it belongs in two places:**

### **1. Your Constitution**

As a top-level “Code Quality & Engineering Standards Law.”

### **2. Your CI/CD Enforcement Spec**

As a formal gating mechanism.

### **3. Your Engineering Doctrine**

As a lifecycle expectation (technical debt is part of design & maintenance).

**Without this, even perfect initial architecture eventually collapses under accumulated entropy.**

---

# **If you want, I can now produce:**

### 🟦 A **Technical Debt Enforcement Playbook**

(What reviewers must check, what tooling to set up)

### 🟥 A **Technical Debt Scanner** spec

(Policy-as-code scanning for common violations)

### 🟩 The **exact wording to paste into your Constitution**, written in “constitutional voice”

### 🟧 A **template for documenting technical debt** (`/technical_debt/README.md`)

Which one should I generate next?
