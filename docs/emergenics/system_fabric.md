# System & Computational Fabric Stack – Summary & ArqonBus vNext Hooks

This note distills `ash/12_System` and surfaces patterns relevant to ArqonBus vNext.

Sources sampled (Emergenics repo):
- `Computational_Fabric/ComputationalFabric_00.ipynb`
- `System_Specs/System-Formal-Specification.ipynb`
- `Research/01_Structure_Dynamics/01_structure_dynamics.ipynb`
- `Research/02_Memory_Signal_Differentiation/02_memory_and_signal_differentiation.ipynb`
- `Research/03_Advanced_Readout_Strategies/03_advanced_readout_strategies.ipynb`
- `Research/04_Memory_Substrate_Discovery/04_memory_substrate_discovery.ipynb`
- `Research/05_Node_Memory_Dynamics/05_node_memory_dynamics.ipynb`
- `Research/06_Overlap_Interference_Test/06_overlap_interference_test.ipynb`
- `Research/07_Capacity_Landscape_Mapping/07_capacity_landscape_mapping.ipynb`
- `Research/08_Gated_Memory_Substrate/08_gated_memory_substrate.ipynb`
- `Research/09_Memory_Feedback_Strength/09_memory_feedback_strength.ipynb`
- `Research/10_10_feedback_ablation_test/10_feedback_ablation_test.ipynb`

---

## 1. What we just read (this chunk)

- **ComputationalFabric_00.ipynb**  
  - Sets up the computational fabric over three graph families:
    - Watts–Strogatz, stochastic block model, and random geometric graphs.
  - Defines simulation parameters (nodes, steps, noise, connectivity) and saves them for reproducibility.

- **System-Formal-Specification.ipynb**  
  - Gives a precise, formal definition of the **Oscillator** and **Network State**:
    - Each node has a state vector \(\vec{s}_i(t) = (s_\tau, s_\rho, s_\delta)\) and an accumulator \(a_i(t)\).
    - The network state \(NS(t)\) is the collection of all oscillator states.  
  - Defines deterministic operators:
    - **Evolution operator \(F\)**: updates \(\vec{s}_i\) and \(a_i\) using local interactions, inputs, and a fold map.
    - **SYNC**: computes the mean state over all nodes.
    - **Update-to-Mean \(U\)**: moves each node’s state toward the global mean with strength \(\alpha\).
    - **Threshold-Spike \(T\)**: produces spikes and resets accumulators based on a threshold.  
  - Composes these into a single, stepwise transition rule for the entire network.

- **Research notebooks 01–10**  
  - **01_structure_dynamics**:
    - Starts from a majority-rule automaton (null result: too stable).
    - Introduces a richer **Harmonic Automaton** with local oscillators and edge memory.
    - Shows:
      - Network structure (p) controls self-organization.
      - Noise (σ) sustains an “edge of chaos” regime.
      - The fabric, in this regime, responds measurably to localized inputs (basic information processing).
  - **02_memory_and_signal_differentiation**:
    - Distinguishes true memory from transient signal in the fabric’s dynamics.
  - **03_advanced_readout_strategies**:
    - Explores readout mechanisms beyond simple global averages for extracting useful signals from the fabric.
  - **04_memory_substrate_discovery & 05_node_memory_dynamics**:
    - Identify parameter regimes where the fabric supports robust memory.
    - Characterize per-node memory decay and retention.
  - **06_overlap_interference_test & 07_capacity_landscape_mapping**:
    - Study interference between overlapping memories.
    - Map capacity landscapes vs parameters to find operational “sweet spots”.
  - **08_gated_memory_substrate**:
    - Introduces gating mechanisms for controlling when/whether memory is written/read.
- **09_memory_feedback_strength & 10_feedback_ablation_test**:
    - Analyze the role of **memory feedback gain** \(\gamma\):
      - Identify a sharp phase transition at a critical \(\gamma_c \approx 0.0294\).
      - Below \(\gamma_c\): catastrophic interference; above \(\gamma_c\): high recall fidelity and robust performance largely insensitive to exact \(\gamma\).

---

## 1.1 Competitive Memory (ash/17_memory)

- **11_comp_write.ipynb & 12_residual_analysis.ipynb** (competitive memory, structural pass)
  - Extend the system-fabric work by:
    - Studying **competitive write dynamics**: how different patterns or sources compete to claim or overwrite shared memory in the fabric.
    - Analyzing **residual structure** in what remains after multiple writes: which traces persist, how interference manifests, and how competition changes effective capacity.
  - Conceptually:
    - Treat memory as a **shared, contested resource** on top of the fabric.
    - Highlight that write policies (who writes, when, and with what priority) are as important as the raw storage substrate.

---

## 2. Key lessons and ArqonBus impact

### 2.1 System-as-fabric and operator layering

- The 12_System stack formalizes a **computational fabric** as:
  - A graph of oscillatory nodes.
  - Deterministic local and global operators (F, SYNC, U, T).
  - An explicit separation between substrate, dynamics, and readout.
- For ArqonBus:
  - Reinforces our existing **Shield/Spine/Brain/Storage** layering as a fabric:
    - Nodes (operators/services) with internal state.
    - Network-level “SYNC/U” operators (controllers) that aggregate and redistribute state.
    - Readout operators that convert fabric behavior into user-visible signals or control actions.

### 2.2 Edge-of-chaos as an operational regime

- The Harmonic Automaton results show:
  - Network topology and noise jointly define regimes: ordered, chaotic, and “edge-of-chaos”.
  - Only the edge-of-chaos regime supports responsive computation (fabric responds to localized inputs).
- For ArqonBus:
  - Edge-of-chaos is an analogy for:
    - Operating clusters and circuits in a region where they are neither locked nor thrashing.
  - Ω-tier controllers may:
    - Monitor load/latency/variance to keep clusters in a “responsive” window.
    - Treat too-stable or too-chaotic regimes as operational smells.

### 2.3 Memory as a fabric property with critical feedback

- The memory notebooks establish:
  - **Node-centric, leaky memory** plus **feedback** is required for robust recall.
  - There exists a critical feedback threshold \(\gamma_c\) separating failure from success.
- For ArqonBus:
  - Suggests:
    - Treating long-lived state as a **fabric-level property** (cluster+cache+protocol), not just as isolated DB configs.
    - Recognizing **critical thresholds** (feedback strength, replication factors, consistency settings) where system behavior changes qualitatively.

**Competitive memory extension (from ash/17_memory)**

- Competitive write/residual analysis suggests:
  - Memory pressure is not only about total capacity, but about **how many independent writers compete** and how their patterns overlap.
  - Certain write strategies (e.g., gated, prioritized, or sparsified writes) preserve more useful structure than naïve, always-on writes.
- For ArqonBus vNext:
  - Encourages designs where:
    - **Stateful operators** and storage backends expose and enforce clear write policies (e.g., priority classes, quotas, or admission control).
    - Controllers consider **who is allowed to write to shared state**, not just read from it.
    - Residual-structure metrics (how much useful configuration/memory remains after heavy churn) can become part of observability for stateful circuits.

### 2.4 Readouts and gating as first-class concerns

- The work on advanced readouts and gating shows:
  - Extracting useful information requires carefully designed readouts, not just raw metrics.
  - Gating is essential to avoid interference and to protect memory.
- For ArqonBus:
  - Supports the design of:
    - **Structured readout operators** (dashboards, SLO evaluators, anomaly detectors) that see the fabric through intentional views.
    - **Gating mechanisms** at the bus level (e.g., limiting write paths, controlling which flows can influence long-lived state).

---

## 3. Updates applied to the docs

- **Added** `docs/emergenics/system_fabric.md`  
  - Summarizes the System/Computational Fabric stack:
    - Formal specification of oscillator and network state.
    - Harmonic Automaton and edge-of-chaos computational fabric.
    - Memory substrate discovery, capacity mapping, gating, and feedback thresholds.  
  - Extracts ArqonBus vNext hooks:
    - Viewing ArqonBus itself as a layered computational fabric.
    - Using edge-of-chaos analogies to guide operational regimes.
    - Treating memory as a fabric property with critical thresholds.
    - Emphasizing structured readouts and gating for safe, robust operation.  
- `docs/emergenics/source_registry.md` has been updated with a dedicated `ash/12_System` section listing all sampled notebooks and data paths.
