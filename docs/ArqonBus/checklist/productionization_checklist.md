# Productionization Checklist

Last updated: 2026-02-19  
Owner: ArqonBus maintainers  
Source plans:

- `docs/ArqonBus/plan/production_readiness_assessment.md`
- `docs/ArqonBus/plan/productionization_execution_plan.md`

## Phase 0: Baseline Lockdown

- [x] Remove runtime package shadowing from `src/aiohttp/**`.
- [x] Ensure HTTP server imports real `aiohttp` dependency path.
- [x] Fix runtime dependency mismatch for `dotenv` (`pyproject.toml` and install tests).
- [x] Add startup preflight for required environment config.
- [x] Validate clean install/import in `helios-gpu-118`.

## Phase 1: Security Hardening

- [x] Remove default JWT secret fallback from Shield production path.
- [x] Disable skip-validation outside test profile.
- [x] Add regression tests for fail-closed auth startup and token checks.
- [x] Re-run `cargo check -p shield` and `cargo test -p shield --tests`.

## Phase 2: Storage Durability Hardening

- [x] Add explicit `strict`/`degraded` storage mode.
- [x] Make Redis unavailability fail startup in `strict` mode.
- [x] Emit explicit degraded health signals in `degraded` mode.
- [x] Add integration tests for both modes.

## Phase 3: Runtime Integrity

- [x] Remove or hard-gate prototype operator logic from production paths.
- [x] Replace silent exception swallows in hot loops with structured handling.
- [x] Add regression tests for no-silent-failure guarantees.

## Phase 4: Deployment Hardening

- [x] Remove hardcoded bind/port defaults in runtime entrypoints.
- [x] Validate environment profile behavior (`dev`, `staging`, `prod`).
- [x] Ensure docs and runbooks reflect final config contract.

## Phase 5: Final Validation

- [x] Unit tests pass.
- [x] Integration tests pass.
- [x] End-to-end tests pass.
- [x] Regression tests pass.
- [x] Adversarial tests pass.
- [x] CI pipeline green with productionization gates enabled.

## Release Gate

- [ ] No production-path stubs/mocks/placeholders remain.
- [ ] No auth bypass toggles available in production profile.
- [ ] No silent durability downgrade in strict profile.
- [ ] Runbook approved and exercised once end-to-end.
