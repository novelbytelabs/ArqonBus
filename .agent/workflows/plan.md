---
description: Execute the implementation planning workflow. Usage: /speckit.plan [description]
---

1. Execute the setup script to initialize the plan context.
// turbo
2. Run the following command (Replace "$ARGUMENTS" with the actual user input string):
   ```bash
   .specify/scripts/bash/setup-plan.sh --json
   ```
3. Read the output from the script (which provides `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, and `BRANCH`).
4. Load the Feature Spec (from the path in output) and `.specify/memory/constitution.md`.
5. Open the Implementation Plan file (from the path in output).
6. Proceed to fill out the Implementation Plan following the `IMPL_PLAN` template structure:
   - Fill Technical Context.
   - Perform Constitution Check.
   - Generate `research.md` (Phase 0) if clarifications are needed.
   - Update `data-model.md` and `contracts/` (Phase 1).
   - Run `.specify/scripts/bash/update-agent-context.sh gemini` to sync context.
