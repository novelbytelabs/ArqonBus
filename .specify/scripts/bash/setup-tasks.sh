#!/usr/bin/env bash

set -e

# Parse command line arguments
JSON_MODE=false
ARGS=()

for arg in "$@"; do
    case "$arg" in
        --json) 
            JSON_MODE=true 
            ;;
        --help|-h) 
            echo "Usage: $0 [--json]"
            echo "  --json    Output results in JSON format"
            echo "  --help    Show this help message"
            exit 0 
            ;;
        *) 
            ARGS+=("$arg") 
            ;;
    esac
done

# Get script directory and load common functions
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get all paths and variables from common functions
eval $(get_feature_paths)

# Check if we're on a proper feature branch (only for git repos)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

# Template handling
# We use a simple task list template if one exists, or create a blank one
TEMPLATE="$REPO_ROOT/.specify/templates/tasks-template.md"
if [[ -f "$TEMPLATE" ]]; then
    # Only copy if TASKS doesn't exist to avoid overwriting work
    if [[ ! -f "$TASKS" ]]; then
        cp "$TEMPLATE" "$TASKS"
        echo "Copied tasks template to $TASKS"
    fi
else
    if [[ ! -f "$TASKS" ]]; then
        # Create a basic plan file if template doesn't exist
        echo "# Task List: $FEATURE_NAME" > "$TASKS"
        echo "" >> "$TASKS"
        echo "**Goal**: Execute the Implementation Plan." >> "$TASKS"
        echo "" >> "$TASKS"
        echo "## Todo" >> "$TASKS"
        echo "" >> "$TASKS"
    fi
fi

# Output results
if $JSON_MODE; then
    # We output the IMPL_PLAN as context for the agent to read
    printf '{"TASKS_FILE":"%s","IMPL_PLAN":"%s","FEATURE_SPEC":"%s","BRANCH":"%s"}\n' \
        "$TASKS" "$IMPL_PLAN" "$FEATURE_SPEC" "$CURRENT_BRANCH"
else
    echo "TASKS_FILE: $TASKS"
    echo "IMPL_PLAN: $IMPL_PLAN"
    echo "FEATURE_SPEC: $FEATURE_SPEC" 
    echo "BRANCH: $CURRENT_BRANCH"
fi
