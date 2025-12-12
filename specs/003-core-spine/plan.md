# System Design Document: The Core Spine (Epoch 1)

**Branch**: `003-core-spine` | **Date**: 2025-12-11 | **Status**: APPROVED FOR EXECUTION
**Reference**: [Constitution v2.2](../../.specify/memory/constitution.md)

---

## 1. Executive Summary

This document defines the architecture for **Epoch 1: The Core Spine**. It is not merely a task list; it is the **Technical Contract** for the implementation.

We are building a **Voltron Architecture** system:
1.  **Shield (Rust)**: Stateless, high-concurrency Edge Gateway (WebSocket -> NATS).
2.  **Spine (NATS)**: The central nervous system for message durability and routing.
3.  **Brain (Elixir)**: The stateful control plane for Presence, Room Lifecycle, and Orchestration.
4.  **Overseer (Wasm)**: The safety policy engine executing at the Edge.

**Key Constraint**: The system must operate with **O(1) Hot Paths** and **Zero-Allocation Routing** in the Shield, while maintaining **Causal Consistency** for Room State in the Brain.

---

## 2. API Contract (The Protocol)

The system is defined by its data structures. We prioritize **Protobuf v3** for all internal communication.

### 2.1 The Envelope (Wire Format)
*File: `crates/proto/src/envelope.proto`*

```protobuf
syntax = "proto3";
package arqon.v1;

message Envelope {
  // Routing Headers (Unencrypted, Mutable by Router)
  string trace_id = 1;      // W3C Trace Context
  string tenant_id = 2;     // Extracted from JWT
  string room_id = 3;       // Target Room
  int64 timestamp = 4;      // Wall clock (ms)

  // Security Headers (Signed/Immutable)
  bytes signature = 10;     // Ed25519 signature of payload

  // The Payload (Opaque to Router)
  oneof payload {
    Command cmd = 20;
    Event event = 21;
    SystemSignal signal = 22; // Control plane (Disconnect, Ban)
  }
}
```

### 2.2 System OpCodes (WebSocket)
The WebSocket protocol (Client <-> Shield) uses a strict OpCode header byte:
*   `0x01` **PUB**: Publish Envelope (Binary)
*   `0x02` **SUB**: Subscribe to Room (Text/JSON for now, moving to Bin)
*   `0x09` **ACK**: Acknowledgement (if `ack_requested=true`)
*   `0x99` **ERR**: Error with Code (Binary: `[u16 code][utf8 message]`)

---

## 3. Component Architecture

### 3.1 The Shield (Rust)
**Responsibility**: Validation, Termination, Inspection.
**Constraint**: No heap allocation for valid messages in the hot loop.

#### Reactor Design (Tokio)
*   **TcpListener**: Spawns a `ConnectionHandler` task per socket.
*   **ConnectionHandler**:
    1.  Owns a `SplitStream` (WebSocket Read/Write).
    2.  Holds a read-lock on `PolicyEngine` (Wasmtime).
    3.  Holds a clone of `NatsClient`.
*   **The Hot Loop**:
    ```rust
    while let Some(msg) = socket.read().await {
        let envelope = Envelope::decode(&msg)?; // Stack allocated if possible
        policy_engine.validate(&envelope)?;     // Wasm Hook (Fail Closed)
        nats.publish(subject, envelope).await?; // Subject = "t.{tenant}.r.{room}"
    }
    ```

#### Crate Structure
*   `crates/shield`: The Axum/Tokio binary.
*   `crates/policy`: The Wasmtime host engine + caching logic.
*   `crates/voltron-core`: Shared traits, Config schema, and Tracing setup.

### 3.2 The Brain (Elixir)
**Responsibility**: State, Presence, Orchestration.
**Constraint**: Global consistency for Room Membership.

#### Supervision Tree
```mermaid
Application
├── Phoenix.PubSub (Local Bus)
├── LibCluster (Mesh Discovery)
├── Brain.Presence (Tracker)
└── Brain.RoomManager (DynamicSupervisor)
    ├── Brain.Room: "tenant_a:room_1"
    └── Brain.Room: "tenant_a:room_2"
```

#### State Management
*   **Presence**: We use `Phoenix.Tracker` (Delta-CRDT) to sync "Who is Here" across the cluster.
*   **Room GenServer**: Holds the "Truth" for a room (e.g., current playlist, lock status). It subscribes to NATS `t.{tenant}.r.{room}.cmds`.

### 3.3 The Spine (NATS)
**Responsibility**: Delivery & Decoupling.

#### Subject Taxonomy
Strict hierarchical subjects enforce isolation:
*   `in.t.{tenant}.r.{room}`: Ingress (Shield -> Brain)
*   `out.t.{tenant}.r.{room}`: Egress (Brain -> Shield -> Client)
*   `sys.t.{tenant}.*`: Control signals (e.g., "Ban User")

---

## 4. Operational Manifesto

### 4.1 Observability (The Dashboard)
We define the **Golden Signals** that must be visible in Grafana from Day 1.

| Metric | Type | Source | Description |
| :--- | :--- | :--- | :--- |
| `shield_active_connections` | Gauge | Rust | Current socket count per node. |
| `shield_ingress_ops` | Counter | Rust | Rate of messages received from clients. |
| `policy_execution_duration` | Histogram | Rust | Latency of Wasmtime execution (Target < 2ms). |
| `brain_room_count` | Gauge | Elixir | Number of active room GenServers. |
| `consistency_convergence_lag` | Gauge | Elixir | Time for CRDTs to settle. |

### 4.2 Configuration Schema
Strict TOML configuration. No magic environment variables.

```toml
[server]
host = "0.0.0.0"
port = 4000

[nats]
urls = ["nats://127.0.0.1:4222"]

[policy]
timeout_ms = 5
fail_closed = true
```

---

## 5. Implementation Roadmap (Phased)

### Phase 1: The Skeleton (Days 1-2)
*   [ ] Initialize Polyglot Repo (Rust Workspace + Elixir App).
*   [ ] Set up CI/CD Pipeline (The Factory).
*   [ ] Define `proto` definitions and generation build scripts.

### Phase 2: The Nervous System (Days 3-4)
*   [ ] **Shield**: Implement WebSocket ingest + NATS publish.
*   [ ] **Brain**: Implement NATS subscribe + Logging consumer.
*   [ ] **Test**: Verify `wscat` -> Shield -> NATS -> Brain -> Logs.

### Phase 3: State & Safety (Days 5-6)
*   [ ] **Brain**: Implement Presence CRDTs.
*   [ ] **Shield**: Integrate Wasmtime for Policy Hooks.
*   [ ] **Test**: Run `load_test.js` (k6) to verify 100k connection stability.

### Phase 4: The Product Wrapper (Day 7)
*   [ ] Build `arq` CLI tool.
*   [ ] Publish Python SDK.
*   [ ] Checkpoint: "Professional Preview" Release.

---

## 6. Definition of Done

1.  **Repo**: Clean, linted, with no `TODO`s in critical paths.
2.  **Coverage**: >80% code coverage on Shield Policy and Brain State.
3.  **Perf**: P99 Latency < 10ms for Message Echo loop at 10k ops/sec.
4.  **Docs**: `epoch1_overview.md` updated with "As Built" architecture.
