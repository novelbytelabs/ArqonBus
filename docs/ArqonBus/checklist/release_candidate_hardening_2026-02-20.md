# ArqonBus Release Candidate Hardening (2026-02-20)

## Scope

- Protocol/time command-lane closure for `history.get` + `history.replay`
- Performance gates for protobuf encode/decode and replay latency
- Final CI matrix alignment for performance suite execution

## Completed Hardening Items

- [x] Implemented command-lane handlers:
  - `op.history.get` (`history.get` alias)
  - `op.history.replay` (`history.replay` alias)
- [x] Enforced fail-closed history access policy:
  - non-admin must scope to `room`
  - global history queries are admin-only
- [x] Added unit coverage for history command lane:
  - `tests/unit/test_history_command_lane.py`
- [x] Added websocket e2e protobuf contract coverage for history command lane:
  - `tests/integration/test_history_command_e2e.py`
- [x] Added performance latency gates:
  - `tests/performance/test_replay_protobuf_latency_gates.py`
- [x] Updated performance CI selector to include all performance gates:
  - `.github/workflows/arqonbus-tests.yml`

## Verification Commands

```bash
conda run -n helios-gpu-118 python -m pytest -q \
  tests/unit/test_history_command_lane.py \
  tests/integration/test_history_command_e2e.py \
  tests/performance/test_replay_protobuf_latency_gates.py

conda run -n helios-gpu-118 python -m pytest -q \
  tests/unit/test_ids_validation.py \
  tests/unit/test_timekeeper_sequence.py \
  tests/unit/test_vector_clock.py \
  tests/unit/test_history_command_lane.py \
  tests/integration/test_history_get_replay.py \
  tests/integration/test_json_adapter_compat.py \
  tests/integration/test_proto_contract_crosslang.py \
  tests/integration/test_time_ordering_e2e.py \
  tests/integration/test_history_replay_e2e.py \
  tests/integration/test_history_command_e2e.py \
  tests/regression/test_time_envelope_regressions.py \
  tests/regression/test_proto_json_adapter_regressions.py \
  tests/regression/test_proto_evolution_regressions.py

conda run -n helios-gpu-118 python scripts/ci/check_protobuf_first.py
```

## Final CI Matrix (RC)

- Unit: `unit and not regression and not e2e and not external and not performance`
- Integration: `integration and not e2e and not external and not performance`
- E2E: `e2e and not external and not performance`
- Regression: `regression and not external and not performance`
- Protobuf Contract: protobuf-first policy script + Python/Rust contract tests
- Performance: `performance and not external`
