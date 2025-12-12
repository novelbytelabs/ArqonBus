---
description: Create a new feature spec using the Speckit workflow. Usage: /specify [description]
---

1. Execute the creation script with the user's prompt.
// turbo
2. Run the following command (Replace "$ARGUMENTS" with the actual user input string):
   ```bash
   .specify/scripts/bash/create-new-feature.sh --json "$ARGUMENTS"
   ```
3. Read the JSON output from the command to identify the new branch and spec file path.
4. If the script output JSON, proceed to edit the file specified in `SPEC_FILE` using the `run_command` output as the source of truth.
