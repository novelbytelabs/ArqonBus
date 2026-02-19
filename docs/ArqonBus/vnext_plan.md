# ArqonBus vNext: Documentation Strategy (SDD)

This plan defines how we will organize the ArqonBus vNext documentation to align with the **Spec-Kit** (Spec-Driven Development) methodology.

## 1. The Core Philosophy
We follow the **Spec-Kit Workflow**:

1.  **Specify (The What):** Define the product requirements and boundaries FIRST.
2.  **Plan (The How):** Define the technical implementation details SECOND.
3.  **Execute (The Tasks):** Break down the plan into checklists LAST.

All documentation will live in `docs/ArqonBus/` and mirror this flow.

## 2. Directory Structure Plan

We will organize `docs/ArqonBus/` as follows:

| Directory | Spec-Kit Role | Contents |
| :--- | :--- | :--- |
| `docs/ArqonBus/constitution/` | **The Law** | The non-negotiable constraints (e.g., `constitution_v2.md`). |
| `docs/ArqonBus/spec/` | **The What** | Product Specifications. Deeply detailed, logic-free. (e.g., `spec.md`, `api.proto.md`). |
| `docs/ArqonBus/plan/` | **The How** | Technical Plans. Architecture diagrams, technology choices, `policy_as_code.md`. |
| `docs/ArqonBus/checklist/` | **The Tasks** | Step-by-step checklists derived from the Plan. |
| `docs/ArqonBus/context/` | **The Knowledge** | Mined Emergenics audits (`emergenics_audit.md`), Deep Dives, and Reference material. |
| `docs/ArqonBus/templates/` | **The Tools** | Templates for new Specs, Plans, and ADRs. |

## 3. Migration Actions

### New Files to Create
*   `docs/ArqonBus/spec/00_master_spec.md`: The single source of truth for the vNext Product.
*   `docs/ArqonBus/plan/00_master_plan.md`: The single source of truth for the vNext Architecture.
*   `docs/ArqonBus/context/readme.md`: Index of mined Emergenics knowledge.

### Simplification
*   Consolidate scattered files (e.g., `docs/configuration.md`) into `spec/` or `plan/`.
*   Ensure we do not have duplicate "specs" (e.g., `v1` vs `v2` should be separated or archived).

## 4. The "Living Doc" Contract
*   **No Code without Spec:** We do not write code until `spec/` and `plan/` are updated.
*   **The Spec is the Boss:** If code conflicts with Spec, code is wrong (or Spec must be updated via PR).

## 5. Emergenics Migration Strategy (Context Ingestion)

We will migrate the research notes from `docs/emergenics/` into `docs/ArqonBus/context/` to serve as the **Authoritative Reference** for the Spec.

| Source Category | Files | Destination | Role in Spec |
| :--- | :--- | :--- | :--- |
| **Vision** | `arqonbus_v.md`, `ttc_vision.md`, `system_fabric.md` | `context/vision/` | Defines the **Master Spec** (Architecture). |
| **Substrates** | `nvm.md`, `primes.md`, `frr.md`, `gnlna.md` | `context/substrates/` | Defines **Operator Specs** (e.g., `spec/operators/nvm.md`). |
| **Engineering** | `emergence_eng.md`, `reality_factory.md` | `context/engineering/` | Defines **Operational Specs** (Lifecycle, Safety). |
| **Agents** | `agi.md`, `omega_theory.md`, `ero.md` | `context/agents/` | Defines **Agent Interfaces** (SAM, Capabilities). |
| **Archive** | Demos, old research | `context/archive/` | Historical reference only. |

### Workflow
1.  **Migrate:** Move files to `docs/ArqonBus/context/category/`.
2.  **Synthesize:** Create `spec/00_master_spec.md` referencing `context/vision`.
3.  **Detail:** Create `spec/02_operators.md` referencing `context/substrates`.

## 6. Specification Hierarchy (The Tree)

To "include everything" without creating an unreadable monolith, we will use a **Federated Specification** structure. The Master Spec acts as the Root Node, legally binding the system to the detailed constraints in the `context/` files.

### The Files
*   **`spec/00_master_spec.md` (The Product)**
    *   Defines the Top-Level Vision (Universal Substrate).
    *   **Includes:** `context/vision/arqonbus_vnext.md`
*   **`spec/01_core_spine.md` (The Bus)**
    *   Defines the Kernel (Transport, Identity, Time, CASIL).
    *   **Includes:** `context/vision/ttc_vnext_vision.md`
*   **`spec/02_tier_omega.md` (The Operators)**
    *   Defines the "Substrate Support" requirements (Must host NVM, Primes, etc.).
    *   **Includes:** `context/substrates/*`
*   **`spec/03_reality_factory.md` (The Lifecycle)**
    *   Defines the "Factory" requirements (Promotion Gates, Observatories).
    *   **Includes:** `context/engineering/*`
*   **`spec/04_agents.md` (The Inhabitants)**
    *   Defines the "SAM Interface" and Agent capabilities.
    *   **Includes:** `context/agents/*`

**Rule:** The Spec files define the **Requirements** ("System MUST support X"). The Context files define the **X** ("X is a Prime-Resonant Field...").
