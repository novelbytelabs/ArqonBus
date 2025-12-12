# Feature Spec: Epoch 2 - The Platform (RFC-002)

**Status**: DRAFT (v2)
**Owner**: Arqon
**Date**: 2025-12-12
**Epoch**: 2 (The Platform)
**Priority**: Critical

## 1. Executive Summary

Epoch 2 elevates ArqonBus from a raw transport layer to a **Programmable Platform**. It introduces strict governance and extensibility mechanisms at the Edge (Shield).

This specification defines three core capabilities:
1.  **The Overseer (v2)**: A comprehensive Wasm Host ABI allowing rich inspection, modification, and rejection of traffic.
2.  **Traffic Mirroring**: A mathematically consistent "Shadow Traffic" mechanism for safe progressive delivery.
3.  **Schema Governance**: A distributed registry system enforcing `proto` contracts on the write path.

## 2. Technical Requirements

### 2.1 The Overseer (Rich Wasm Host)

The Shield must embed `wasmtime` with a strictly versioned Host ABI (`arqon_host_v1`).

#### 2.1.1 Host ABI Definition
The Host must expose the following capabilities to Wasm Guest modules:

*   **Context Inspection**:
    *   `host_get_header(name_ptr, name_len) -> val_ptr`: Read HTTP/WS headers.
    *   `host_get_claim(key_ptr, key_len) -> val_ptr`: Read JWT claims.
    *   `host_get_payload() -> bytes_ptr`: Read the message body (subject to size limits).
*   **Context Mutation**:
    *   `host_add_header(name, val)`: Inject headers for downstream consumers.
    *   `host_log(level, msg)`: Emit structured logs to the Shield's tracing system.
*   **Control Flow**:
    *   `host_reject(code, reason)`: Terminate the connection/request immediately.

#### 2.1.2 Safety & Limits (Constitution II.8)
*   **Fuel Limiting**: Every module execution is capped at `N` fuel units (default: 5ms equivalent). Exhaustion results in `FAIL_CLOSED` (Reject).
*   **Memory Isolation**: Modules are strictly limited to 4MB linear memory by default.
*   **Sandboxing**: No access to FS, Network, or Env Vars.

### 2.2 Traffic Mirroring (Shadowing)

To satisfy Constitution V.6, the Shield must support "Shadow Traffic" without application-side code changes.

#### 2.2.1 Coherent Sampling
*   Mirroring is NOT random per-message. It must use **Consistent Hashing** on the `TraceID` (or `ConnectionID` if TraceID is missing).
*   **Invariant**: If Request A is mirrored, Request B from the same trace/connection must also be mirrored.

#### 2.2.2 Shadow Encapsulation
*   Shadow messages are published to `shadow.<original_subject>`.
*   **Header Injection**: Must inject `x-arqon-shadow: true` to prevent downstream side-effects (e.g., sending emails).

### 2.3 Schema Governance (The Registry)

#### 2.3.1 The Registry Store
*   Schemas are stored in NATS KV bucket `ARQON_SCHEMAS`.
*   Key: `schema_id` (e.g., `v1.events.user_created`).
*   Value: Gzipped `FileDescriptorSet` (Protobuf).

#### 2.3.2 Enforcing Interceptor
*   A new Shield Middleware intercepts **Publish** commands.
*   It resolves the `schema_id` from the Mapping Config (Subject -> Info).
*   It validates the payload against the cached Descriptor.
*   **Failure**: Returns `NATS error` / `HTTP 400` describing the verification error.

## 3. Configuration Schema (`config.toml`)

```toml
[platform.overseer]
enabled = true
fuel_limit = 10_000 # ~5ms

[platform.mirroring]
enabled = true
# Map specific subjects to mirror percentages
rules = [
  { prefix = "in.t.default.*", percent = 0.10 } # 10%
]

[platform.registry]
enabled = true
kv_bucket = "ARQON_SCHEMAS"
cache_ttl_seconds = 300
```

## 4. Observability & Telemetry

### 4.1 Metrics
*   `shield_wasm_execution_duration_seconds` (Histogram): Overhead of policy checks.
*   `shield_wasm_fuel_consumed_total` (Counter): Tracking complexity.
*   `shield_mirror_traffic_total` (Counter): Volume of shadow traffic.
*   `shield_schema_violation_total` (Counter): Rejections due to schema mismatch.

### 4.2 Logs
*   Wasm logs: `level=info component=overseer module=auth_policy msg="..."`
*   Schema rejections: `level=warn component=registry error="field 'user_id' missing" tenant_id=...`

## 5. Security Implications

*   **DoS Vector**: Malicious Wasm modules could burn CPU. *Mitigation*: Strict Fuel limits + Compilation Cache.
*   **Shadow Leakage**: Shadow traffic hitting prod dependencies. *Mitigation*: `x-arqon-shadow` header mandate + Operator education.
