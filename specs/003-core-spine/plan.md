# Implementation Plan: The Core Spine (Epoch 1)

**Branch**: `003-core-spine` | **Date**: 2025-12-11 | **Spec**: [spec.md](./spec.md)
**Input**: "Implement Core Spine using Voltron Architecture (Rust Shield, NATS Spine, Elixir Brain, Wasm Safety)."

## Summary

This plan covers the foundational "Voltron" infrastructure for the ArqonBus vNext Epoch 1. We will establish the **Voltron Monorepo** structure, implement the **Shield** (Rust) for zero-allocation routing, deploy the **Spine** (NATS) with strict isolation configs, and boot the **Brain** (Elixir) for presence tracking.

## Technical Context

**Language/Version**: 
- **Rust**: 1.75+ (Shield) using Tokio/Axum/NATS.rs
- **Elixir**: 1.15+ (Brain) using OTP 26
- **Config**: TOML/YAML

**Primary Dependencies**: 
- **Rust**: `tokio`, `axum`, `async-nats`, `wasmtime`, `prost`
- **Elixir**: `phoenix_pubsub`, `libcluster`, `protobuf`

**Storage**: 
- **Valkey (Redis)**: Persistence for Brain state and Presence
- **NATS JetStream**: (Future) Durable log, strictly Core NATS for now

**Testing**: 
- **Rust**: `cargo test`, `cargo bench` (Criterion)
- **Elixir**: `mix test`
- **Integration**: `k6` for load testing WebSocket gateway

**Target Platform**: Linux (OCI Containers)
**Performance Goals**: < 100μs Shield Routing overhead, 100k concurrent connections per node.
**Constraints**: Fail-Closed Safety, Strict Tenant Isolation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Voltron Pattern**: Adheres to Shield -> Spine -> Brain layering. (II.1)
- [x] **Statelessness**: Shield is purely functional router. (II.2)
- [x] **Protocol Sovereignty**: Protobuf v3 used for all internal messages. (II.3)
- [x] **Tenant Isolation**: NATS subjects enforced as `TenantID.*`. (II.6)
- [x] **Security by Design**: Wasmtime "Fail-Closed" policy hook included. (II.8)

## Project Structure

### Documentation (this feature)

```text
specs/003-core-spine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
# Mixed Polyglot Monorepo
crates/                  # Rust Components (Shield)
├── shield/              # The Gateway Service
│   ├── src/main.rs
│   └── Cargo.toml
├── proto/               # Shareable Protobuf Definitions
│   └── build.rs
└── voltron-core/        # Shared Libs (Wasm host, Config)

lib/                     # Elixir Components (Brain)
├── brain/
│   ├── mix.exs
│   └── lib/brain/
└── brain_web/

deploy/                  # Infrastructure
├── docker-compose.yml   # Local Dev (NATS, Valkey, Shield, Brain)
└── nats/
    └── nats.conf        # Strict config
```

**Structure Decision**: A hybrid workspace. `crates/` for Rust workspace, `lib/` for Elixir umbrella (or standard app). This keeps "Systems" code (Rust) separate from "Business" code (Elixir) while sharing the repo.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Polyglot (Rust + Elixir) | **Optimized for Physics**: Rust for IO/Throughput (Shield), Elixir for Concurrency/State (Brain). | Pure Rust lacks BEAM recovery/presence. Pure Elixir lacks low-level Wasm control/raw websocket perf at scale. |
