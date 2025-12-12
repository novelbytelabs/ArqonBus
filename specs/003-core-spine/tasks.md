# Task List: The Core Spine (Epoch 1)

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Status**: Planning

## Phase 1: The Factory (CI/CD & Polyglot Scaffolding)
*The Foundation Phase. Nothing exists until the Factory can build it.*

- [x] **Initialize Polyglot Workspace**
    - [ ] Create `crates/Cargo.toml` (Workspace Root)
    - [ ] Create `lib/brain/mix.exs` (Elixir App)
    - [ ] Create `deploy/docker-compose.yml` (NATS, Valkey, Jaeger, Grafana)
    - [ ] **Verification**: `docker compose up` starts all infra services.
- [x] **Setup GitHub Actions (The Assembly Line)**
    - [ ] Create `.github/workflows/ci-rust.yml` (Matrix: Lin/Win/Mac)
    - [ ] Create `.github/workflows/ci-elixir.yml` (OTP 26)
    - [ ] Create `.github/workflows/docker-publish.yml` (GHCR Multi-Arch)
    - [ ] **Verification**: Push to branch triggers green CI matrix.
- [x] **Define Protocol Contracts**
    - [ ] Create `crates/proto/src/envelope.proto` (The V1 Schema)
    - [ ] Add `prost-build` to `crates/proto/build.rs`
    - [ ] **Verification**: `cargo build -p proto` generates Rust structs.

## Phase 2: The Core (Shield & Spine)
*The Nervous System. Establishing connectivity.*

- [/] **Implement The Shield Reactor (Rust)**
    - [ ] Scaffold `crates/shield` (Axum/Tokio)
    - [ ] Implement `ConnectionActor` (WebSocket State Machine)
    - [ ] Implement Zero-Copy NATS Bridge (`async-nats`)
    - [ ] **Verification**: `wscat` connection sends message to NATS subject `in.t.T1.r.R1`.
- [ ] **Implement NATS Topology**
    - [ ] Configure `deploy/nats/nats.conf` with strict Subject Mapping
    - [ ] Define JetStream Streams for `sys.*` (Audit Logs)
    - [ ] **Verification**: `nats pub` to forbidden subject is rejected.

## Phase 3: The Brain (Elixir State)
*The Control Plane. Tracking "Who is where".*

- [ ] **Implement Brain Topology**
    - [ ] Configure `libcluster` for Mesh Discovery
    - [ ] Implement `Brain.Application` Supervision Tree
    - [ ] **Verification**: Start 2 Brain nodes, verify they form a cluster.
- [ ] **Implement Presence Engine**
    - [ ] Add `Brain.Overlay.Presence` (Phoenix.Tracker)
    - [ ] Implement NATS Consumer (`in.t.*`) -> Presence Update
    - [ ] **Verification**: Connect Client A -> Shield -> NATS -> Brain -> Client B sees "A Joined".
- [ ] **Implement Room Manager**
    - [ ] Create `Brain.Context.Room` GenServer
    - [ ] Implement `DynamicSupervisor` for Room spawning
    - [ ] **Verification**: Sending to `room_1` spawns a process for `room_1`.

## Phase 4: The Overseer (Safety & Observability)
*The Governance Layer.*

- [ ] **Implement Wasm Host (Rust)**
    - [ ] Add `wasmtime` to `crates/shield`
    - [ ] Implement `PolicyEngine` (Fail-Closed Execution)
    - [ ] **Verification**: Load a "Ban All" wasm module; verify all connections drop.
- [ ] **Implement Telemetry Contracts**
    - [ ] Configure `opentelemetry` in Rust (Shield)
    - [ ] Configure `opentelemetry_exporter` in Elixir (Brain)
    - [ ] **Verification**: TraceID propagates from Client -> Shield -> Brain -> Jaeger UI.

## Phase 5: The Product (Packaging)
*The Developer Experience.*

- [ ] **Build `arq` CLI Tool**
    - [ ] Create `crates/arq-cli` (Clap)
    - [ ] Implement `arq dev up` (Docker Wrapper)
    - [ ] Implement `arq auth gen` (JWT Minter)
    - [ ] **Verification**: `arq dev up` boots the full stack from zero.
- [ ] **Publish Python SDK**
    - [ ] Create `sdks/python/pyproject.toml`
    - [ ] Implement `arqon.connect()` wrapper
    - [ ] **Verification**: `pip install .` and run echo example.
- [ ] **Final Polish**
    - [ ] Audit `config.toml` Schema Enforcement
    - [ ] Update Documentation with "As Built" specs
