# ArqonBus vNext: Epoch 1 Product Overview

**Status**: Active Definition  
**Epoch**: 1 (The Core Spine)  
**Target Release**: Professional Preview v0.1

---

## 1. Product Vision: The "Complete Package"

ArqonBus Epoch 1 is not just a message broker; it is a **Complete Distributed Application Platform**. It provides the infrastructure, tooling, and observability required to build high-performance, real-time systems out of the box.

We are delivering a "Professional Grade" product from Day 1, emphasizing:

1.  **Zero-Allocation Performance** (Rust Shield)
2.  **Sovereign State Management** (Elixir Brain)
3.  **Developer Joy** (Native CLI, SDKs, Dev Containers)
4.  **Operational Maturity** (OTEL, Grafana, Strict Config)

---

## 2. Architecture & Components

The system follows the **Voltron Architecture**, strictly layering components to separate concerns.

### The Core Runtime (Server)

| Component | Technology | Responsibility | Hosted As |
| :--- | :--- | :--- | :--- |
| **Shield** | **Rust** (Tokio/Axum) | The Edge Gateway. Handles 100k+ WebSockets, JWT Auth, Wasm Safety policies. No allocation on hot paths. | Docker Implementation (`ghcr.io/arqon/shield`) |
| **Spine** | **NATS** (Core) | The Nervous System. Pure subject-based routing (`Tenant.Room`). No business logic. | Docker Image (`nats:alpine`) |
| **Brain** | **Elixir** (OTP) | The State Engine. Manages Presence (CRDTs), Room lifecycle, and Orchestration. | Docker Implementation (`ghcr.io/arqon/brain`) |
| **Safety** | **Wasmtime** | The Overseer. WebAssembly modules running *inside* the Shield for policy enforcement. | Wasm Modules (`.wasm`) |

### The Developer Platform (Tools)

| Component | Technology | Responsibility | Hosted As |
| :--- | :--- | :--- | :--- |
| **`arq` CLI** | **Rust** (Clap) | Unified command-line control. `arq dev up`, `arq auth gen`, `arq status`. | Binary Release (GitHub) |
| **Python SDK** | **Python 3** | Idiomatic client wrapper. `pip install arqon-sdk`. Windows/Mac/Linux support. | PyPI Package (`arqon-sdk`) |
| **Dev Stack** | **Docker Compose** | One-command local environment including NATS, Valkey, Jaeger, and Grafana. | Repo (`deploy/docker-compose.yml`) |

---

## 3. End-to-End Coverage

We provide a complete lifecycle solution, not just a binary.

### A. Development (The "First 5 Minutes")
*   **Dev Containers**: A `.devcontainer` definition allows instant onboarding in VS Code with all toolchains pre-installed.
*   **Local Stack**: `arq dev up` spins up the entire platform locally, mirroring production.
*   **Hot Reload**: The `brain` (Elixir) and `shield` (Rust) support rapid iteration.

### B. Deployment & Operations
*   **Strict Configuration**: A typed `config.toml` acts as the contract between Dev and Ops. No hidden environment variables.
*   **Observability First**:
    *   **Metrics**: Prometheus endpoints on all services.
    *   **Tracing**: OpenTelemetry context propagation (W3C Trace Context) from Client -> Shield -> Spine -> Brain.
    *   **Visuals**: Pre-provisioned Grafana Dashboards included in the Docker image.
*   **Health**: Deep health check endpoints (`/health/live`, `/health/ready`) for K8s integration.

### C. Distribution Strategy
All artifacts are built automatically via GitHub Actions pipelines:

1.  **Docker Images**: Multi-arch builds (AMD64/ARM64) pushed to **GitHub Container Registry (GHCR)**.
    *   `ghcr.io/novelbytelabs/arqon-shield:latest`
    *   `ghcr.io/novelbytelabs/arqon-brain:latest`
2.  **SDKs**: Python packages published to **PyPI** on every release tag.
3.  **CLI Binaries**: Static binaries for Windows, macOS, and Linux attached to **GitHub Releases**.

---

## 4. Implementation Plan (Current Status)

We are currently executing the **Epoch 1 Implementation Plan** (`specs/003-core-spine/plan.md`).

### Active Workstreams
1.  **Scaffolding**: Setting up the Polyglot Monorepo (`crates/` + `lib/`).
2.  **Core Core**: Implement basic NATS connectivity in Rust and Elixir.
3.  **Tooling**: Building the `arq-cli` to replace manual script usage.

### Next Steps
*   Run `/speckit.tasks` to generate the granular work items.
*   Begin code implementation of the Shield and Brain.
