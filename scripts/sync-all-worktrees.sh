#!/bin/bash
# Sync all worktrees with the main branch for DisPinMap development
# Usage: ./sync-all-worktrees.sh [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WORKTREES_DIR="$PROJECT_ROOT/claude-worktrees"

sync_all_worktrees() {
    local force_mode=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_mode=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [--force]"
                echo ""
                echo "Sync all worktrees with the main branch"
                echo ""
                echo "Options:"
                echo "  --force    Skip uncommitted changes check (dangerous)"
                echo "  --help     Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    echo "🔄 Syncing all worktrees with main branch..."
    echo "Project root: $PROJECT_ROOT"
    echo "Force mode: $force_mode"
    echo ""

    # First, fetch latest changes
    cd "$PROJECT_ROOT"
    echo "📡 Fetching latest changes from origin..."
    git fetch origin
    echo ""

    # Get list of worktrees
    local worktree_count=0
    local synced_count=0
    local skipped_count=0
    local error_count=0

    # Sync each worktree
    for worktree_dir in "$WORKTREES_DIR"/*; do
        if [[ -d "$worktree_dir" && "$worktree_dir" != *"/subagent-tasks" ]]; then
            local worktree_name=$(basename "$worktree_dir")
            worktree_count=$((worktree_count + 1))

            echo "🔄 Processing worktree: $worktree_name"

            cd "$worktree_dir"
            local current_branch=$(git branch --show-current)
            echo "  Branch: $current_branch"

            # Check for uncommitted changes
            if [[ -n $(git status --porcelain) ]]; then
                if [[ "$force_mode" == "true" ]]; then
                    echo "  ⚠️  Uncommitted changes detected (force mode - continuing)"
                else
                    echo "  ⚠️  Skipping $worktree_name (uncommitted changes)"
                    echo "      Use --force to sync anyway or commit/stash changes"
                    skipped_count=$((skipped_count + 1))
                    echo ""
                    continue
                fi
            fi

            # Sync based on branch type
            if [[ "$current_branch" == "main" ]]; then
                echo "  📥 Pulling latest main..."
                if git pull origin main; then
                    echo "  ✅ Updated main branch"
                    synced_count=$((synced_count + 1))
                else
                    echo "  ❌ Failed to update main branch"
                    error_count=$((error_count + 1))
                fi
            else
                echo "  🔀 Merging main into $current_branch..."
                # Try to merge main into feature branch
                if git merge origin/main --no-edit; then
                    echo "  ✅ Merged main into $current_branch"
                    synced_count=$((synced_count + 1))
                else
                    echo "  ❌ Merge conflicts detected in $current_branch"
                    echo "      Manual resolution required in: $worktree_dir"
                    echo "      Run: cd $worktree_dir && git merge origin/main"
                    error_count=$((error_count + 1))

                    # Abort the merge to leave worktree in clean state
                    git merge --abort 2>/dev/null || true
                fi
            fi

            echo ""
        fi
    done

    # Return to project root
    cd "$PROJECT_ROOT"

    # Summary
    echo "📊 Sync Summary:"
    echo "  Total worktrees: $worktree_count"
    echo "  Successfully synced: $synced_count"
    echo "  Skipped (uncommitted changes): $skipped_count"
    echo "  Errors (merge conflicts): $error_count"
    echo ""

    if [[ $error_count -gt 0 ]]; then
        echo "⚠️  Some worktrees have merge conflicts that need manual resolution."
    elif [[ $skipped_count -gt 0 ]]; then
        echo "⚠️  Some worktrees were skipped due to uncommitted changes."
        echo "   Commit/stash changes or use --force to sync anyway."
    else
        echo "🎉 All worktrees synced successfully!"
    fi

    echo ""
    echo "Current worktree status:"
    git worktree list
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    sync_all_worktrees "$@"
fi
