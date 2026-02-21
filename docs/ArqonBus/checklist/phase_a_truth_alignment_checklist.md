# Phase A Truth Alignment Checklist

Last updated: 2026-02-19  
Branch: `dev/vnext-innovation-execution`

## Scope

Close the documentation/evidence gap before feature expansion, and lock execution rules for Rust 1.82 plus full test coverage categories.

## Checklist

- [x] Create a canonical vNext innovation execution plan.
  - Evidence: `docs/ArqonBus/plan/vnext_innovation_execution_plan.md`
- [x] Create requirement-to-test traceability matrix.
  - Evidence: `docs/ArqonBus/plan/phase_a_requirement_test_traceability.md`
- [x] Classify each requirement as `GREEN`/`AMBER`/`RED` with factual evidence.
- [x] Define hard merge gate: no innovation merge without `U + I + E2E + R` coverage for changed surfaces.
- [x] Pin Rust toolchain to `1.82.x` in-repo and align CI toolchain.
  - Evidence: `rust-toolchain.toml`, `.github/workflows/ci-rust.yml`
- [x] Add CI guard to fail when Rust toolchain drifts from `1.82.x`.
  - Evidence: `.github/workflows/ci-rust.yml` ("Verify rust-toolchain pin matches CI toolchain")
- [ ] Add CI guard that fails if a changed high-risk module lacks at least one test in each required suite category.
- [x] Create explicit Phase B test task list for Shield (`auth`, `schema`, `wasm`, `NATS`, `tenant isolation`).
  - Evidence: `docs/ArqonBus/checklist/phase_b_shield_test_task_list.md`
- [x] Create explicit Phase C test task list for protocol/time (`protobuf contract`, `sequence`, `vector clocks`, `history.get replay`).
  - Evidence: `docs/ArqonBus/checklist/phase_c_protocol_time_test_task_list.md`
- [x] Create explicit Phase D test task list for modularization parity (`operator pack`, `omega lane`, `SAM handshake`).
  - Evidence: `docs/ArqonBus/checklist/phase_d_modularization_test_task_list.md`
- [ ] Link this checklist from `docs/ArqonBus/vnext_status.md` after Phase A signoff.

## Hard Rules (Effective Immediately)

- Rust core runtime work targets `Rust 1.82.x`.
- For each high-risk change, add and pass:
  - Unit tests
  - Integration tests
  - End-to-end tests
  - Regression tests
