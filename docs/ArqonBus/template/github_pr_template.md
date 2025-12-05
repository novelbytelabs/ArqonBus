# ArqonBus Pull Request

> ⚖️ This PR must comply with the **ArqonBus Engineering Constitution** and the **SOTA Engineering Doctrine**.
> If a change conflicts with the constitution/doctrine, the change is wrong.

---

## 1. Overview

**What does this PR do, in one or two sentences?**

- 

**Which part(s) of the Voltron architecture does it touch?**

- [ ] Shield (Edge)
- [ ] Spine (Bus)
- [ ] Brain (Control)
- [ ] Storage (State)
- [ ] Shared Libraries / Tooling
- [ ] Other:

---

## 2. Linked Spec (SDD)

**Spec / Design Doc(s):**

- [ ] Spec exists in `/specs/` and is linked here  
  Link(s): 

**Does this PR fully implement the behavior described in the spec?**

- [ ] Yes  
- [ ] Partially (explain what’s deferred):

> If there is no spec, this PR is not ready.

---

## 3. State Machines & Protocol

**State Machines:**

- Does this PR change or introduce a state machine?
  - [ ] No  
  - [ ] Yes → Updated diagrams/specs in `/state_machines/`  
    - [ ] All new/changed transitions are documented  
    - [ ] Invariants are documented and enforced in code

**Protocol / Protobuf:**

- Does this PR change `.proto` files or public protocol?
  - [ ] No  
  - [ ] Yes → Schema changes in `/proto/`  
    - [ ] Only additive changes (MINOR)  
    - [ ] Breaking change (requires MAJOR bump)  
    - [ ] Deprecated fields are marked and documented

**Golden Test Vectors:**

- [ ] Added/updated golden test vectors for new/changed messages

---

## 4. Invariants & Guarantees

**What invariants does this PR rely on or introduce?**  
(e.g., “Presence cannot exist without a room”; “TenantID must be present in every subject/key”)

- 

**How are these invariants enforced?**  
(check all that apply)

- [ ] Type system / encoding
- [ ] State machine logic
- [ ] Validation at boundaries
- [ ] Unit tests
- [ ] Property-based tests
- [ ] Integration tests

---

## 5. SLO & Risk Impact

**SLOs potentially affected:**

- [ ] Connect Latency
- [ ] Publish Latency
- [ ] Message Delivery Reliability
- [ ] Presence Correctness
- [ ] Tenant Isolation
- [ ] Control Plane Availability
- [ ] Other:

**Impact type:**

- [ ] No expected SLO impact  
- [ ] Improves SLOs (explain):  
- [ ] May risk SLOs (explain + mitigation):

**Risk level:**

- [ ] Low  
- [ ] Medium  
- [ ] High (requires explicit maintainer sign-off)

---

## 6. Security & Multi-Tenancy

**Security:**

- Does this PR touch auth, authz, or safety logic (Wasm, Overseer, Zero Trust)?
  - [ ] No  
  - [ ] Yes (explain changes and threat model updates):

- Security checklist:
  - [ ] No secrets in code, logs, or config
  - [ ] Inputs are validated at trust boundaries
  - [ ] New capabilities/roles documented
  - [ ] Fails **closed** on security/safety module failure

**Multi-Tenancy:**

- Does this PR touch tenant-scoped data or routing?
  - [ ] No  
  - [ ] Yes (explain):

- Tenant isolation checklist:
  - [ ] Every NATS subject, key, and row uses `TenantID`
  - [ ] No wildcard subscriptions cross tenant boundaries
  - [ ] No shared global mutable state across tenants

---

## 7. Observability (OFD)

For any new user/tenant-visible behavior:

- [ ] Metrics added/updated  
  - Names (e.g. `arqonbus.gateway.connect_success_total`):  
- [ ] Structured logs added/updated (no PII, no secrets)  
- [ ] Traces/spans added around critical operations  
- [ ] Correlation IDs (trace_id, span_id, TenantID, RequestID) correctly propagated

How will we **observe** that this PR behaves correctly in staging/production?

- 

---

## 8. Testing

**Unit Tests:**

- [ ] Added/updated unit tests
- [ ] Covers new logic, edge cases, and invariants

**Integration Tests:**

- [ ] Added/updated integration tests involving:
  - [ ] Shield ↔ Spine ↔ Brain ↔ Storage
  - [ ] Multi-tenant behavior
  - [ ] Failure modes (timeouts, partial outages)

**Adversarial / Chaos / Property-Based:**

- [ ] Fuzz tests for parsers/handlers updated
- [ ] Flood/overload scenarios covered
- [ ] Property-based tests (where applicable)

**Manual Testing (if any):**

- 

---

## 9. Technical Debt

Does this PR **introduce** technical debt?

- [ ] No  
- [ ] Yes → Recorded in `/technical_debt/` and issue tracker

If **Yes**:

- Debt ID(s): `TD-XXX`  
- Type(s): Protocol | State Machine | Concurrency | Security | Observability | Tooling/Infra | Other  
- Severity: Critical | High | Medium | Low  
- TTL (fix-by date):  

Why is this debt justified now, and what is the exit plan?

- 

Does this PR **pay down** existing debt?

- [ ] No  
- [ ] Yes → Linked TD item(s) resolved:  

---

## 10. Deployment & Rollback

**Deployment considerations:**

- [ ] No special considerations  
- [ ] Requires data migration  
- [ ] Requires configuration changes  
- [ ] Requires coordination across services

**Safety nets:**

- [ ] Canary plan defined  
- [ ] Shadow traffic plan (if applicable)  
- [ ] Rollback is documented and tested

If something goes wrong, **how do we know**, and **how do we roll back safely**?

- 

---

## 11. Checklist (Must Pass Before Merge)

Author:

- [ ] I confirm this change adheres to the ArqonBus Engineering Constitution.
- [ ] I have linked and updated the relevant spec(s).
- [ ] I have updated state machines and/or protocol definitions as needed.
- [ ] I have added/updated tests and they pass locally.
- [ ] I have considered security, multi-tenancy, and observability impact.
- [ ] I have documented any technical debt introduced.

Reviewer:

- [ ] Spec matches implementation.
- [ ] No architectural layer violations (Voltron pattern respected).
- [ ] No stealth protocol or API breaking changes.
- [ ] Tests and CI status are green.
- [ ] SLO, security, and tenant isolation impacts are acceptable.
- [ ] Any technical debt is intentional, documented, and time-bounded.

Maintainer (for high-risk/critical changes):

- [ ] Approved after reviewing SLO impact, rollback plan, and risk profile.

---
