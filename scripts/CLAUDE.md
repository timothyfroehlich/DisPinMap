# Scripts Agent Instructions

## Validation Scripts

- **run_all_validations.py** - Comprehensive fixture and API validation
- **validate_litestream.py** - Database backup configuration checks

## Local Development Scripts

- **download_production_db.py** - Download production database for local testing

## Git Worktree Management (Advanced)

- **create-feature-worktree.sh** - Create new worktree for parallel development
- **sync-all-worktrees.sh** - Sync all worktrees with latest changes
- **cleanup-completed-worktree.sh** - Remove finished worktrees
- **../worktree-aliases.sh** - Convenience aliases (in project root)

## Common Commands

```bash
# Download production database for local development
python scripts/download_production_db.py

# Validate all fixtures and API responses
python scripts/run_all_validations.py --ci-safe

# Check Litestream backup configuration
python scripts/validate_litestream.py

# Create new worktree for feature work
./scripts/create-feature-worktree.sh feature-name

# Sync all worktrees (when main branch updates)
./scripts/sync-all-worktrees.sh
```

## Fixture Validation

The `run_all_validations.py` script ensures:

- API response fixtures match current API format
- All test fixtures load without JSON errors
- External API endpoints are reachable (when not in CI)
- Fixture data matches expected schema

## Worktree Workflow (Advanced)

**Purpose**: Work on multiple features simultaneously without branch switching

```bash
# Setup (one time)
source worktree-aliases.sh

# Create feature worktree
create-feature-worktree feature-name

# Work in parallel directories
cd ../DisPinMap-feature-name
# Make changes, commit, etc.

# When done
cleanup-completed-worktree feature-name
```

## Script Dependencies

- **Python scripts**: Require active virtual environment
- **Bash scripts**: Require git and standard Unix tools
- **Validation scripts**: May need network access for API checks

## Environment Variables

Some scripts check for:

- `CI` - Skips network-dependent validations
- `DATABASE_PATH` - For database-related validations
- Git configuration for worktree operations

## Integration with CI

- **GitHub Actions** uses `ci_fixture_validation.yml` workflow
- Scripts designed to run in both local and CI environments
- Exit codes indicate success/failure for automation
