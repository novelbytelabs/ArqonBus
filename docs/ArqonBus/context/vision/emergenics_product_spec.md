# ArqonBus Specification (PRD)

## 1. Product Overview

**Product Name:** ArqonBus  
**Type:** Websocket-based message and computation bus  
**Primary Users:**  
- Researchers and engineers using NVM / ITMD / BowlNet systems.  
- Backend developers building services that consume or provide physical/digital compute.  
- Platform engineers operating NVMaaS / Omega-Fabric style infrastructures.

**Problem:**  
There is no coherent way to treat physical compute (acoustic bowls, optical paths, NVM rigs) and digital services as peers on a single bus. Current systems treat analog experiments as offline, manual pipelines, and websockets as thin JSON pipes, not carriers of executable, causally-compressed programs.

**Solution:**  
ArqonBus is a websocket-native bus that:

- Transports **typed messages and program capsules** between digital and physical endpoints.
- Provides **topics and circuits** to orchestrate complex pipelines (NVM → BowlNet → QML → storage).
- Bakes in **observability, safety, and reproducibility** at the protocol level.

## 2. Goals & Non-Goals

### 2.1 Goals

- **G1: Unified Bus for Digital & Physical Compute**  
  Allow NVM, BowlNet, QML POCs, and standard microservices to communicate over a single bus abstraction.

- **G2: Program Capsules over Websockets**  
  Define a standard message shape for self-executing jobs that includes code/refs, parameters, constraints, and provenance.

- **G3: Topic & Circuit Orchestration**  
  Support declarative configuration of pipelines, including branching, fan-in/fan-out, and routing to physical operators.

- **G4: Observability & Replay**  
  Capture enough metadata to replay computations and reconstruct flows from logs and stored messages.

- **G5: Safety & Quotas**  
  Enforce resource caps and sandboxing boundaries for program capsules, including physical resource usage.

- **G6: Helios / NVMaaS Alignment**  
  Provide a transport and orchestration layer that aligns cleanly with the Helios Engine and NVMaaS roadmap (pilot projects, SaaS APIs), so the same ArqonBus topics and contracts can be used internally and by early external clients.

### 2.2 Non-Goals

- ArqonBus is **not** a long-term archival system. It may integrate with object storage or databases but is not itself a database.
- ArqonBus is **not** a GUI analytics product. It exposes APIs and a minimal CLI/SDK; UIs are separate projects.
- ArqonBus is **not** responsible for training neural networks or designing NVM hardware; it follows the contracts defined by those systems.

## 3. User Stories

1. **NVM Job Dispatch**  
   As a researcher, I want to submit an NVM pulse configuration and payload over a websocket and receive the resulting measurements and computed outputs as a structured response stream.

2. **BowlNet Feature Pipeline**  
   As a data scientist, I want to stream audio into a BowlNet operator (physical or simulated) and receive labeled feature vectors and classifications over the same bus.

3. **Hybrid Circuit Orchestration**  
   As a platform engineer, I want to define a pipeline that routes inputs to NVM, forwards outputs into a QML classifier, and archives results, all configured declaratively and monitored centrally.

4. **Simulation vs. Hardware Swap**  
   As an experiment designer, I want to test against a software-simulated operator, then switch to real hardware by changing configuration only, not code.

5. **Safe Experimental Sandboxes**  
   As a researcher, I want to run experimental program capsules with tight quotas (time, CPU, physical runs) in isolated namespaces before promoting them to production.

6. **Helios / Hybrid Engine Integration**  
   As a platform engineer, I want to route Helios (ITMD/RR/Passive Compute) engine jobs and results through ArqonBus, so the same bus orchestrates both Helios-accelerated digital compute and NVM/BowlNet/physical operators.

7. **Δ-Only Update Flows**  
   As an infra engineer, I want to declare that certain topics carry only deltas (changes) rather than full state, so operators and clients can implement efficient ITMD-style incremental updates.

8. **Streaming ITMD Transformers & Kernels**  
   As an ML engineer, I want to stream Transformer or kernel workloads (e.g., RFF attention, dynamic graphs, PDE solvers) through ArqonBus as incremental ITMD jobs, so I can amortize heavy precomputation and reuse across changing inputs.

9. **Churn-Aware Hybrid Engine Control**  
   As a systems engineer, I want to expose Helios/ITMD/RR engine modes and churn metrics over ArqonBus so that a meta-controller (possibly external) can observe dynamics and choose between PASS/ITMD/RR or other modes per step.

## 4. System Architecture

### 4.1 High-Level Components

- **ArqonBus Server**
  - Logically split into:
    - **Shield (Edge):** WebSocket termination, auth, rate limiting, Wasm safety.
    - **Spine (Bus):** Internal topics, circuits, routing, and authorization.
  - Exposes a control API (for management/topology) and data API (for messages).

- **Client SDKs**
  - First-class: Python SDK for research environments and services.
  - Responsibilities:
    - Connect, authenticate, and subscribe/publish.
    - Encode/decode ArqonBus message types.
    - Provide helpers for common patterns (NVM jobs, BowlNet streams, PACF programs).

- **Operators**
  - Long-lived workers that:
    - Subscribe to `*.jobs` topics on the Spine.
    - Execute compute (Helios, NVM, BowlNet, Genesis-style distillers, QML, etc.).
    - Publish `*.results` and telemetry.
  - Two deployment styles:
    - **Native operators:** use ArqonBus SDKs directly.
    - **Proxied services:** existing HTTP/GRPC workers driven by a thin ArqonBus operator shim.

- **NVMaaS / Helios API Bridges**
  - Lightweight services or adapters that translate between:
    - Existing Helios/NVMaaS REST-style APIs (`/compile_transform`, `/apply_transform`, pilot endpoints).
    - ArqonBus topics and message schemas (e.g., `helios.jobs`, `helios.results`).
  - Allow existing Helios clients to gradually adopt ArqonBus without breaking changes.

### 4.2 Deployment Model

- **Single-node Dev Mode**
  - One ArqonBus server (Shield + Spine in a single process).
  - Operators and clients connect over local WebSockets (`ws://`) or via native SDK to the Spine.

- **Cluster Mode (Future)**
  - Multiple ArqonBus instances with a shared state store (e.g., etcd, Redis, or a pluggable backend).
  - Horizontal scaling of topics and circuits.
  - Operators are scheduled onto nodes but always speak to the Spine, never to the Shield directly.

## 5. Message & Protocol Design

### 5.1 Transport

- Websocket over TLS (`wss://`) is the primary transport.
- Messages are encoded primarily as **Protocol Buffers (protobuf)** on the wire for efficiency and strong typing.
- Human-facing and debugging endpoints (e.g., CLI tools, dashboards, simple HTTP control APIs) may expose **JSON views** of the same messages, derived from the protobuf schemas.

### 5.2 Core Message Envelope

Every ArqonBus message MUST follow a base envelope:

- `id`: globally unique message identifier (UUID).
- `type`: one of `event`, `job`, `job_result`, `stream_start`, `stream_chunk`, `stream_end`, `control`.
- `topic`: semantic channel name (e.g., `nvm.jobs`, `bowlnet.features`).
- `ts`: ISO-8601 timestamp.
- `schema`: logical schema identifier (`arqonbus.nvm.job.v1`, etc.).
  - `payload`: schema-specific body (see below).
- `trace`: optional tracing metadata (`span_id`, `parent_id`, etc.).

### 5.3 Operator Endpoint Contract

Operators MUST implement the following behaviors (directly or via a proxy shim):

- Advertise capabilities on the **control plane**:
  - `operator_id`
  - `operator_type` (`nvm`, `bowlnet`, `qml`, `helios`, `generic`)
  - `supported_schemas` (input/output)
  - `resource_limits` (max parallel jobs, physical run budget, etc.)
  - `hardware_profile` (e.g., `cpu`, `gpu`, `fpga`, `asic`) and any Δ-aware capabilities (e.g., `supports_delta_only_topics: true`).
  - Optional `engine_modes` (e.g., `["pass", "itmd", "rr"]`) and exposed `churn_metrics` (e.g., observed churn fraction `p`, error estimates).

- Subscribe to one or more **job topics** (e.g., `nvm.jobs`).

- For each `job` message received:
  - Validate the schema and parameters.
  - Enforce local quotas (and reject if violated).
  - Execute the job (digital and/or physical).
  - Emit `job_result` and optional `stream_*` messages with results.

- **Proxied operators**
  - An ArqonBus-native shim owns the bus contract.
  - The shim forwards requests to a backing service (e.g., Genesis Flask server) over HTTP/GRPC.
  - The backing service never talks to the Spine or Shield directly; it remains a pure worker behind the proxy.

### 5.4 Job Payloads (Examples)

**NVM Job (`arqonbus.nvm.job.v1`):**

- `job_id`
- `program_ref` or inline `program` (NVM pulse configuration, parameters).
- `input_data` (or references to stored data).
- `constraints`:
  - `max_runtime_ms`
  - `max_energy_joules` (if available)
  - `max_runs`
- `metadata` (experiment labels, tags).

**BowlNet Feature Job (`arqonbus.bowlnet.job.v1`):**

- `job_id`
- `operator_set` (which bowls/impulse responses to use).
- `mode` (`online_stream`, `batch`).
- `input_audio_ref` or streaming audio topic.
- `output_topics` (feature vectors, labels).

**ITMD Streaming Job (`arqonbus.itmd.job.v1`):**

- `job_id`
- `workload_type` (`transformer_attn`, `dynamic_graph`, `pde_solver`, etc.).
- `kernel_spec` (e.g., RFF kernel parameters, Nyström config).
- `precompute_ref` or inline `precompute_config` (what to cache and reuse).
- `delta_mode` (`full_state`, `delta_only`).
- `input_state_ref` and optional `delta_payload` (for incremental updates).
- `constraints` (max latency per update, error tolerance).

### 5.5 Streams

- Streams are modeled as sequences of messages:
  - `stream_start` (with stream id, topics, schemas).
  - `stream_chunk` (sequence of payloads, chunks, frames).
  - `stream_end` (final status and summary).

- Use cases:
  - Continuous audio into a BowlNet operator.
  - NVM output frames (e.g., QML POC frames) to downstream consumers.
  - Δ-only update streams for ITMD/Helios-style incremental state evolution.

## 6. Topics & Circuits

### 6.1 Topic Naming

- Use dot-separated names: `domain.subdomain.verb` style, e.g.:
  - `nvm.jobs`, `nvm.results`
  - `bowlnet.features`, `bowlnet.jobs`
  - `pacf.streams`
   - `helios.jobs`, `helios.results`, `helios.metrics`
  - `system.control.operators`

### 6.2 Circuit Configuration

- Circuits are defined declaratively (e.g., in YAML) as:
  - Nodes (topics and operators).
  - Edges (routing rules, filters, fan-out).

- Example circuit:
  - `input.audio` → `nvm.jobs` → `nvm.results` → `bowlnet.jobs` → `bowlnet.features` → `qml.jobs` → `qml.results`.

- Topology introspection:
  - The control API MUST expose:
    - The set of registered operators and their topic bindings.
    - Active circuits and their constituent topics.
  - This enables external tooling (and future CI) to verify that:
    - All traffic between Shield and operators flows through the Spine.
    - No hidden side channels or bypass paths exist.

## 7. Security & Auth

- **Authentication:**  
  - JWT or mTLS-based identity for clients and operators.

- **Authorization:**  
  - Role/capability-based policies, e.g.:
    - `can_publish:nvm.jobs`, `can_subscribe:nvm.results`.
    - `can_execute:bowlnet` with specific resource caps.

- **Isolation:**  
  - Namespaces or projects to separate experimental and production workloads.

- **Audit Logs:**  
  - Every job and stream is logged with:
    - Inputs, outputs, and hashes.
    - Operator identity and environment fingerprint.
    - Resource usage metrics where available.

## 8. Observability

- **Metrics:**  
  - Message throughput, latency, error rates per topic and operator.

- **Tracing:**  
  - Correlate messages through circuits using `trace` metadata.

- **Replay:**  
  - Ability to re-inject recorded message sequences into a test namespace.

## 9. MVP Scope

The initial ArqonBus MVP will:

- Implement a **single-node server** with websocket support.
- Provide a **Python SDK** with:
  - Connect/subscribe/publish.
  - Helpers for `nvm.jobs` and `nvm.results`.
- Implement a **reference NVM operator proxy** that:
  - Wraps existing NVM notebooks / scripts as callable jobs where feasible.
  - Logs inputs/outputs to local storage.
- Implement a **minimal Helios/Meta-ITMD bridge** that:
  - Wraps a local or remote Helios Engine instance behind `helios.jobs` / `helios.results` topics.
  - Mirrors core `/compile_transform` and `/apply_transform` flows used in pilot projects.
- Provide **basic auth** (API keys or JWT) and per-topic ACLs.
- Include minimal **docs and examples**, including:
  - “Hello, NVM job” example.
  - “Hello, BowlNet features” example (may initially be simulated).

Out of scope for MVP (but in roadmap):

- Clustered deployment.
- Full BowlNet and QML integration.
- Binary framing and advanced QoS.

## 10. Roadmap (High-Level)

1. **MVP (v0.1)**  
   - Single server, Python SDK, NVM job path, basic auth, minimal observability.

2. **Hybrid Compute (v0.2)**  
   - BowlNet operators, QML integration, richer circuits, improved tracing.

3. **Production-Grade Bus (v1.0)**  
   - Clustering, robust security, binary protocol, full docs and SDKs in multiple languages.

4. **Standards & Community (v1.x+)**  
   - Publish stable protocol versions, reference implementations, and engage external community and standards bodies.
