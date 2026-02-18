# ArqonBus vNext: Master Plan (The How)

This document defines the **execution strategy** for ArqonBus vNext. It maps the Vision (Constitution) to a concrete roadmap of Engineering Epochs.

Operational status source of truth: `docs/ArqonBus/vnext_status.md`.

## 1. The Strategy: Epoch-Based Execution

We cannot build the "Emergent Intelligence" (Epoch 3) until the "Road" (Epoch 1) is paved. We proceed in three distinct phases.

| Epoch | Name | Focus | Goal |
| :--- | :--- | :--- | :--- |
| **1** | **The Core (Spine)** | Performance, Connectivity, Safety | A working, unblockable O(1) Message Bus. |
| **2** | **The Factory (Platform)** | DevEx, Tooling, SDKs | A platform where humans can easily build Operators. |
| **3** | **The Intelligence (Tier $\Omega$)** | Emergence, Substrates, Agents | Introduction of "Alien" substrates and autonomous optimization. |

---

## 2. Epoch 1: The Foundation (Current Focus)

**Objective:** Build the immutable "Spine" of the system. If we stop after Epoch 1, we must have a world-class, high-performance WebSocket bus that rivals Pusher or Ably, but with our specific architectural guarantees.

### 2.1 The Deliverables

#### **A. The Spine (Transport)**
*   **Technology:** NATS Core + JetStream (or internal Rust implementation if specified).
*   **Requirements:**
    *   Zero-allocation hot paths.
    *   Strict Tenant Isolation context propogation.
    *   CASIL (Content-Aware Safety Inspection Layer) hooks prepared.

#### **B. The Shield (Gateway)**
*   **Technology:** Rust (Axum/Tokio).
*   **Requirements:**
    *   Handle 100k+ concurrent WebSocket connections.
    *   Protocol Normalization (JSON/Protobuf -> Internal Protobuf).
    *   AuthZ/AuthN enforcement at the edge.
    *   **The Overseer:** Wasm host integration for safety policies.

#### **C. The Brain (State)**
*   **Technology:** Elixir (OTP).
*   **Requirements:**
    *   Presence (Who is here?).
    *   Room State (What is the mode?).
    *   Churn Management (Optimization of high-flux rooms).

#### **D. The Protocol (Contract)**
*   **Deliverable:** `arqon.proto` v1.0.
*   **Requirements:**
    *   Header definitions for Time Travel (`X-Twist-ID`, `X-Timestamp`).
    *   Strict message envelopes.

### 2.2 The Checkpoint (Gate to Epoch 2)
*   [ ] Can I connect via `wscat`? (manual CLI validation still pending in this sandbox)
*   [x] Can I auth with a JWT?
*   [x] Can I send a message and see it echoed?
*   [x] Does the Wasm Safety Layer block a "bad" message? (validated via CASIL enforce policy path)

### 2.3 Scope Freeze (Phase 0)
*   [x] Scope is frozen to Epoch 1 deliverables until checkpoint 2.2 is green.
*   [x] Epoch 2/3 work remains explicitly out of scope for current stabilization.

---

## 3. Epoch 2: The Factory (Developer Experience)

**Objective:** Make the bus programmable. Enable "Code-Mobile" architectures and standard Operator patterns.

### 3.1 The Deliverables

*   **SDKs:** Batteries-included clients for Python (Agents), TypeScript (UI), and Go/Rust (Systems).
*   **CLI:** `arqon` command line for tenant management and debugging.
*   **Observability Stack:** Instant Grafana/Prometheus dashboards for every Tenant.
*   **Standard Operators:**
    *   `op-webhook`: Turn messages into HTTP POSTs.
    *   `op-cron`: Schedule messages.
    *   `op-store`: Simple KV storage for Agents.

### 3.2 The Checkpoint (Gate to Epoch 3)
*   [ ] Can a junior dev write a "Hello World" bot in Python in < 5 mins?
*   [ ] Can we deploy a safety policy without restarting the gateway?
*   [ ] Is there a "Tail" (Log stream) visible in the CLI?

---

## 4. Epoch 3: The Singularity (Tier $\Omega$)

**Objective:** Activate the "Alien" features. This is where ArqonBus diverges from standard tech.

### 4.1 The Deliverables

*   **Architect Operators:** RPZL/Relational-Adjoint optimizers that rewrite routing tables.
*   **Subaltrate Operators:** `prime_reservoir`, `algebraic_number_theory` containers.
*   **Holistic Synthesis:** The closed-loop optimization of the system by the system.
*   **TTC (Time Travel):** Replay and Differential Messaging enabled.

---

## 5. Execution Rules

1.  **Strict Seriality:** We do not write Epoch 2 code until Epoch 1 Checkpoints are green.
2.  **Spec First:** Before starting Epoch 1 coding, we must complete `spec/01_core_spine.md`.
3.  **TDD:** All Epoch 1 components must feature full integration tests from Day 0.
