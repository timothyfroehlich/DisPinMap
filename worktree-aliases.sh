#!/bin/bash
# Git Worktree Navigation Aliases for DisPinMap
# Source this file in your ~/.bashrc or ~/.zshrc: source /home/froeht/DisPinMap/worktree-aliases.sh

# Core worktree management aliases
alias gwl='git worktree list'
alias gwa='git worktree add'
alias gwr='git worktree remove'
alias gwp='git worktree prune'

# Navigation shortcuts for DisPinMap worktrees
export DISPINMAP_ROOT="/home/froeht/DisPinMap"
export DISPINMAP_WORKTREES="$DISPINMAP_ROOT/claude-worktrees"

alias goto-main="cd $DISPINMAP_ROOT"
alias goto-main-workspace="cd $DISPINMAP_WORKTREES/main-workspace"
alias goto-primary="cd $DISPINMAP_WORKTREES/primary-feature"
alias goto-review="cd $DISPINMAP_WORKTREES/review-workspace"
alias goto-hotfix="cd $DISPINMAP_WORKTREES/hotfix-ready"
alias goto-lab="cd $DISPINMAP_WORKTREES/experiment-lab"
alias goto-subagents="cd $DISPINMAP_WORKTREES/subagent-tasks"

# Quick status check for all worktrees
alias gwstatus='echo "=== Git Worktree Status ==="; git worktree list; echo ""; echo "=== Current Location ==="; pwd; echo ""; echo "=== Current Branch ==="; git branch --show-current'

# Helper functions for worktree management
worktree_help() {
    echo "Git Worktree Navigation Commands:"
    echo "  goto-main           - Go to main repository"
    echo "  goto-main-workspace - Go to main branch workspace"
    echo "  goto-primary        - Go to primary feature workspace"
    echo "  goto-review         - Go to review workspace"
    echo "  goto-hotfix         - Go to hotfix ready workspace"
    echo "  goto-lab            - Go to experiment lab"
    echo "  goto-subagents      - Go to subagent tasks directory"
    echo ""
    echo "Git Worktree Management Commands:"
    echo "  gwl                 - List all worktrees"
    echo "  gwa <path> <branch> - Add new worktree"
    echo "  gwr <path>          - Remove worktree"
    echo "  gwp                 - Prune stale worktree references"
    echo "  gwstatus            - Show worktree and current status"
    echo "  worktree_help       - Show this help"
}

# Function to create a new feature worktree
create_feature_worktree() {
    local feature_name=$1
    if [[ -z "$feature_name" ]]; then
        echo "Usage: create_feature_worktree <feature-name>"
        echo "Example: create_feature_worktree user-auth"
        return 1
    fi

    local worktree_path="$DISPINMAP_WORKTREES/feature-${feature_name}"
    local branch_name="feature/${feature_name}"

    # Ensure we're in project root
    cd "$DISPINMAP_ROOT"

    # Check if branch already exists
    if git show-ref --verify --quiet refs/heads/"$branch_name"; then
        echo "Error: Branch '$branch_name' already exists"
        echo "Use: git worktree add '$worktree_path' '$branch_name'"
        return 1
    fi

    # Create worktree with new branch
    echo "Creating worktree: $worktree_path"
    echo "Branch: $branch_name"
    git worktree add "$worktree_path" -b "$branch_name"

    if [[ $? -eq 0 ]]; then
        echo "✅ Successfully created worktree"
        echo "Navigate with: cd $worktree_path"
        echo "Or use: goto-feature-${feature_name} (if you add an alias)"
    else
        echo "❌ Failed to create worktree"
        return 1
    fi
}

# Function to cleanup a completed worktree
cleanup_worktree() {
    local worktree_path=$1
    if [[ -z "$worktree_path" ]]; then
        echo "Usage: cleanup_worktree <worktree-path>"
        echo "Example: cleanup_worktree claude-worktrees/feature-user-auth"
        return 1
    fi

    # Make path absolute if relative
    if [[ ! "$worktree_path" = /* ]]; then
        worktree_path="$DISPINMAP_ROOT/$worktree_path"
    fi

    if [[ ! -d "$worktree_path" ]]; then
        echo "Error: Worktree directory '$worktree_path' does not exist"
        return 1
    fi

    # Ensure worktree is clean
    cd "$worktree_path"
    if [[ -n $(git status --porcelain) ]]; then
        echo "Error: Worktree has uncommitted changes"
        echo "Commit or stash changes before cleanup"
        git status
        return 1
    fi

    # Get branch name before removal
    local branch_name=$(git branch --show-current)

    # Return to main project
    cd "$DISPINMAP_ROOT"

    # Remove worktree
    echo "Removing worktree: $worktree_path"
    git worktree remove "$worktree_path"

    if [[ $? -eq 0 ]]; then
        echo "✅ Worktree removed successfully"

        # Optionally delete branch (prompt user)
        if [[ "$branch_name" != "main" && "$branch_name" != "master" ]]; then
            read -p "Delete branch '$branch_name'? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git branch -d "$branch_name"
                if [[ $? -eq 0 ]]; then
                    echo "✅ Branch '$branch_name' deleted"
                else
                    echo "⚠️  Branch '$branch_name' not deleted (may have unmerged changes)"
                fi
            fi
        fi
    else
        echo "❌ Failed to remove worktree"
        return 1
    fi
}

# Function to sync all worktrees with main
sync_all_worktrees() {
    echo "🔄 Syncing all worktrees with main branch..."

    # First, fetch latest changes
    cd "$DISPINMAP_ROOT"
    echo "Fetching latest changes..."
    git fetch origin

    # Sync each worktree
    for worktree_dir in "$DISPINMAP_WORKTREES"/*; do
        if [[ -d "$worktree_dir" && "$worktree_dir" != *"/subagent-tasks" ]]; then
            local worktree_name=$(basename "$worktree_dir")
            echo "🔄 Syncing $worktree_name..."

            cd "$worktree_dir"
            local current_branch=$(git branch --show-current)

            # Only sync if not on main and no uncommitted changes
            if [[ -n $(git status --porcelain) ]]; then
                echo "⚠️  Skipping $worktree_name (uncommitted changes)"
            elif [[ "$current_branch" == "main" ]]; then
                git pull origin main
                echo "✅ $worktree_name updated"
            else
                # Try to merge main into feature branch
                git merge origin/main
                if [[ $? -eq 0 ]]; then
                    echo "✅ $worktree_name merged with main"
                else
                    echo "⚠️  $worktree_name has merge conflicts - manual resolution needed"
                fi
            fi
        fi
    done

    cd "$DISPINMAP_ROOT"
    echo "🎉 Sync complete"
}

echo "🤖 Git Worktree aliases loaded for DisPinMap! Type 'worktree_help' for commands."
