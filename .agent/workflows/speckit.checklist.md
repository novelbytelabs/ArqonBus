---
description: Generate a quality checklist for a feature or domain. Usage: /speckit.checklist [domain/feature]
---

1. Identify the target domain or feature from the arguments.
2. Load the appropriate checklist template (e.g., `.specify/templates/checklist-template.md` or similar).
3. If no specific template exists, create a new checklist file at `docs/ArqonBus/checklists/[domain]_checklist.md`.
4. Populate the checklist with:
   - **Content Quality**: No implementation details, clear value.
   - **Requirement Completeness**: Testable, unambiguous.
   - **Feature Readiness**: Scenarios defined, success criteria measurable.
5. Notify the user of the created checklist.
