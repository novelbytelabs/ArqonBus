# Tasks: Phase 1 – The Overseer (Wasm Host)

**Branch**: `004-epoch-2-platform`

| ID | Description | Owner | Status |
|----|-------------|-------|--------|
| 001 | Create `abi.rs` defining host functions (`host_get_header`, `host_log`, `host_reject`, etc.) and safety limits (fuel, memory). | Rust Engineer | [ ] Todo |
| 002 | Extend `engine.rs` to configure `wasmtime::Config` with fuel limits and load Wasm modules per tenant. | Rust Engineer | [ ] Todo |
| 003 | Implement middleware `wasm.rs` that invokes the policy engine for each incoming WebSocket request, handling allow/deny decisions. | Rust Engineer | [ ] Todo |
| 004 | Write unit tests for ABI functions and fuel exhaustion behavior. | QA Engineer | [ ] Todo |
| 005 | Add integration test verifying that a sample Wasm policy can reject a request with missing `X-Tenant-Token`. | QA Engineer | [ ] Todo |

**Next Steps**
- Review the tasks list.
- Once approved, start implementation of ID 001.
