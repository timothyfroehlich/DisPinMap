# Project Instructions

**This file contains project-specific instructions for AI code agents (Claude,
Copilot, etc).**

- If you are using an AI agent to automate coding, testing, or infrastructure
  tasks, you (and the agent) must read this file first.
- Human contributors: For general developer guidance, see
  `docs/DEVELOPER_HANDBOOK.md`.

## This is our repo: <https://github.com/timothyfroehlich/DisPinMap>

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

### Code Quality Tools

This project uses **Ruff** for both linting and formatting, plus **Prettier**
for markdown/YAML files.

#### Quick Commands

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
