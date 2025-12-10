# ArqonBus Constitution

## 1. Mission

ArqonBus is a websocket-native fabric for routing self-executing logic, not just bytes.  
It treats each message as **Kolmogorov-style code** (seed + rules) that can unpack into
potentially unbounded, structured behavior at the edge or in specialized physical backends.

The mission of ArqonBus is to:

- Provide a **universal, substrate-agnostic bus** that can address digital compute, NVM / ITMD engines, BowlNet-style physical operators, and classical services through a single coherent message model.
- Make **causal compression and PACF “digital DNA”** first-class citizens of the transport layer.
- Enable **safe, auditable, self-executing computation** to flow across media (websockets, RF, acoustic, optical) with verifiable integrity and bounded risk.

ArqonBus is the networking spine of the QuantumHyperEngine ecosystem.

## 2. First Principles

ArqonBus is grounded in the core ideas developed throughout this repo:

1. **Input → Transform → Measure (ITM / ITMD)**  
   - Any stable physical transform can be treated as a computational primitive.  
   - The bus addresses not only digital services but **physical transform endpoints** (acoustic bowls, optical paths, NVM pulses).

2. **Causal Compression & PACF Digital DNA**  
   - Messages can be expressed as **PACF-like encodings** or other causal programs:  
     short seeds + rules that deterministically generate long, structured behavior.  
   - The bus is optimized for **sending seeds and deltas**, not raw expanded data.

3. **NVM Pulses as Program Carriers**  
   - NVM pulses are **self-contained programs** with forward-error correction and
     fixed-size, media-agnostic envelopes.  
   - ArqonBus adopts this philosophy at the protocol layer: fixed, predictable
     envelopes carrying **typed pulses** of logic/state.

4. **Transform-Measure Networks (BowlNet)**  
   - Physical and virtual “bowl” operators act as **fixed, pre-trained layers**; a small digital head performs classification or control.  
   - ArqonBus routes **signals and feature streams** through these operators as first-class subscribers, not as opaque black boxes.

5. **Relational Information, Not Raw Entropy**  
   - Meaning arises from **relations, flows, and context**, not symbol counts.  
   - The bus is designed around **semantic channels** (topics, circuits, and roles)
     rather than just byte streams.

6. **Δ-First Computation (ITMD Calculus)**  
   - Computation cost should scale with **change (Δ)**, not with total system size.  
   - ArqonBus prefers **incremental, delta-based updates** and representations wherever possible, aligning with ITMD calculus (“compute by differences”).

7. **Physics-Respecting Efficiency (Within Fundamental Limits)**  
   - ArqonBus is designed to **respect physical laws** (causality, thermodynamic bounds) while exploiting the large algorithmic headroom that still exists.  
   - Efficiency gains should come from **avoiding redundant work and propagating local changes**, not from hand-waving around physical constraints.

## 3. Core Values

1. **Substrate-Agnostic Computation**
   - Treat acoustic, optical, RF, numerical, and symbolic compute as peers.
   - The bus defines **interfaces and contracts**, not implementation preferences.

2. **Deterministic Reproducibility**
   - Every message that carries executable logic must be **fully reproducible** from its
     encoded form (seed + rules + versioned interpreter spec).
   - Physical transforms are recorded as **Phonic ROM / operator fingerprints**
     so that experiments and production flows are replayable in software.

3. **Safety & Bounded Blast Radius**
   - All self-executing logic must run inside **explicit sandboxes** with quotas
     (time, energy, calls to physical hardware, data access).  
   - The bus encourages **declarative computation** with clear resource bounds.

4. **Observability & Evidence**
   - Every message and computation path should be traceable via **computational fingerprints**, logs, and hashes.  
   - Observability is built in at the protocol and SDK layers, not bolted on.

5. **Progressive Disclosure & Open Standards**
   - Core protocols, schemas, and reference implementations are **open and documented**.  
   - Sensitive hardware designs may be staged (NVMaaS / hardware IP), but **wire protocols and message formats remain standardizable.**

6. **Human-Centric Clarity**
   - Despite its depth, ArqonBus aims to be **understandable by a senior engineer** by reading a small number of docs and examples.  
   - Everything complex is packaged into **named patterns** (e.g., “NVM pulse job”, “BowlNet feature stream”, “PACF program delivery”).

## 4. Scope & Responsibilities

ArqonBus is responsible for:

- A **websocket-based message fabric** for local and distributed deployment.
- A **typed message model** that can describe:
  - Static data (events, documents, metrics).
  - Jobs: requests to run computation in digital or physical endpoints.
  - Streams: continuous feature or signal flows (e.g., NVM output, BowlNet features).
- **Routing, authorization, and identity** for participants (services, devices, bowls, NVM nodes).
- **Observation and introspection** of flows (monitoring, replay, provenance).

ArqonBus is not responsible for:

- The internal numerical details of NVM, ITMD, or BowlNet algorithms.  
- User-facing UI products (dashboards, IDEs) beyond minimal reference tooling.  
- Long-term archival storage (it can integrate with storage, but is not storage).

## 5. Architectural Tenets

1. **Message-As-Program**
   - A message may be:
     - A simple event, or
     - A **program capsule**: code + parameters + constraints.  
   - Program capsules must:
     - Declare their **runtime/environment** (`nvm`, `bowlnet`, `wasm`, `python`).
     - Declare **resource caps** (time, memory, I/O, hardware usage).
     - Be **hash-addressable** and versioned.

2. **Dual Plane: Control vs. Data**
   - **Control plane**: configuration, topology, auth, capabilities, schemas.  
   - **Data plane**: actual events, jobs, and streams.  
   - The websocket bus exposes both, but treats them as distinct **topics / channels**.

3. **Topic & Circuit Model**
   - Topics are **semantic channels** (e.g., `nvm.jobs`, `bowlnet.features`, `pacf.streams`).  
   - Circuits are **composed routes**: DAGs or pipelines of topics and services (e.g., “ingest audio → NVM pulse → BowlNet features → classifier → archive”).

4. **Physical Operators as First-Class Endpoints**
   - Each physical or virtual operator (bowl, optical path, NVM rig) has:
     - A **canonical identifier** and capability descriptor.
     - A **digital proxy** attached to the bus (agent or sidecar).
   - Jobs sent over the bus are executed by these proxies, which mediate between digital messages and physical operations.

5. **Causal & Event-Driven Semantics**
   - The preferred pattern is **event-driven propagation of deltas** (ITMD style),
     not polling or bulk dumps.  
   - State is modeled as a **cached summary**; messages carry diffs and observations.

## 6. Security & Trust Principles

1. **Zero-Trust Default**
   - Every connection, service, and endpoint is authenticated and authorized; there are no implicit “trusted” zones.

2. **Capability-Based Permissions**
   - Endpoints receive narrow, explicit capabilities (e.g., “can dispatch NVM jobs within namespace X with energy cap Y”), not broad roles.

3. **Auditability**
   - Every program capsule and physical execution is logged with:
     - Input hashes and schemas.
     - Output hashes and statistics.
     - Execution environment fingerprints (software version, hardware identity).

4. **Safe Experimentation**
   - The bus must support **playground / research namespaces** where experimental logic can run with tight caps, easy teardown, and strong isolation from production.

## 7. Evolution & Governance

1. **Versioned Protocol & Schemas**
   - All wire formats and schemas are **explicitly versioned** (`arqonbus/1.x`, `job.v1`, `stream.v2`).  
   - Breaking changes require **migration paths** and coexistence periods.

2. **Reference Implementations**
   - At least one open-source reference server and client SDKs (Python first) must always exist and track the spec.

3. **Research-to-Production Bridge**
   - New capabilities proven in notebooks (NVM, BowlNet, QML POCs) should graduate through a standard path:
     - Notebook prototype → internal ArqonBus “experimental topic” → hardened operator spec → documented production capability.

4. **Community & External Standards**
   - Where possible, ArqonBus message formats should align with or extend existing standards (IETF/JSON, CBOR, gRPC-like schemas) rather than inventing bespoke formats without need.

## 8. Success Criteria

ArqonBus is successful when:

- A developer can **connect a websocket client**, dispatch an NVM job or BowlNet feature pipeline, and see traceable results with < 30 minutes of onboarding.
- Physical and virtual compute backends can be **added or swapped** with minimal changes to clients, via capability descriptors and topic configuration.
- The bus can **sustain high-throughput, low-latency** flows for digital-only workloads and gracefully extend to slower, high-value physical workloads.
- The system’s behavior is **legible and auditable**: we can explain, reproduce, and reason about any computation path that flows through the bus.
