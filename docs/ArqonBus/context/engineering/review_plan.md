# ArqonBus Source Review Plan

This document defines how we will systematically read **every document and directory** in this repo and continuously fold the insights into ArqonBus.

The goal is not just coverage, but a **running, evolving plan** for ArqonBus that stays in sync with the full body of work.

---

## 0. Emoji Legend (Progress at a Glance)

- ✅ reviewed (reflected into ArqonBus where relevant)
- 🟡 in_progress (partially read or mid-reflection)
- ⏳ queued (identified but not yet read)
- 🔁 revisit (needs re-read after major ArqonBus changes)
- ❗ critical (high impact / must-integrate soon)

We’ll use these in the tracking table to make scan-level progress visible.

---

## 1. Objectives

- Build a **complete mental map** of the repo as it relates to ArqonBus.
- Ensure **no important idea is stranded** in notebooks, archives, or demos.
- Maintain a **living ArqonBus plan** (constitution, spec, roadmap, designs) under `docs/projects/novelbytelabs/arqonbus`.
- Track review status so we always know:
    - What has been read.
    - What’s in progress.
    - What still needs reflection / integration.

---

## 2. Scope

We will review, in a structured way:

- `docs/` — all narrative documentation, archives, future directions, and summaries.  
- `dev/QuantumHyperEngine/` — core NVM, research notebooks, demos, and snippets.  
- `production/`, `staging/`, `README.md`, `requirements.txt`, and any other top-level project docs.  

Non-text binaries (audio, images, frames) are in-scope **conceptually** (what they demonstrate and how they’re used) but not for line-by-line reading.

---

## 3. Phased Review Strategy

### Phase 1 — Inventory & Categorization

1. Generate a file inventory (one time, refreshed as needed) using `find` over:
     - `docs/`
     - `dev/QuantumHyperEngine/`
     - other top-level paths as needed.
2. Categorize each path into coarse buckets:
     - `theory` (ITMD, PAL, Shannon/Kolmogorov, philosophy).
     - `nvm_core` (Number Virtual Machine, pulses, FEC).
     - `quantum` (NVM quantum computing, teleportation, distributed).
     - `acoustic_bowls / BowlNet / Phonic ROM`.
     - `qml` (QML POCs, VQE, hybrid).
     - `benchmarks / performance`.
     - `archive_journal` (dated logs and code snippets).
     - `infra / tooling` (deployment, services, configs).
3. Record this inventory and category in a **tracking table** (see §4).

### Phase 2 — Category-First Reading

4. Pick one category at a time (e.g., `theory`) and review all its files:
     - Read or skim documents depending on size.
     - For notebooks, focus on **intro, conclusions, and key code cells** that define behaviors or architectures.
5. For each file, write a **short ArqonBus reflection** (2–5 bullet points):
     - What does this file teach us about messages, operators, protocols, or circuits?
     - Does it suggest a new ArqonBus capability, pattern, or constraint?
     - Does it challenge or refine anything in the constitution/spec?

### Phase 3 — Integration into ArqonBus Docs

6. As reflections accumulate, update the ArqonBus docs under `docs/projects/novelbytelabs/arqonbus/`:
     - `constitution.md` — only when core principles or values shift.
     - `specification.md` — when we clarify or add concrete product behavior.
     - New design notes (e.g., `design_nvm_operators.md`, `design_bowlnet_streams.md`) for deeper topics.
7. Aim to keep **high-level docs stable**, and push detailed insights into:
     - Design notes.
     - Examples.
     - Operator-specific specs.

### Phase 4 — Full Coverage & Periodic Sweeps

8. Continue until **every file in the tracking table** has:
     - A category.
     - A review status of `reviewed`.
     - At least one ArqonBus reflection entry.
9. On a regular cadence (e.g., weekly), run a **short sweep**:
     - Check for new or changed files.
     - Revisit any areas where ArqonBus design has shifted significantly and ensure older insights still fit.

---

## 4. Tracking Table (Living)

The full, growing tracking table now lives in `docs/projects/novelbytelabs/arqonbus/source_registry.md`.

Use that registry to:

- Add new rows as you review files/notebooks.
- Update statuses (⏳ → 🟡 → ✅) and notes.
- Drive which areas we focus on next in this plan.

---

## 5. Reflection Pattern for Each File

For each document/notebook reviewed, follow a consistent template in your notes:

1. **Summary (1–3 sentences):**  
   What is this artifact about?

2. **Key Concepts:**  
   Short bullets for the main technical or conceptual ideas.

3. **ArqonBus Impact:**  
     - Does this influence message shapes, topics, operators, or circuits?
     - Does it inform security, observability, or resource constraints?
     - Does it suggest a new product feature or mode?

4. **Actions (choose one or more):**  
     - Update `specification.md` section X.  
     - Add a new operator design note.  
     - Add an example or tutorial.  
     - No immediate change; just record the insight.

These reflections can live:

- Inline in the tracking table’s “ArqonBus Notes” column, and/or
- In dedicated design docs grouped by area.

---

## 6. Keeping Documentation Centralized

To honor the constraint that **all ArqonBus documentation lives under `docs/projects/novelbytelabs`**:

- Put all ArqonBus-specific docs in `docs/projects/novelbytelabs/arqonbus/`.
- When a reflection suggests a change elsewhere (e.g., in `docs/NVMaaS/...`), update those docs as needed but **record the ArqonBus-facing impact** back here:
    - A short note in the tracking table.
    - A pointer from the relevant ArqonBus design note.

This keeps ArqonBus as a coherent “view” over the entire repo.

---

## 7. Working Rhythm

Suggested daily/weekly workflow:

1. Pick a small batch of paths from the tracking table.
2. Read and reflect, updating:
     - Status.
     - ArqonBus Notes.
3. Apply any high-value updates to:
     - `constitution.md` (sparingly).
     - `specification.md`.
     - New or existing design docs.
4. Commit changes with clear messages (e.g., `docs: integrate NVM quantum notebook into ArqonBus plan`).

Over time, this rhythm will converge to **full coverage** and a deeply integrated ArqonBus design grounded in every part of the QuantumHyperEngine.

---

## 8. Directory Priority Roadmap

To make the review tractable, we will progress in **stages**, always looping: read a chunk → reflect → update `constitution.md`, `specification.md`, and this `review_plan.md`.

### Stage 1 — Product & Narrative Spine (Highest Priority)

Goal: understand the **product vision, timelines, and commercial framing** that ArqonBus must support.

- `docs/projects/novelbytelabs/`

       - `future_directions.md` ✅
       - ArqonBus docs (this folder) 🟡

- `docs/projects/helios/`
  
       - `summary.md` ✅
       - `phases.md` ✅

- `docs/archive/august/`

       - Focus on **August 10–31** ✅ (08-10, 08-15, 08-18, 08-19, 08-20, 08-21, 08-22, 08-23, 08-25, 08-27 reviewed)

### Stage 2 — Core Engines & Physical Compute

Goal: fully map the **computational substrates** ArqonBus will orchestrate.

- `dev/QuantumHyperEngine/core/`
       - `NVM_CORE/` ✅
       - any Helios/ITMD core engine modules ⏳
- `dev/QuantumHyperEngine/research/Quantum/`
       - `1_NVM_Quantum_Computing/` ✅
       - `2_NVM_Quantum_State_Teleportation/` ✅
       - `3_NVM_Distributed_Quantum_Computation/` ✅
       - `4_Hybrid_VQE_with_QTR_backend/` ✅
       - `5_QML_POC/` ✅
- `docs/archive/august/08-10-2025*.md` ✅ (BowlNet, Phonic ROM)

### Stage 3 — Demos, Benchmarks, and Tooling

Goal: capture **real-world usage patterns** and performance assumptions.

- `dev/QuantumHyperEngine/demos/` ✅
- `dev/QuantumHyperEngine/snippets/` ✅
- `docs/archive/july/` ✅ (earlier context, benchmarks, and narrative)

### Stage 4 — Infra, Deployment, and Edges

Goal: understand how ArqonBus will sit inside real systems and services.

- `production/` ✅
- `staging/` ✅
- `requirements.txt` ✅
- `README.md` ✅

As we progress:

- We will move folders/files from ⏳ → 🟡 → ✅ in the tracking table.  
- After completing a stage, we’ll do a quick **constitution/spec review pass** to see if any deep principle or major product feature needs updating before moving on.
