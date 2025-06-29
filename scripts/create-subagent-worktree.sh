#!/bin/bash
# Create a new subagent worktree for DisPinMap development
# Usage: ./create-subagent-worktree.sh <task-name> [base-branch]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SUBAGENT_DIR="$PROJECT_ROOT/claude-worktrees/subagent-tasks"

create_subagent_worktree() {
    local task_name=$1
    local base_branch=${2:-main}

    if [[ -z "$task_name" ]]; then
        echo "Usage: $0 <task-name> [base-branch]"
        echo ""
        echo "Examples:"
        echo "  $0 fix-bug-123"
        echo "  $0 add-logging feature/user-auth"
        echo ""
        echo "This creates:"
        echo "  - Branch: subagent/<task-name>"
        echo "  - Worktree: claude-worktrees/subagent-tasks/<task-name>"
        echo "  - Task metadata file for coordination"
        exit 1
    fi

    local worktree_path="$SUBAGENT_DIR/$task_name"
    local branch_name="subagent/${task_name}"

    # Ensure we're in project root
    cd "$PROJECT_ROOT"

    echo "🤖 Creating subagent worktree..."
    echo "Task name: $task_name"
    echo "Base branch: $base_branch"
    echo "Worktree path: $worktree_path"
    echo "Branch name: $branch_name"
    echo ""

    # Check if base branch exists
    if ! git show-ref --verify --quiet refs/heads/"$base_branch" && ! git show-ref --verify --quiet refs/remotes/origin/"$base_branch"; then
        echo "❌ Error: Base branch '$base_branch' does not exist"
        exit 1
    fi

    # Check if branch already exists
    if git show-ref --verify --quiet refs/heads/"$branch_name"; then
        echo "❌ Error: Branch '$branch_name' already exists"
        echo "To use existing branch: git worktree add '$worktree_path' '$branch_name'"
        exit 1
    fi

    # Check if worktree directory already exists
    if [[ -d "$worktree_path" ]]; then
        echo "❌ Error: Worktree directory '$worktree_path' already exists"
        exit 1
    fi

    # Create worktree with new branch from base branch
    echo "Creating subagent worktree and branch..."
    git worktree add "$worktree_path" -b "$branch_name" "$base_branch"

    if [[ $? -eq 0 ]]; then
        # Create task metadata file
        local task_metadata="$worktree_path/.subagent-task.json"
        cat > "$task_metadata" << EOF
{
  "task_name": "$task_name",
  "branch_name": "$branch_name",
  "base_branch": "$base_branch",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "in_progress",
  "assigned_to": "subagent",
  "worktree_path": "$worktree_path",
  "description": "Subagent task: $task_name",
  "priority": "medium"
}
EOF

        echo "✅ Successfully created subagent worktree!"
        echo ""
        echo "Task metadata created: $task_metadata"
        echo ""
        echo "Next steps for subagent:"
        echo "  cd $worktree_path"
        echo "  # Perform task work..."
        echo "  # When ready:"
        echo "  git add . && git commit -m 'feat: $task_name'"
        echo "  git push -u origin $branch_name"
        echo ""
        echo "To complete task:"
        echo "  $SCRIPT_DIR/complete-subagent-task.sh $task_name"
        echo ""
        echo "To abandon task:"
        echo "  $SCRIPT_DIR/cleanup-completed-worktree.sh $worktree_path"

        # Create a simple status tracking file
        echo "$task_name:in_progress:$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$SUBAGENT_DIR/.task-registry"

    else
        echo "❌ Failed to create subagent worktree"
        exit 1
    fi
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    create_subagent_worktree "$1" "$2"
fi
