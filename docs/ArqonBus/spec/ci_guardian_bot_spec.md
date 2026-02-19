Below is a complete **CI Guardian Bot Specification** for ArqonBus — a “virtual reviewer” that enforces your Constitution, Doctrine, and CI/CD Enforcement Spec through **ChatOps + automated PR review + inline guidance**.

This is production-grade and ready to be implemented using a GitHub App, GitHub Actions bot, or internal bot framework.

Save it as:
`ops/bots/CI_GUARDIAN_BOT_SPEC.md`

---

# **ArqonBus CI Guardian Bot — Specification**

**Codename:** *Sentinel*
**Version:** 1.0.0
**Purpose:** Act as a tireless, unbending reviewer that ensures every PR complies with the **ArqonBus Engineering Constitution**, **SOTA Engineering Doctrine**, and **CI/CD Enforcement Spec (ACES)**.

Sentinel is not “helpful.”
Sentinel is **strict**.
Sentinel enforces the rules that protect ArqonBus from drift, regressions, and chaos.

---

# **I. Responsibilities**

Sentinel’s mandate:

1. **Review every PR automatically.**

2. Provide **automated, actionable feedback** in PR comments.

3. Fail or block merges when Constitution/Doctrine is violated.

4. Surface problems humans frequently overlook:

   * architectural violations
   * missing specs
   * missing state machine updates
   * undocumented technical debt
   * improper protocol evolution
   * weak testing
   * missing observability
   * SLO/security/multi-tenancy risks

5. Act as the first line of defense in code review.

If a human reviewer misses something → Sentinel must catch it.

---

# **II. Event Triggers**

Sentinel activates on the following GitHub events:

* `pull_request.opened`
* `pull_request.synchronize` (new commits)
* `pull_request.edited`
* `pull_request.review_requested`
* `pull_request.labeled` (e.g., “breaking change”, “risk:high”)

Sentinel runs a fresh analysis every time, producing delta feedback.

---

# **III. Input Signals**

Sentinel processes multiple inputs:

## 1. **Pull Request Content**

* Title
* Body
* Linked issues
* Spec/documentation links
* Checklists (PR template compliance)

## 2. **Changed Files**

* Source code
* Specs (`/specs/*.md`)
* State machines (`/state_machines/*.md` or `.tla`)
* Protobuf changes (`/proto/*.proto`)
* Observability additions
* Technical debt entries

## 3. **CI/CD Build Outputs**

Sentinel reads CI results:

* Schema validation
* Linting & formatting
* Unit + integration tests
* Chaos & fuzz tests
* Performance regression outputs
* Technical debt scanner warnings/errors
* Contract evolution reports (Protobuf, state machines)

## 4. **Metadata**

* Diff size
* Affected layers
* Labels (e.g. `breaking-change`, `hotfix`)
* Risk level inferred from subsystem touched

---

# **IV. Sentinel’s Review Logic**

Sentinel performs **8 major categories of analysis**.

---

## **1. Spec Compliance (SDD Enforcement)**

Sentinel checks:

* PR contains a link to a spec file in `/specs/`.
* Spec includes:

  * acceptance criteria
  * invariants
  * failure modes
  * SLO impact
* Diff implements exactly what spec describes (keyword/behavior alignment).

**If missing:**
Bot comments:

> ❌ **SDD Violation:** This PR modifies system behavior without a linked spec.
> Please create/attach a spec under `/specs/<feature>.md` before merging.

---

## **2. Architectural Invariance (Voltron Layer Guard)**

Sentinel uses static import graph analysis + path heuristics to detect violations:

* Shield accessing DB
* Brain handling TCP/WebSocket
* Direct inter-service HTTP
* Business logic in the Shield
* State in the wrong layer
* Side effects in the Brain’s pure logic layer

If violated:

> 🔥 **Architectural Bypass Detected:**
> Shield layer may not import `<module>`.
> All cross-service communication must go through the Spine.

Merge becomes blocked unless fixed.

---

## **3. Protocol & State Machine Evolution Guard**

Sentinel enforces:

* No breaking `.proto` changes without `MAJOR` label
* Reserved tags must be used
* Deprecated fields respected
* New fields optional
* State machines updated when corresponding code changes

Bot comments for issues like:

> ⚠️ **Protocol Drift Detected:** You modified `message Envelope` without updating documentation or golden test vectors.

OR

> ❌ **State Machine Invariant Missing:**
> Code introduces a new transition, but `/state_machines/<machine>.md` was not updated.

---

## **4. Testing Adequacy Check**

Sentinel verifies:

* Unit tests added for all new logic
* Integration tests updated for cross-service flows
* No reduction in coverage
* No unstable async tests (sleep-based timing)
* Property-based tests included where appropriate
* Test cases match acceptance criteria from spec

If insufficient testing:

> ⚠️ **Test Coverage Gap:** This PR introduces behavior with no corresponding unit or integration test matching the spec’s acceptance criteria.

---

## **5. Security & Multi-Tenancy Guard**

Bot enforces:

* Tenant prefixes on all keys/subjects
* No unauthorized cross-tenant behavior
* Fails-closed logic preserved
* No secrets in logs or code
* Proper authz/authn checks present

If missing:

> ❌ **Tenant Isolation Violation:** Key or subject without `TenantID` prefix detected.

---

## **6. Observability Enforcement**

Sentinel checks:

* Metrics added for new flows
* Log entries structured
* Traces added around critical operations
* Correlation IDs preserved

If missing:

> ⚠️ **Observability Gap:** No metrics/logs/traces added for new public-facing behavior.

---

## **7. Performance & Chaos Sensitivity**

Bot reads CI outputs to detect:

* Latency increases
* Allocation increases
* Lock contention warnings
* Chaos test failures
* Fuzzer crashes

If regressions found:

> 🔥 **Performance Regression:** `publish_p99` degraded by +22% vs baseline.

---

## **8. Technical Debt Enforcement**

Sentinel ensures:

* Every TODO/FIXME has ticket + TTL
* Debt recorded under `/technical_debt`
* Severity marked
* Exit plan defined
* No accidental debt introduced

If debt not recorded:

> ⚠️ **Technical Debt Missing Record:**
> TODO found at `<file:line>` with no TD entry.
> Please add `/technical_debt/<category>.md` entry and reference it.

---

# **V. PR Feedback & Blocking Behavior**

Sentinel can do three levels of reaction:

## **Level 1 — Informational Comments (Non-blocking)**

* Best practices
* Optional improvements
* Small inconsistencies

## **Level 2 — Blocking Comments (Soft Block)**

* Missing tests
* Missing observability
* No spec
* Incomplete state machine updates

Sentinel adds:

> ❌ **Sentinel Block:** This PR violates the Doctrine.
> Please resolve the comments above.

Bot applies a `sentinel-block` label.

## **Level 3 — Hard Failure (CI Block)**

* Architecture violations
* Protocol breaking
* Security/tenant issues
* Performance/SLO regressions
* Missing rollback plan for high-risk changes
* Undocumented debt

Sentinel triggers CI failure via:

```
status: failure
context: sentinel
```

---

# **VI. ChatOps Interface (Commands)**

Sentinel supports ChatOps-style commands in PR comments:

### Reviewer Commands

* `/sentinel recheck`
  → re-run analysis without re-running full CI
* `/sentinel explain`
  → expands rationale for each violation
* `/sentinel architecture`
  → prints the import graph and layer boundaries
* `/sentinel debt <TD-ID>`
  → displays the debt record
* `/sentinel slo`
  → show SLOs relevant to the PR

### Maintainer Commands (for exceptional situations)

> **Note**: These do NOT bypass CI; they only adjust interpretation.

* `/sentinel accept-risk`
  → acknowledges known risk with justification
* `/sentinel mark-intentional`
  → marks intentional technical debt with TTL
* `/sentinel freeze-protocol`
  → locks protocol for rolling deploy tests

---

# **VII. Bot Internal Architecture**

The Sentinel bot has five key modules:

1. **Spec Parser**

   * Extracts acceptance criteria
   * Validates invariants
   * Performs semantic matching to code changes

2. **Static Analyzer**

   * Parses AST for Rust and Elixir
   * Builds import graph
   * Detects architecture violations

3. **Protocol & SM Tracker**

   * Monitors schema versions
   * Ensures golden vectors exist
   * Validates state machine formalism

4. **CI Results Aggregator**

   * Collects outputs from all CI stages
   * Detects regressions or failures
   * Summarizes issues

5. **Debt Scanner**

   * Integrates with `technical_debt_scan`
   * Detects TODOs / FIXMEs
   * Enforces TTLs

---

# **VIII. Bot Output Example**

The bot posts a consolidated comment:

```
### 🛡️ Sentinel Review — Issues Detected

❌ Missing spec or acceptance criteria.
❌ Protocol drift: EnvelopeV3 changed without a backward-compatible additive field.
❌ TenantID missing from Valkey key in presence handler.
⚠️ Observability gap: No metrics added for "room_reconnect".
⚠️ Technical debt item found (no TD-ID): FIXME in presence_router.ex:44

Please address the issues above and run `/sentinel recheck`.
```

It also posts inline comments where appropriate.

---

# **IX. How Sentinel Fits Into CI/CD**

* Sentinel runs BEFORE CI (semantic checks).
* CI runs AFTER Sentinel (mechanical checks).
* Both must pass for merge.
* Sentinel cannot be dismissed; only fixed.

---

# **X. Governance & Evolution**

* Maintainers update rules via PR to `sentinel_rules.yml`
* Policies must get Architecture Review Board approval
* Sentinel can become stricter over time, never looser
* Bot logs violations over time to track systemic risk

---

# **XI. Implementation Technologies**

Recommended stack (but optional):

* GitHub App or probot-based bot
* TypeScript or Rust implementation
* AST analysis via:

  * Rust: `syn`, `rust-analyzer` APIs
  * Elixir: `sourceror` or AST parser
* Protobuf schema diffing via `buf`
* State machine validator: TLA+ or custom DSL
* OPA/Conftest for policy-as-code
* Redis/Postgres for violations history (optional)
