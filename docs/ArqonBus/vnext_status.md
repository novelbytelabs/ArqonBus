# ArqonBus vNext Status (Single Source of Truth)

Last updated: 2026-02-18
Branch: `feature/vnext-phase0-phase1`
Program status: In Progress

## Why this file exists

This is the canonical status file for vNext execution. If any other document conflicts
with this file, this file wins until the conflicting document is updated.

## Scope Freeze (Phase 0)

Current implementation scope is frozen to Epoch 1:

- Shield gateway hardening (auth, policy gate, schema validation)
- Spine transport/routing reliability
- Protocol consistency and envelope contracts
- CASIL integration and operations safety

Out of scope for this freeze:

- Epoch 2 DevEx expansion work
- Epoch 3 Tier-Omega / substrate ambitions

## Program Milestones

| Milestone | Status | Notes |
| --- | --- | --- |
| M0: Baseline and truth alignment | Completed | Canonical status file and doc links aligned. |
| M1: Core Python stability pass | Completed | Dispatch/auth/http/websocket stabilization merged on branch. |
| M2: Test/Quality hardening gate | Completed | Unit/integration/e2e/regression + coverage/codecov wired. |
| M3: Epoch 2 Factory gate | Not Started | CLI/SDK/operator DX remains partial. |
| M4: Tier-Omega experimental lane | Not Started | Will remain feature-flagged and isolated. |

## Phase 0 Completion Checklist

- [x] Canonical vNext status file created
- [x] Scope freeze defined for Epoch 1
- [x] Contradictory status docs marked and aligned
- [x] Execution branch created from `dev`

## Phase 1 Completion Checklist

- [x] Dispatch regression fixes started
- [x] Operator registration auth behavior made configurable
- [x] High-risk TODOs in hot-path modules removed/closed
- [x] Test layers made explicit in pytest configuration
- [x] Optional Integriguard/RSI dependency paths gated
- [x] CI profile split committed (`core`, `integration`, `performance`)

## Validation Commands

Core stability checks:

```bash
python -m pytest -q tests/unit
python -m pytest -q tests/test_dispatcher.py tests/test_dispatch_integration.py tests/test_dispatch_e2e.py
```

Optional external checks:

```bash
python -m pytest -q -m external
python -m pytest -q tests/integration
python -m pytest -q -m performance
```

## Phase 2: Test and Coverage Hardening

- [x] Explicit suite taxonomy: `unit`, `integration`, `e2e`, `regression`
- [x] Regression tests added for Phase 1 bugfixes
- [x] CI split into unit/integration/e2e/regression jobs
- [x] Combined coverage gate with XML export
- [x] Codecov upload workflow + repository config

## Phase 3: Socket-Gated Test Reliability

- [x] Socket capability marker added (`socket`)
- [x] Runtime skip/fail policy added for socket-required tests
- [x] CI e2e job enforces socket capability (`ARQONBUS_REQUIRE_SOCKET_TESTS=1`)
- [x] Optional performance job enforces socket capability
- [x] Added unit tests for command authorization/admin/http transport behavior

## Phase 4: Monitoring + Deployment Polish (In Progress)

- [x] Added HTTP `/version` endpoint
- [x] Added HTTP request instrumentation wrapper (count, latency, errors)
- [x] Added unit tests for `/version` and tracked handler metrics/error paths
- [x] Added top-level docs runbook entrypoint (`docs/runbook.md`)
- [x] Fixed README/docs index links to canonical architecture/API/runbook docs
