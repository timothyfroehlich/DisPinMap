#!/bin/bash
# Create a new feature worktree for DisPinMap development
# Usage: ./create-feature-worktree.sh <feature-name>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WORKTREES_DIR="$PROJECT_ROOT/claude-worktrees"

create_feature_worktree() {
    local feature_name=$1
    if [[ -z "$feature_name" ]]; then
        echo "Usage: $0 <feature-name>"
        echo "Example: $0 user-auth"
        echo "This will create:"
        echo "  - Branch: feature/user-auth"
        echo "  - Worktree: claude-worktrees/feature-user-auth"
        exit 1
    fi

    local worktree_path="$WORKTREES_DIR/feature-${feature_name}"
    local branch_name="feature/${feature_name}"

    # Ensure we're in project root
    cd "$PROJECT_ROOT"

    echo "🔄 Creating feature worktree..."
    echo "Project root: $PROJECT_ROOT"
    echo "Worktree path: $worktree_path"
    echo "Branch name: $branch_name"
    echo ""

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

    # Create worktree with new branch
    echo "Creating worktree and branch..."
    git worktree add "$worktree_path" -b "$branch_name"

    if [[ $? -eq 0 ]]; then
        echo "✅ Successfully created feature worktree!"
        echo ""
        echo "Next steps:"
        echo "  cd $worktree_path"
        echo "  # Start development..."
        echo "  # When ready:"
        echo "  git push -u origin $branch_name"
        echo ""
        echo "To clean up later:"
        echo "  $SCRIPT_DIR/cleanup-completed-worktree.sh $worktree_path"
    else
        echo "❌ Failed to create worktree"
        exit 1
    fi
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    create_feature_worktree "$1"
fi
