# Software Design Document (SDD) - ArqonHPO
**Version**: 1.0.0
**Status**: Release Candidate
## 1. Introduction
ArqonHPO is a specialized Hyperparameter Optimization (HPO) engine designed to solve "Structured" engineering problems 10x faster than standard Bayesian methods.
## 2. Architecture: ArqonBus Operator Pattern

### 2.1 Core Principle: "Hot Path in Rust"
To meet the microsecond-class latency requirements of ArqonBus vNext, ArqonHPO allows no Python in the critical search path.
- **Eval Path**: May be slow (Simulation/AI).
- **Search Path**: MUST be fast (Rust).

### 2.2 Component Diagram
\`\`\`mermaid
graph TD
    subgraph "Rust Core (arqonhpo-core)"
        RPZL[RPZL Sampler]
        Variance[Variance Detector]
        TPE[TPE Logic]
    end
    
    subgraph "Interfaces"
        Op[arqonhpo-operator (Bus/Protobuf)]
        Py[arqonhpo-py (Python Bindings)]
        CLI[arqon-hpo-cli]
    end
    
    RPZL --> Op
    RPZL --> Py
    TPE --> Op
    TPE --> Py
\`\`\`

## 3. Implementation Plan
1.  **Phase 1 (Rust Core)**: Implement `arqonhpo-core` crate.
    -   Port `_rpzl_sample` from Python to Rust.
    -   Implement `VarianceTest`.
2.  **Phase 2 (Bindings)**: Use `pyo3` and `maturin` to bind Core to Python.
    -   Replace `src/arqon_hpo.py` with a Rust extension.
3.  **Phase 3 (Operator)**: Build the standalone Bus Operator service.

## 4. Interfaces
- **Rust API**: `pub fn optimize(config: Config) -> OptimizationResult`
- **Python API**: `from arqon_hpo import ArqonSolver` (Wrapper around Rust)
- **Protocol**: NATS/WebSocket for Bus communication.

## 5. Requirements Traceability
- **REQ-001**: **Latency**: Search step overhead < 100μs (Rust Required).
- **REQ-002**: **Latency**: Bus integration via Async Tokio.
- **REQ-003**: **UX**: Python glue for offline research (PyO3).
