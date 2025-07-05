# Project Instructions

**This file contains project-specific instructions for AI code agents (Claude,
Copilot, etc).**

- If you are using an AI agent to automate coding, testing, or infrastructure
  tasks, you (and the agent) must read this file first.
- Human contributors: For general developer guidance, see
  `docs/DEVELOPER_HANDBOOK.md`.

## This is our repo: <https://github.com/timothyfroehlich/DisPinMap>

## 🚨 Issue Awareness - Read First

**CRITICAL**: Before starting any work, review current issues to understand
known problems:

```bash
# 1. List all documented issues
ls docs/issues/*.md

# 2. Get summary of each issue (first 5 lines)
head -5 docs/issues/*.md

# 3. Check GitHub issues (requires gh CLI)
gh issue list --state open

# 4. Review recent closed issues for context
ls docs/issues/closed/*.md 2>/dev/null || echo "No closed issues yet"
```

💡 **Always run these commands to understand the full problem landscape before
starting work. The `head -5` command shows the title and priority/status of each
documented issue.**

## 🗂️ Directory-Specific Agent Instructions

**IMPORTANT**: Before working in any directory, consult its specific CLAUDE.md
file:

- **📁 `src/CLAUDE.md`** - Core application code, models, API clients, command
  handlers
- **📁 `tests/CLAUDE.md`** - Testing framework, mock patterns, test organization
- **📁 `terraform/CLAUDE.md`** - Infrastructure as Code, GCP resources,
  deployment
- **📁 `alembic/CLAUDE.md`** - Database migrations, schema changes, SQLAlchemy
- **📁 `scripts/CLAUDE.md`** - Utility scripts, validation tools, automation
- **📁 `docs/CLAUDE.md`** - Documentation standards, writing guidelines

💡 **Always read the relevant directory CLAUDE.md before making changes in that
area.**

## 📚 Documentation Map

### For Users & Overview

- `README.md` - Project overview, quick start
- `USER_DOCUMENTATION.md` - Bot command reference

### For Developers

- `docs/DEVELOPER_HANDBOOK.md` - Complete development guide
- `docs/DATABASE.md` - Database schema and patterns
- `docs/LOCAL_DEVELOPMENT.md` - Local development with console interface
- `tests/CLAUDE.md` - Testing framework guide

### For AI Agents (This File + Directory-Specific)

- **Main**: `CLAUDE.md` (this file) - Project overview, workflows, standards
- **Specific**: `{directory}/CLAUDE.md` - Directory-specific context and
  patterns

## CRITICAL: Branch and Pull Request Workflow

**ALL work must be done in feature branches with PR review:**

1. **Always create a branch**: `git checkout -b feature/description` or
   `fix/description`
2. **Never commit directly to main**
3. **All changes require PR review and approval**
4. **Wait for approval before merging**
5. **Include test results and verification in PR description**
6. **Use descriptive branch names that clearly indicate the purpose**
7. **GitHub branch protection rules require passing status checks before merge**

## Environment Assumptions for Automation

- **Assume GCP, Docker, and Terraform are already installed and authenticated.**
  - All commands can assume the correct GCP project is set, Docker is
    authenticated for Artifact Registry, and Terraform is initialized and has
    access to state.
  - No need to repeat authentication or setup steps unless explicitly requested.
- **Assume required environment variables and secrets are already configured.**
  - The bot's Discord token and database credentials are present in Secret
    Manager and referenced by Terraform.
- **Assume the working directory is the project root unless otherwise
  specified.**

_Update this section if your environment setup changes or if additional
assumptions should be made for automation or agent work._

## Python Development Environment

**CRITICAL: Always use the Python virtual environment located in `venv/` (not
`.venv`).**

### Setting Up the Environment

If the `venv/` directory doesn't exist, create it:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

### Activating the Environment

Always activate the virtual environment before running any Python commands:

```bash
source venv/bin/activate
```

## 🖥️ Local Development Mode

**For debugging monitoring issues and cost-effective testing without Cloud
Run.**

### Quick Start

```bash
# 1. Download production database
source venv/bin/activate
python scripts/download_production_db.py

# 2. Start local development mode
python local_dev.py
```

### Local Development Features

- **Console Discord Interface**: Interact with bot commands via stdin/stdout
- **File Watcher Interface**: Send commands by appending to `commands.txt` file
- **Enhanced Logging**: All output to console + rotating log file
  (`logs/bot.log`)
- **Production Database**: Real data from Cloud Run backups
- **Monitoring Loop**: Full monitoring functionality with API calls
- **Cost Savings**: Cloud Run scaled to 0 instances

### Console Commands

**Discord Bot Commands** (prefix with `!`):

- `!add location "Name"` - Add location monitoring
- `!list` - Show monitored targets
- `!check` - Manual check all targets
- `!help` - Show command help

**Console Special Commands** (prefix with `.`):

- `.quit` - Exit local development session
- `.health` - Show bot health status (Discord, DB, monitoring loop)
- `.status` - Show monitoring status (target counts, recent targets)
- `.trigger` - Force immediate monitoring loop iteration

### External Command Interface (File Watcher)

**Send commands from another terminal without restarting the bot:**

```bash
# Terminal 1: Keep bot running
python local_dev.py

# Terminal 2: Send commands
echo "!list" >> commands.txt
echo ".status" >> commands.txt
echo "!config poll_rate 15" >> commands.txt

# Terminal 3: Monitor responses
tail -f logs/bot.log
```

**Benefits:**

- **No interruption**: Bot keeps running while you send commands
- **External control**: Control from scripts, other terminals, or automation
- **Command history**: All commands saved in `commands.txt` file
- **Cross-platform**: Works on any system that supports file operations

### Log Monitoring

```bash
# Watch logs in real-time
tail -f logs/bot.log

# Search for monitoring activity
grep "MONITOR" logs/bot.log

# Check for errors
grep "ERROR" logs/bot.log
```

### Troubleshooting Local Dev

- **Console not responding**: Check for EOF/Ctrl+D in input
- **Database not found**: Run `python scripts/download_production_db.py`
- **Discord connection issues**: Verify `DISCORD_BOT_TOKEN` in `.env.local`
- **Missing environment**: Ensure `.env.local` exists with required variables

### Production Database Download

The production database is downloaded from Litestream backups:

```bash
python scripts/download_production_db.py
```

- Downloads latest backup from `dispinmap-bot-sqlite-backups` GCS bucket
- Restores to `local_db/pinball_bot.db`
- Verifies database integrity and shows table counts

## Code Quality Standards

**CRITICAL: We use Ruff exclusively for all Python code quality.**

### Our Tool Stack

- **Python**: `ruff` for ALL linting, formatting, type checking, and import
  sorting
- **Markdown/YAML**: `prettier` for formatting
- **Tests**: `pytest` with coverage
- **Git**: `pre-commit` hooks

### Tools We Do NOT Use

We have standardized on Ruff and explicitly **do not use**:

- ❌ `mypy` (Ruff handles type checking)
- ❌ `black` (Ruff handles formatting)
- ❌ `flake8` (Ruff handles linting)
- ❌ `isort` (Ruff handles import sorting)

### Quick Commands

```bash
# Activate environment first
source venv/bin/activate

# Format and lint Python code
ruff format .           # Format Python code
ruff check .            # Lint Python code
ruff check --fix .      # Auto-fix linting issues

# Format markdown and YAML
prettier --write "**/*.{md,yml,yaml}" --ignore-path .gitignore

# Run tests
pytest tests/ --ignore=tests/simulation -v

# Run ALL checks (comprehensive script)
./scripts/run_all_checks.sh
```

#### VS Code Tasks (Recommended)

Use the pre-configured VS Code tasks (accessible via `Ctrl+Shift+P` → "Tasks:
Run Task"):

- **Format Code**: Runs `ruff format .`
- **Lint Code**: Runs `ruff check .`
- **Run Tests**: Runs pytest with coverage
- **Install Dependencies**: Sets up the virtual environment

#### Pre-Commit Workflow

Before committing changes:

1. **Format**: `ruff format .`
2. **Lint**: `ruff check --fix .`
3. **Test**: `pytest tests/ --ignore=tests/simulation -v`
4. **Format Docs**:
   `prettier --write "**/*.{md,yml,yaml}" --ignore-path .gitignore`

#### CI/CD Integration

The GitHub Actions workflows automatically run:

- `ruff check .` (linting)
- `ruff format --check .` (format checking)
- `prettier --check "**/*.{md,yml,yaml}"` (markdown/YAML checking)
- Full test suite with coverage

For detailed project lessons learned and historical context, load
`@project-lessons.md`. When you solve a tricky problem or we end up taking a
different direction, update project-lessons.md with those new lessons.

## Claude Code Commit Attribution

When Claude Code makes commits, use proper attribution to distinguish
AI-generated changes:

```bash
git commit --author="Claude Code <claude-code@anthropic.com>" -m "commit message"
```

**Standard commit format:**

- Use descriptive commit messages explaining the changes and reasoning
- Always include the Claude Code signature block:

  ```
  🤖 Generated with [Claude Code](https://claude.ai/code)

  Co-Authored-By: Claude <claude-code@anthropic.com>
  ```

- Keep user's git configuration unchanged - never modify `git config` settings
- Use `--author` flag instead of changing global git configuration

This ensures clear attribution while preserving the user's personal git
settings.

## Debugging

Use this command to check recent logs:

```
gcloud run services logs read dispinmap-bot --region=us-central1 --limit=50
```

When presented with a production bug, start by adding a failing test that
reproduces the bug. Only start fixing the bug once you have a test that fails.

## Other

Never use src.path.append for imports.
