# Staged Strong Start Checklist (Reconciled)

This file is a strategic checklist spanning a broader multi-stack vision (Rust/Elixir + platform ops),
while current implementation work on this branch is Python-focused vNext.

Reconciled: 2026-02-19

Status legend:
- ✅ Complete in current repo/slice
- 🟡 Partially complete or implemented with different scope
- ⏳ Deferred backlog (not completed in current slice)

## Stage 1: Foundations

- ✅ Engineering doctrine present (`docs/ArqonBus/spec/engineering_doctrine.md`).
- ✅ Minimal SDD enforcement template present (`docs/ArqonBus/templates/github_pr_template.md`).
- 🟡 Protobuf usage is present (`src/arqonbus/proto/arqon.proto`), but centralized generation strategy is not documented as a single policy artifact.
- 🟡 State-machine governance exists in doctrine/template references, but a fully standardized Mermaid-only representation policy is not explicitly codified as a single source.
- ⏳ Rust/Elixir formatter+linter enforcement is not active in this Python CI profile.

## Stage 2: Testing and CI Hardening

- ✅ TDD scope is established for this slice via canonical phase tracking and suite taxonomy (`docs/ArqonBus/vnext_status.md`, `tests/conftest.py`).
- ✅ Unit test harness exists (`tests/unit/`).
- 🟡 Integration harness exists (`tests/integration/`, Redis service in CI), but not the full NATS+Valkey+Postgres container matrix listed in this original checklist.
- ✅ CI runs tests on PRs (`.github/workflows/arqonbus-tests.yml`).
- ⏳ `clippy`/`credo` strict enforcement is not active in this repo's current workflow.
- ⏳ Security/dependency scanning is not yet wired as a dedicated CI gate in the active workflow.

## Stage 3: Observability, Security, and Rollout

- ✅ Observability expectations/template exist in PR template and runbook references (`docs/ArqonBus/templates/github_pr_template.md`, `docs/runbook.md`).
- 🟡 Correlation data exists (`request_id`, `tenant_id` in envelope/auth/flows), but full end-to-end `trace_id`/`span_id` propagation is not fully codified in active tests.
- 🟡 Zero-trust baseline is partially implemented (JWT auth + role/tenant claims), but service-to-service auth model is not fully formalized here.
- ✅ Minimal role/permission behavior exists in command/auth flows (`src/arqonbus/security/jwt_auth.py`, `tests/unit/test_command_authorization.py`).
- ⏳ Canary deployment mechanism not yet implemented as an active release gate in this repo.
- 🟡 Rollback guidance exists in doctrine/runbook context, but not yet enforced as a tested one-command rollout primitive in CI.
- ⏳ First explicit numeric SLO (for example connect success rate target + budget gate) is not yet defined as a formal gating metric.

## Notes

- Current vNext implementation milestone status should be read from `docs/ArqonBus/vnext_status.md`.
- This checklist remains useful as governance backlog, but should not be interpreted as the sole completion source for the Phase0/Phase1 branch slice.
