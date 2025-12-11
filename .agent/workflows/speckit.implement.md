---
description: Execute the implementation plan from tasks.md. Usage: /speckit.implement
---

1. Verify environment prerequisites.
// turbo
2. Run the following command:
   ```bash
   .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
   ```
3. If prerequisites pass:
   - Check status of checklists in `checklists/` directory (if existing).
   - If checklists pass or user overrides:
     - Read `tasks.md`, `plan.md`, and available design docs (`data-model.md`, etc).
4. **Execute the Implementation Loop**:
   - For each phase in `tasks.md`:
     - Run the tasks sequentially (or parallel if marked `[P]`).
     - **For Code Tasks**: Write the code, then run tests.
     - **For Test Tasks**: specificy/run the tests.
     - Mark tasks as `[x]` in `tasks.md` upon completion.
   - **Crucial**: Update `task_boundary` tools effectively to reflect the `tasks.md` progress.
