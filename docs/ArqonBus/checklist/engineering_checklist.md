# Staged Strong Start Checklist

Here’s how to **actually get this moving** without boiling the ocean.

### Stage 1: Foundations

* [ ] Create `ENGINEERING_DOCTRINE.md` (basically this doc) in the repo.
* [ ] Define minimal SDD template (one-pager) and require it for any new feature.
* [ ] Choose and standardize:

     * [ ] Protobuf repo + generation strategy
     * [ ] State machine representation format (Mermaid)

* [ ] Enforce formatter + linter in CI (Rust + Elixir).

### Stage 2: Testing & CI Hardening

* [ ] Define TDD scope: which parts *must* be TDD’d.
* [ ] Add:

     * [ ] Unit test harness
     * [ ] Integration test harness (NATS, Valkey, Postgres containers)

* [ ] Extend CI to:

     * [ ] Run tests on every PR
     * [ ] Run `clippy`/`credo` with strict configs
     * [ ] Run security/dependency scans

### Stage 3: Observability, Security, and Rollout

* [ ] Add a **standard metric/log/trace template** for new features.
* [ ] Implement **correlation IDs** (TenantID, RequestID) end-to-end.
* [ ] Define zero-trust baseline:

     * [ ] Service-to-service authentication method
     * [ ] Minimal roles & permissions schema

* [ ] Implement a basic:

     * [ ] Canary deploy mechanism
     * [ ] Rollback script / process
  
* [ ] Write the first **SLO** (e.g., “WebSocket connect success rate”).

When those are in place, you’ve gone from “aspirational SOTA” to **practically enforceable doctrine**.