# ArqonBus vNext - Master Product Requirements Document (PRD)

| Metadata | Details |
| :--- | :--- |
| **Document ID** | **SPEC-000-MASTER** |
| **Version** | 1.0.0-DRAFT |
| **Status** | **DRAFT** |
| **Owner** | Product Engineering (NovelByte Labs) |
| **Last Updated** | 2025-12-09 |
| **Classification** | **CONFIDENTIAL** |

---

## 1. Executive Summary

**ArqonBus vNext** is the "Universal Computational Substrate" designed to bridge the gap between digital microservices and physical/emergent computing. Unlike traditional message buses (Kafka, NATS) which treat messages as passive data, ArqonBus treats messages as **Causal Pulses** that drive state transitions in a rigorously defined "Reality."

It unifies **High-Performance Transport** (WebSockets/Protobuf), **Programmable Safety** (Wasm-based CASIL), and **Emergent Physics** (Time-Travel, Interference, Criticality) into a single "Voltron" architecture. This allows Human Users, AI Agents, and Physical Rigs (NVM, BowlNet) to coexist as first-class citizens on the same coordinating fabric.

### 1.1 The "Why"
*   **The Problem:** Current infrastructure isolates "Production Services" from "Research Experiments." Moving an AI Agent from a Jupyter Notebook (Research) to a live cluster (Production) requires a complete rewrite of the plumbing.
*   **The Solution:** ArqonBus provides a consistent **Operator Interface**. An agent written for a local simulation runs unmodified on the production bus, because the "Physics" of the bus (Time, Identity, Messaging) are identical in both environments.

---

## 2. Scope & Definitions

### 2.1 In Scope
1.  **The Spine (Kernel):** The core Rust-based message bus managing TCP/QUIC/WebSocket connections, routing, and subscription trees.
2.  **Tier-1 Operators:** Standard infrastructure operators (Gateway, Auth, Storage, Presence).
3.  **Tier-Ω Hosting:** The runtime environment for "Emergent" operators (NVM, Primes, ERO, BowlNet) via Wasm sandboxing or Native Proxies.
4.  **CASIL (Safety):** The Content-Aware Safety & Inspection Layer, enforcing policy at the edge.
5.  **TTC (Time):** The Temporal Consistency protocols (Vector Clocks, BFT Time) ensuring causal ordering.

### 2.2 Out of Scope
1.  **Model Training:** ArqonBus routes interference jobs *to* GPUs, but is not a CUDA trainer itself.
2.  **UI Frameworks:** We provide the SDKs; the User Interface is the client's responsibility.
3.  **Physical Hardware Drivers:** We define the `IOperator` interface; the specific USB/Serial drivers for a BowlNet rig are part of the *Operator Implementation*, not the Bus Kernel.

### 2.3 Terminology
| Term | Definition |
| :--- | :--- |
| **Pulse** | A discrete, causally-ordered event message. The fundamental atom of time. |
| **Operator** | An autonomous actor (Service, Agent, or Function) connected to the bus. |
| **Reality** | A named scope (Namespace) with defined "Laws of Physics" (Time, Consistency, Permissions). |
| **Substrate** | The underlying medium an Operator manipulates (e.g., NVM Grid, Prime Field). |
| **Trajectory** | The verified path of a sequence of Pulses through spacetime. |
| **CASIL** | Content-Aware Safety & Inspection Layer (The "Police" of the bus). |

---

## 3. User Personas & Stories

### 3.1 Personas
*   **Alice (Researcher):** Works in Jupyter. Wants to sweep parameters on an NVM rig without deploying servers.
*   **Bob (Platform Eng):** Cares about latency, uptime, and preventing Alice from crashing the production cluster.
*   **Omega (Agent):** An AI Construct. Needs high-bandwidth low-latency state synchronization to coordinate with swarms.

### 3.2 User Stories
*   **[US-01] NVM Job Dispatch:** As **Alice**, I want to submit a `job.nvm` payload via Python SDK and receive a streaming result, so I can run physics experiments from my laptop.
*   **[US-02] Hybrid Circuit:** As **Bob**, I want to define a "Circuit" where data flows `Audio -> BowlNet -> Features -> QML -> Class`, ensuring type safety at each hop.
*   **[US-03] Safety Sandbox:** As **Bob**, I want to enforce a Wasm policy that blocks any `job.nvm` requesting > 50 Joules of energy, preventing hardware damage.
*   **[US-04] Time Travel:** As **Alice**, I want to replay yesterday's "Reality" with a different parameter set ($k_c$) to see if the system diverges.
*   **[US-05] Agent Swarm:** As **Omega**, I want to publish my internal `coherence_metric` to the swarm every 10ms with minimal overhead (<1ms).

---

## 4. Functional Requirements (FR)

### 4.1 Transport & Connectivity (FR-CORE)
*   **FR-CORE-01:** The System SHALL accept connections via Secure WebSockets (`wss://`) and TCP.
*   **FR-CORE-02:** The System SHALL enforce **TLS 1.3** for all non-local connections.
*   **FR-CORE-03:** The System SHALL implement **Backpressure**. If a consumer is slow, the bus MUST buffer up to a configured limit, then drop packets (shed load) or disconnect the client, signaling the event via metrics.

### 4.2 Messaging Protocol (FR-MSG)
*   **FR-MSG-01:** All control and data plane traffic MUST use **Protocol Buffers (Protobuf)** as the wire format.
*   **FR-MSG-02:** The Message Envelope MUST contain: `MessageID` (UUIDv7), `Timestamp` (UTC), `ProducerID`, `RealityID`, `TraceID`, and `Payload` (Any).
*   **FR-MSG-03:** The System SHALL support **Differential Messaging** (Delta Encoding). Operators MAY declare a topic as `delta_only`, requiring subscribers to reconstruct state.

### 4.3 Operator Runtime (FR-OPS)
*   **FR-OPS-01:** The System SHALL serve as a host for **Wasm Operators**. The runtime MUST strictly cap Memory (Pages) and CPU (Instruction Count/Gas).
*   **FR-OPS-02:** The System SHALL support **Native Proxies**. A standardized sidecar (Go/Rust) MUST be provided to bridge legacy HTTP/gRPC services onto the bus.
*   **FR-OPS-03:** The System SHALL implement the **SAM Interface** (Standard Agent Model). Operators must report `Capabilities`, `InputSchema`, and `OutputSchema` on handshake.

### 4.4 Temporal Physics (FR-TIME)
*   **FR-TIME-01:** The System SHALL act as the **Timekeeper**. Messages MUST be stamped with a strictly monotonic sequence number within their Reality.
*   **FR-TIME-02:** The System SHALL support **Vector Clocks** for causal ordering across partitioned operators.
*   **FR-TIME-03:** Access to historical streams MUST be provided via a standard `history.get` API, allowing strict time-bounded replay.

### 4.5 Safety & Governance (FR-SAFE)
*   **FR-SAFE-01:** The **CASIL Middleware** MUST inspect every message at the Edge (Shield Layer).
*   **FR-SAFE-02:** Policy execution MUST be **Fail-Closed**. If the policy engine crashes or times out, the message is BLOCKED.
*   **FR-SAFE-03:** The System MUST maintain an **Audit Log** of every Governance Action (e.g., Operator Promotion, User Ban), stored in immutable storage.

### 4.6 Emergence Engineering (FR-EMERG)
*   **FR-EMERG-01:** The System SHALL expose **Spectral Metadata** (e.g., `eigenvalue_spectrum`, `coherence_score`) as first-class header fields for Tier-Ω messages.
*   **FR-EMERG-02:** The System SHALL support **Control Parameter Tuning**, allowing authorized Controllers to broadcast global parameter updates (e.g., `set_coupling_k`) to all subscribers in a Reality.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Performance (SLAs)
*   **NFR-PERF-01:** **Latency:** End-to-end delivery (Producer -> Bus -> Consumer) SHALL be **< 5ms** at p99 for local clusters.
*   **NFR-PERF-02:** **Throughput:** A standard 3-node cluster SHALL support **> 100,000 TPS** (1KB payloads).
*   **NFR-PERF-03:** **Connection Density:** A single node SHALL support **> 50,000** concurrent idle connections.

### 5.2 Reliability
*   **NFR-REL-01:** **Determinism:** Replaying an Input Log through the System Config MUST produce the bit-exact same Output Log.
*   **NFR-REL-02:** **Isolation:** One Tenant crashing/flooding SHALL NOT impact the performance of another Tenant (Bulkhead Pattern).

### 5.3 Security
*   **NFR-SEC-01:** **Zero Trust:** Every component (Gateway, Engine, Store) MUST mutually authenticate (mTLS/Token).
*   **NFR-SEC-02:** **Encryption:** Data MUST be encrypted at Rest (AES-256) and in Transit (TLS 1.3).

---

## 6. Interface Specifications

### 6.1 The Wire Protocol (Protobuf)
The canonical definition is the `.proto` schema.

```protobuf
message ArqonMessage {
  // Transport Header
  string id = 1;          // UUIDv7
  uint64 sequence = 2;    // Monotonic Ordering
  string topic = 3;       // e.g. "nvm.jobs"
  
  // Context Header
  string producer_id = 4; // Who sent this?
  string reality_id = 5;  // Which universe?
  map<string, string> trace_context = 6; // Dapper/OpenTelemetry
  
  // Emergence Header (Optional)
  SpectralMetadata spectral = 7; 
  
  // Payload
  google.protobuf.Any payload = 8;
}

message SpectralMetadata {
  float coherence = 1;    // Interference visibility [0.0 - 1.0]
  float criticality = 2;  // Distance from critical point
  repeated float eigenvalues = 3; // For spectral analysis
}
```

### 6.2 Topic Naming Standard
Topics MUST follow the hierarchical `domain.subdomain.verb` pattern.
*   `nvm.job.submit`
*   `bowlnet.stream.audio`
*   `sys.control.promote`

---

## 7. System Architecture

The Architecture follows the **Voltron Pattern** (Strict Layering).

```mermaid
graph TD
    Client[Client / Agent] -->|WSS| Shield[Shield (Edge Gateway)]
    Shield -->|Auth & CASIL| Spine[Spine (Message Bus)]
    Spine -->|Route| Brain[Brain (State & Presence)]
    Spine -->|Persist| Storage[(Storage Layer)]
    Spine -->|Dispatch| Op1[Operator: NVM]
    Spine -->|Dispatch| Op2[Operator: Co-Pilot]
```

1.  **Shield:** Terminates TLS, handles Rate Limiting, executes Wasm Safety/CASIL.
2.  **Spine:** Distributed Log / PubSub core (Rust).
3.  **Brain:** Global Coordination, Presence, Room State (Elixir/Rust).
4.  **Operator Tier:** The workers (Wasm/Native) that do the actual computation.

---

## 8. Compliance & Governance

### 8.1 Data Retention
*   **Ephemeral:** Pub/Sub messages default to "Fire and Forget" unless a Retention Policy is defined.
*   **Durable:** "Reality State" must be persisted to valid storage (Postgres/S3) with synchronous write confirmation.

### 8.2 Audit
*   All `sys.control.*` messages are **Mandatory Audit**. They cannot be disabled.

### 8.3 Release Gates
*   No code reaches Production without passing the **ACES Pipeline** (Automated Compliance & Enforcement System), which verifies:
    *   Unit Tests (Coverage > 80%).
    *   Integration Tests (Chaos/Network Partitions).
    *   Safety Policy Verification (Wasm Logic Checks).

---
**End of Specification**
**Approved By:** ____________________ (Product Owner)
