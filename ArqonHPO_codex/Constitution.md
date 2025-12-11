# ArqonHPO Constitution

## 1. The Prime Directive: Latency First
ArqonHPO is a microsecond-class operator for the ArqonBus.
**Rule #1**: The Hot Path (Search Logic) MUST be implemented in a systems language (Rust).
**Rule #2**: Python is allowed ONLY for offline analysis, bindings, and research glue. It must NEVER be in the real-time control loop.

## 2. Architecture
- **Core**: `arqonhpo-core` (Rust). No GC, Zero-Cost Abstractions.
- **Operator**: `arqonhpo-operator` (Rust). Async Tokio bindings to the Bus.
- **Bindings**: `arqonhpo-py` (PyO3). Ergonomic wrapper for Data Scientists.

## 3. Operations
- **Reproducibility**: All random seeds must be distinct and logged.
- **Observability**: All internal state transitions must emit structured telemetry.
