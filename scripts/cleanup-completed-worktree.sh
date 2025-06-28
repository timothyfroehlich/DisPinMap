#!/bin/bash
# Clean up a completed worktree for DisPinMap development
# Usage: ./cleanup-completed-worktree.sh <worktree-path>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cleanup_worktree() {
    local worktree_path=$1
    if [[ -z "$worktree_path" ]]; then
        echo "Usage: $0 <worktree-path>"
        echo "Examples:"
        echo "  $0 claude-worktrees/feature-user-auth"
        echo "  $0 /full/path/to/worktree"
        echo ""
        echo "Current worktrees:"
        git worktree list
        exit 1
    fi

    # Make path absolute if relative
    if [[ ! "$worktree_path" = /* ]]; then
        worktree_path="$PROJECT_ROOT/$worktree_path"
    fi

    echo "🔄 Cleaning up worktree..."
    echo "Worktree path: $worktree_path"
    echo ""

    if [[ ! -d "$worktree_path" ]]; then
        echo "❌ Error: Worktree directory '$worktree_path' does not exist"
        echo ""
        echo "Current worktrees:"
        git worktree list
        exit 1
    fi

    # Ensure worktree is clean
    cd "$worktree_path"
    if [[ -n $(git status --porcelain) ]]; then
        echo "❌ Error: Worktree has uncommitted changes"
        echo "Please commit or stash changes before cleanup:"
        echo ""
        git status
        exit 1
    fi

    # Get branch name before removal
    local branch_name=$(git branch --show-current)
    echo "Current branch: $branch_name"

    # Check if branch has been pushed and merged
    local is_merged=false
    cd "$PROJECT_ROOT"

    if git merge-base --is-ancestor "$branch_name" origin/main 2>/dev/null; then
        is_merged=true
        echo "✅ Branch has been merged into main"
    else
        echo "⚠️  Branch may not be merged into main"
    fi

    # Remove worktree
    echo ""
    echo "Removing worktree..."
    git worktree remove "$worktree_path"

    if [[ $? -eq 0 ]]; then
        echo "✅ Worktree removed successfully"

        # Handle branch deletion
        if [[ "$branch_name" != "main" && "$branch_name" != "master" ]]; then
            if [[ "$is_merged" == "true" ]]; then
                echo "Branch appears to be merged. Recommending deletion."
                read -p "Delete branch '$branch_name'? (Y/n): " -n 1 -r
                echo
                if [[ -z "$REPLY" || $REPLY =~ ^[Yy]$ ]]; then
                    git branch -d "$branch_name"
                    if [[ $? -eq 0 ]]; then
                        echo "✅ Branch '$branch_name' deleted locally"

                        # Optionally delete remote branch
                        if git show-ref --verify --quiet refs/remotes/origin/"$branch_name"; then
                            read -p "Delete remote branch 'origin/$branch_name'? (y/N): " -n 1 -r
                            echo
                            if [[ $REPLY =~ ^[Yy]$ ]]; then
                                git push origin --delete "$branch_name"
                                echo "✅ Remote branch deleted"
                            fi
                        fi
                    else
                        echo "⚠️  Could not delete branch '$branch_name' (may have unmerged changes)"
                        echo "To force delete: git branch -D '$branch_name'"
                    fi
                fi
            else
                echo "⚠️  Branch '$branch_name' may not be merged. Not deleting automatically."
                echo "To delete anyway: git branch -D '$branch_name'"
            fi
        fi

        echo ""
        echo "🎉 Cleanup complete!"
        echo "Remaining worktrees:"
        git worktree list

    else
        echo "❌ Failed to remove worktree"
        exit 1
    fi
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cleanup_worktree "$1"
fi
