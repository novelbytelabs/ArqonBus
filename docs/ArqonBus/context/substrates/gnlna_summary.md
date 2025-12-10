# GNLNA / NLCA Technology Summary (for ArqonBus)

This document summarizes the core GNLNA substrate work (beyond the demos) and how it informs future ArqonBus design.

---

## 1. GNLNA_Exploration_01.ipynb – Generalized Non-Local Network Automata

**Summary**

- Extends 1D/2D NLCA work to **arbitrary graphs** (network automata).
- Defines a GNLNA via:
  - A **local layer**: adjacency of a base graph \(G\) → \(M_{\text{local}}\).
  - A **non-local layer**: a rule \(P\) (e.g., k-hop interactions) → \(P_{\text{offset}}\).
  - A combined update rule:
    \[
      M = (M_{\text{local}} + P_{\text{offset}}) \mod 2
    \]
- The notebook:
  - Formalizes GNLNA simulation on diverse graph generators (Watts–Strogatz, SBM, random regular, Barabási–Albert).
  - Explores how the interplay of local topology \(\Phi\) (properties of \(G\)) and non-local rule \(P\) shapes the attractor landscape \(\Omega\).
  - Tests whether adding non-local structure restores the tractable, engineerable dynamics seen on regular grids.

**ArqonBus Hooks**

- **Graph-embedded emergent operators**
  - Demonstrates that emergence engineering naturally extends to **irregular network topologies**, not just grids.
  - For ArqonBus:
    - Reinforces that future emergent operators may be tied to graph-shaped fabrics (e.g., social graphs, service graphs, communication networks).
    - Suggests we may eventually want to tag operators with **graph/topology descriptors** (or at least support operators whose internal model is a non-grid graph).

- **Topology + non-local rule as configuration**
  - GNLNA’s behavior depends on both the base graph and the non-local rule schedule.
  - For ArqonBus:
    - Encourages viewing some operators’ configs as **(topology, non-local rule)** pairs — and perhaps exposing both pieces in config topics or job payloads.

---

## 2. NLCA / GNLNA Pattern (Collective)

The NLCA_* notebooks (1D, 2D, Multiscale, State‑Dependent) reinforce and refine a common pattern:

- **Local vs Non-Local Layers**
  - A local adjacency (grid or graph) plus a non-local interaction rule combine to define the update operator.

- **Linear Backbone + Optional Nonlinearity**
  - A GF(2) linear layer is often the backbone; nonlinearities (AND/OR, state thresholds) are introduced surgically where needed.

- **Time-Varying and State-Dependent Rules**
  - Rules can vary in time (schedules) and in response to state (state-dependent feedback, k_persist).

Additional specifics from these dirs:

- **2D_NLCA_Exploration_01.ipynb**
  - Generalizes 1D NLCA to 2D grids:
    - Grid states flattened to vectors.
    - Local rules become **block-circulant matrices** over GF(2).
    - Non-local interactions are added as structured taps or shifts across the grid.
  - Focuses on mapping out “law space” (attractors) and identifying tractable 2D subspaces where linear methods still help.

- **NLCA_Multiscale_01.ipynb**
  - Builds **multiscale NLCAs**: coarse and fine grids (or layers) with interactions across scales.
  - Demonstrates how hierarchical structure changes attractors and control; suggests multiscale control levers.

- **NLCA_State_Dependent_01.ipynb**
  - Implements **state-dependent rules** on 2D grids:
    - Hamming-weight-based switching between different P_t matrices.
    - Persistent switching (k_persist) vs instantaneous switching.
  - Shows:
    - A nontrivial baseline rule (“Product_P_Cycle”) giving predictable cycles.
    - Adaptive rules that drive systems from complex dynamics to fixed points (homeostasis), and that this behavior scales to larger grids.

**ArqonBus Hooks**

- **Operator configuration as a multi-part object**
  - For emergent operators, “configuration” is not a flat blob; it may include:
    - Topology (graph or grid).
    - Local rule parameters.
    - Non-local rule definitions.
    - Schedules and timescales.
  - ArqonBus schemas for such operators should anticipate this multi-part structure rather than a single opaque config string.

- **Linear + nonlinear sub-modes**
  - The linear backbone is algebraically tractable; nonlinear elements define where “hard” emergence enters.
  - For ArqonBus:
    - Suggests we might eventually encode in operator metadata whether an operator is **fully linear**, **linear + localized nonlinearities**, or **strongly nonlinear**, to inform routing, safety, and expectations.

---

## 3. ArqonBus Design Takeaways from GNLNA Core

From the core GNLNA substrate work we add three more concrete design considerations for ArqonBus:

1. **Graph-Aware Emergent Operators**
   - ArqonBus should remain agnostic about internal topology, but the spec should not assume “grid-only” or “stateless-only” operators.
   - Future emergent operators may naturally be **graph-embedded** (and may even align with the service graph that ArqonBus orchestrates).

2. **Rich Configuration Objects**
   - For emergent operators, configs may be structured as (topology, local rule, non-local rule, schedule, timescale).
   - ArqonBus message schemas should be comfortable with **nested configuration structures** for such operators, not just flat key-value maps.

3. **Operator Metadata about Structure and Regimes**
   - Even if the bus does not understand the internal math, it can benefit from metadata such as:
     - “has_nonlocal_layer: true/false”
     - “uses_graph_topology: true/false”
     - “nonlinearity_mode: linear / localized / strong”
   - This information can feed future governance, routing decisions, and safety tooling.

---

## 4. GNLNA_Causal_Discovery_01.ipynb – Causal Graph Discovery

**Summary**

- Frames **GNLNA structure discovery** (recovering the total evolution matrix `M`) as a regression problem:
  - Generate synthetic time-series from a known sparse `M` (ground-truth GNLNA).
  - For each node i, treat predicting \(s_i(t+1)\) from \(s(t)\) as a logistic regression problem.
  - Use L1-regularized (LASSO) logistic regression so most coefficients go to zero; non-zero coefficients correspond to non-zero entries in the true row of `M`.
- Shows that for sparse, static `M` and enough data, you can **reverse-engineer the causal graph** underlying an emergent fabric.

**ArqonBus Hooks**

- **Causal discovery operators**
  - Suggests a future operator that, given time-series streams from another operator, infers:
    - A sparse structural model of its interactions (approximate `M` or adjacency).
  - On ArqonBus, such an operator could:
    - Subscribe to state telemetry from a substrate operator.
    - Publish inferred structure or model summaries for debugging, safety review, or automatic design.

---

## 5. GNLNA_Feedback_Control_01.ipynb – Feedback Control Patterns

**Summary**

- Implements a **FeedbackController** for a noisy GNLNA:
  - Observes current state vs. a target/ideal state.
  - Computes an error (Hamming distance).
  - Chooses between:
    - A “standard” evolution matrix (e.g., random permutation) when error is small.
    - A corrective matrix (identity) when error exceeds a threshold.
- Encodes a clear control pattern:
  - When deviation is too large, temporarily override normal dynamics with **corrective dynamics** until the system is back in bounds.

**ArqonBus Hooks**

- **Feedback controller operators**
  - Mirrors the Actor–Controller pattern:
    - Controller operators consume error metrics and push mode/parameter changes back to substrate operators.
  - For ArqonBus:
    - Reinforces the value of:
      - Explicit error thresholds and control modes in operator configs.
      - Control topics that can switch operators between “normal” and “corrective” behavior.

---

## 6. GNLNA_Continuous_Time_01.ipynb – Continuous-Time Generalization

**Summary**

- Extends emergence engineering from discrete-time GF(2) updates to **continuous-time systems over ℝ**:
  - Discrete rule \(s_{t+1} = M s_t\) becomes \( \frac{ds}{dt} = L s(t)\) with \(L = A_{\text{loc}} + P\).
  - Links the **rank of \(L\)** to the dimension of the stable subspace: rank \(N-1\) ⇒ unique non-trivial stable state.
- Explores how design principles from discrete GNLNA (structured A_loc and P) carry over to engineering target stability in continuous-time.

**ArqonBus Hooks**

- **Continuous-time substrate operators**
  - Suggests operators whose internal dynamics are continuous-time systems (ODEs, neural fields, etc.).
  - For ArqonBus:
    - We should not assume all operators are discrete-step; some may expose continuous-time models with discretized interfaces for the bus.

---

## 7. Hypergraph_Automata_Emergence_01.ipynb – Hypergraph Fabrics

**Summary**

- Investigates **hypergraph automata**, where interactions are higher-order (k-way) rather than pairwise:
  - Uses incidence matrices \(B\) and node-centric evolution \(M_V = B B^T\).
  - Shows that moving from graphs (k=2) to hypergraphs (k≥3) fundamentally changes the algebraic properties and rank behavior.
- Key findings:
  - Many control strategies that work on graphs (non-local permutations, dynamic perfect matching analogues) **fail** for hypergraphs.
  - A single robust path to controllability is identified: eliminate local hypergraph structure and drive evolution via sequences of non-local permutations.

**ArqonBus Hooks**

- **Higher-order interaction awareness**
  - Hypergraphs represent a more challenging class of emergent substrate.
  - For ArqonBus:
    - Signals that future emergent operators may involve higher-order interactions that are harder to control; such operators should likely be treated as higher-tier (more restricted) in governance.
