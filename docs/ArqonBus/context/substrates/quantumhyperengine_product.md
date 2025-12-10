# QuantumHyperEngine Product Brief

This document reframes the core research in this repo (NVM, ITMD/Helios, BowlNet/Phonic ROM, Quantum NVM, QML) as a coherent product line that ArqonBus can orchestrate and expose.

It is intentionally high-level and customer-facing: what the system is, who it serves, and how it’s packaged.

---

## 1. Product Overview

**Product Family Name:** QuantumHyperEngine  
**Core Offering:** A suite of hybrid physical–digital compute engines that offload heavy computation into pre-computed transforms and physical substrates, with ArqonBus as the coordination fabric.

QuantumHyperEngine is composed of three primary pillars:

1. **Helios Engine (ITMD / RR / Meta-ITMD)**
   - A software accelerator for AI and scientific computing that makes compute cost scale with *change* (Δ) instead of problem size.
   - Targets: Transformers (attention), GEMMs, dynamic graphs, PDEs, and streaming workloads.

2. **Number Virtual Machine (NVM) & Phonic / Optical NVM**
   - A physical computation paradigm where pulses (audio, optical) carry self-contained programs and are transformed by engineered media.
   - Targets: massively parallel correlation, causal compression, and quantum-inspired computation via acoustic/optical hardware.

3. **BowlNet / Phonic ROM / QML Backends**
   - Hybrid physical–digital neural networks and QML systems where physical bowls or optical paths act as fixed kernels, and lightweight digital heads do interpretation.
   - Targets: feature extraction, classification, and QML inference with strong physical priors.

ArqonBus sits above these as the **message and coordination bus**, turning them into addressable services.

---

## 2. Target Users & Problems

**Primary Users:**

- AI / ML infrastructure teams running large Transformer or kernel-heavy models under tight latency/throughput budgets.
- Scientific computing teams (simulation, PDEs, optimization) looking for speedups without sacrificing accuracy.
- Research labs and startups exploring hybrid physical–digital compute (acoustic, optical, neuromorphic) with real workloads.

**Core Problems:**

- Quadratic or cubic scaling of key workloads (attention, GEMMs, dynamic graphs) makes long-context, real-time systems too expensive.
- High-value physical compute experiments remain siloed in notebooks, not exposed as services that can be orchestrated at scale.
- There is no unified way to treat digital accelerators (Helios), physical NVMs, and QML systems as peers on a single fabric.

QuantumHyperEngine addresses these by:

- Turning Δ-aware algorithms (ITMD/RR) into productized engines.
- Turning physical setups (bowls, optical paths, NVM rigs) into virtualized “operators” with digital APIs.
- Using ArqonBus to orchestrate jobs, streams, and checkpoints across all of them.

---

## 3. Product Components

### 3.1 Helios Engine (Software)

**Description:**  
A C++/CUDA (and Python-wrapped) engine that implements ITMD, RR, and hybrid controllers for:

- Sub-quadratic Transformers (attention with ITMD/RR/PASS).
- NT-IRR for structured GEMMs and linear algebra.
- Dynamic graphs (Dijkstra, PageRank) and PDEs.

**Key Features:**

- Δ-first compute: cost proportional to fraction changed `p`.
- Hybrid modes (PASS / ITMD / RR) with a churn-aware meta-controller.
- Proven speedups vs. strong baselines (2–10x and beyond) on real workloads.

**ArqonBus Integration:**

- Exposed as `helios` operators reachable via `helios.jobs`, `helios.results`, and `helios.metrics` topics.
- ArqonBus encapsulates Helios jobs as protobuf messages (workload type, kernel spec, precompute references, constraints).

### 3.2 NVM Pulse Engine (Audio / Optical)

**Description:**  
A set of NVM encoders/decoders and protocols that:

- Encode certificates (program + parameters + checksums) into audio/optical pulses (OOK modulation with robust preambles).
- Decode received pulses back into program capsules and state.
- Execute programs on fixed, mini-CPU / TinyRISC-style NVM cores with:
  - Fixed-size binary state snapshots (registers, RAM, PC).
  - Integrated FEC and resilience against noise.
  - Demonstrated robustness and throughput in noisy or lossy channels (audio, optical frames).
- Externalize and re-import CPU state via pulses (e.g., Fibonacci RISC/TinyRISC demos), proving that computation can be “chunked” and streamed through physical media.

Variants:

- **Quantum NVM:** Pulses carry quantum simulation states, circuits, and inputs; receivers verify fidelity.
- **Distributed Quantum NVM:** Intermediate states are teleported between nodes via pulses.
- **Hybrid VQE & QML POCs:** Iterative classical–quantum loops that use pulses for IO.

**ArqonBus Integration:**

- Exposed as `nvm` operators reachable via `nvm.jobs`, `nvm.results`, and stream topics for pulses and measurement data.
- NVM jobs carry structured payloads (config refs, certificate bytes, mode flags like `quantum_state_teleport`, `vqe_step`, `qml_inference`).

**Demonstrated Capabilities:**

- Audio CPU execution (TinyRISC over NVM pulses, RAM/state round-tripping in audio).
- Optical robustness (NVM certificates encoded as frame sequences and recovered with perfect integrity).
- Interactive NVM (Lunar Lander game where NVM owns physics/state and the host is a thin terminal).
- Simulated metamaterial and CMOS/neuromorphic receivers (film-based XOR/CPU, spatial and “flash” CMOS capture) that outline future physical NVM hardware profiles behind the same ArqonBus operator contract.

### 3.3 BowlNet / Phonic ROM & QML Backends

**Description:**  
Physical or recorded impulse-response libraries (Phonic ROM) representing bowls or acoustic setups that:

- Act as pre-trained convolutional layers or kernels.
- Provide feature extraction and classification when combined with small digital heads.

QML POCs extend this to:

- Quantum-inspired classifiers where QTR and pulses carry parameters and results.

**ArqonBus Integration:**

- BowlNet operators as `bowlnet` services with jobs for feature extraction and classification.
- QML backends as `qml` operators receiving input data, ansatz definitions, and returning predictions/metrics.

**Demonstrated Capabilities:**

- Dual-core (and multi-core) phonic processing with distinct channels per bowl and measurable differential transforms.
- Bowl supercomputer benchmarks (phase-code search, control planning) validating phonic substrates as high-throughput correlators.

---

## 4. Productized Workflows (Examples)

### 4.1 Long-Context Transformer Inference

- Client sends a Helios ITMD attention job (`helios.jobs`) with:
  - Model/key parameters.
  - Churn metrics or update sets.
  - Accuracy/latency constraints.
- Helios operator runs hybrid PASS/ITMD/RR attention and returns results on `helios.results`.
- ArqonBus streams metrics on `helios.metrics` for observability and control.

### 4.2 Quantum State Checkpoint & Teleport

- Node A prepares a quantum state via QTR, serializes it, and sends an NVM job (`nvm.jobs`) to encode and transmit pulse(s).
- A physical or simulated NVM pipeline runs; the receiver decodes and verifies fidelity.
- ArqonBus topics capture the full trace:
  - `nvm.jobs`, `nvm.results`.
  - Optional `nvm.streams` for raw pulse/measurement data.

### 4.3 Hybrid VQE Loop

- Optimizer service publishes VQE step jobs:
  - Circuit parameters, desired observables.
- NVM/QTR backend operator consumes jobs, runs circuits, returns expectation values.
- ArqonBus orchestrates this loop, enabling multiple optimizers/backends and centralized logging/metrics.

### 4.4 QML Classification with Physical Verification

- Data ingestion service publishes QML inference jobs with:
  - Input points.
  - Classifier definition (ansatz parameters).
- QML backend returns predicted labels and wraps them in pulses for external verification.
- ArqonBus ensures end-to-end traceability for each inference.

---

## 5. Packaging & Editions

**Edition A: Helios SDK + ArqonBus Integration**

- Helios Engine library (C++/CUDA + Python bindings).
- ArqonBus server + Python SDK.
- Protobuf schemas for Helios jobs/results/metrics.
- Target: AI/ML infra teams wanting software-only acceleration.

**Edition B: NVM Pulse & Phonic ROM Kit**

- NVM encoder/decoder libraries.
- Phonic ROM libraries (recorded bowls/operators).
- Example ArqonBus circuits connecting clients → NVM → digital consumers.
- Target: research labs and early adopters of physical compute.

**Edition C: Quantum/QML Lab Edition**

- QTR-based quantum simulation backends.
- VQE and QML examples with NVM pulses and ArqonBus orchestration.
- Target: quantum researchers and hybrid ML teams.

**Internal Demos & Staging Patterns (Reference Only)**

- Genesis Engine (procedural asset distillation via Flask + Cloudflare tunnel) lives under `staging/` and serves as a pattern for how notebook-born engines become HTTP APIs.
- ArqonBus is expected to front similar services not by embedding Flask, but by treating them as external operators reachable over stable, versioned protocols.

---

## 6. Relationship to ArqonBus

QuantumHyperEngine is **not** ArqonBus itself; it is the primary **tenant** and **workload family** that ArqonBus is designed to showcase and support.

- ArqonBus provides:
  - Websocket/protobuf message fabric.
  - Topics, circuits, and safety layers.
  - Multi-tenant, multi-operator orchestration.

- QuantumHyperEngine provides:
  - The high-value, Δ-first and physical compute services.
  - Concrete jobs, streams, and patterns that drive ArqonBus’ design.

Design decisions in ArqonBus (Δ-first, physics-aware, protobuf-on-the-wire, semantic topics) are grounded in the needs of QuantumHyperEngine and similar workloads.

---

## 7. Roadmap (High-Level)

1. **Productization of Helios (Short Term)**  
   - Harden Helios APIs and protobuf schemas.
   - Deliver ArqonBus-integrated Helios SDK and reference operators.

2. **NVM Pulse & Phonic ROM Services (Mid Term)**  
   - Turn the existing NVM and BowlNet demos into deployable services behind ArqonBus.
   - Provide clear NVM job schemas, SLAs, and monitoring.

3. **Quantum / QML Workflows (Mid–Long Term)**  
   - Formalize VQE and QML job types.
   - Provide example multi-node circuits (distributed quantum, teleportation).

4. **Externalization & Developer Experience**  
   - SDKs, examples, and tutorials showing how to build on QuantumHyperEngine via ArqonBus.
   - Clear onboarding for “add your own operator” (digital or physical).
