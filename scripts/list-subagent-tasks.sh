#!/bin/bash
# List all active subagent tasks for DisPinMap development
# Usage: ./list-subagent-tasks.sh [--detailed]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SUBAGENT_DIR="$PROJECT_ROOT/claude-worktrees/subagent-tasks"

list_subagent_tasks() {
    local detailed=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --detailed|-d)
                detailed=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [--detailed]"
                echo ""
                echo "List all active subagent tasks"
                echo ""
                echo "Options:"
                echo "  --detailed, -d    Show detailed task information"
                echo "  --help, -h        Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    echo "🤖 Subagent Task Status"
    echo "======================="
    echo ""

    if [[ ! -d "$SUBAGENT_DIR" ]]; then
        echo "No subagent tasks directory found."
        echo "Create one with: $SCRIPT_DIR/create-subagent-worktree.sh <task-name>"
        exit 0
    fi

    local task_count=0
    local active_count=0

    # List all task directories
    for task_dir in "$SUBAGENT_DIR"/*; do
        if [[ -d "$task_dir" && "$(basename "$task_dir")" != ".*" ]]; then
            local task_name=$(basename "$task_dir")
            task_count=$((task_count + 1))

            # Check if it's a valid worktree
            if [[ -f "$task_dir/.git" ]]; then
                active_count=$((active_count + 1))

                echo "📋 Task: $task_name"

                # Get basic info
                cd "$task_dir"
                local current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
                local commit_count=$(git rev-list --count HEAD ^main 2>/dev/null || echo "0")
                local has_changes="No"
                if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
                    has_changes="Yes"
                fi

                echo "  Branch: $current_branch"
                echo "  Commits ahead of main: $commit_count"
                echo "  Uncommitted changes: $has_changes"

                # Show detailed info if requested
                if [[ "$detailed" == "true" ]]; then
                    echo "  Path: $task_dir"

                    # Read metadata if exists
                    if [[ -f "$task_dir/.subagent-task.json" ]]; then
                        local created_at=$(jq -r '.created_at // "unknown"' "$task_dir/.subagent-task.json" 2>/dev/null || echo "unknown")
                        local description=$(jq -r '.description // "No description"' "$task_dir/.subagent-task.json" 2>/dev/null || echo "No description")
                        echo "  Created: $created_at"
                        echo "  Description: $description"
                    fi

                    # Show recent commits
                    echo "  Recent commits:"
                    git log --oneline -3 2>/dev/null | sed 's/^/    /' || echo "    No commits"
                fi

                echo ""
            else
                echo "⚠️  Invalid task directory: $task_name (not a worktree)"
                echo ""
            fi
        fi
    done

    # Summary
    echo "📊 Summary:"
    echo "  Total task directories: $task_count"
    echo "  Active worktrees: $active_count"

    if [[ $active_count -eq 0 ]]; then
        echo ""
        echo "No active subagent tasks. Create one with:"
        echo "  $SCRIPT_DIR/create-subagent-worktree.sh <task-name>"
    fi

    # Show task registry if exists
    if [[ -f "$SUBAGENT_DIR/.task-registry" ]]; then
        echo ""
        echo "📝 Task Registry:"
        while IFS=':' read -r task_name status timestamp; do
            echo "  $task_name ($status) - $timestamp"
        done < "$SUBAGENT_DIR/.task-registry"
    fi
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    list_subagent_tasks "$@"
fi
