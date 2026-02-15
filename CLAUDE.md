# Project Instructions for AI Agents

**Repo:** <https://github.com/timothyfroehlich/DisPinMap>

A Discord bot that monitors [pinballmap.com](https://pinballmap.com) for pinball
machine changes and posts updates to Discord channels. Deployed on GCP Cloud Run
with Terraform.

## Directory-Specific Instructions

Read the relevant CLAUDE.md before working in any directory:

| Directory               | Scope                                                            |
| ----------------------- | ---------------------------------------------------------------- |
| `src/CLAUDE.md`         | Core application: models, API, database, commands, notifications |
| `tests/CLAUDE.md`       | Test framework, mock patterns, fixtures, test organization       |
| `terraform/CLAUDE.md`   | Infrastructure as Code, GCP resources                            |
| `alembic/CLAUDE.md`     | Database migrations, schema changes                              |
| `scripts/CLAUDE.md`     | Utility scripts, validation tools                                |
| `docs/CLAUDE.md`        | Documentation standards                                          |
| `docs/issues/CLAUDE.md` | Issue tracking and bug documentation                             |

## Architecture Overview

```
Discord User
    │
    ▼
CommandHandler (src/cogs/command_handler.py)
    │  validates args → calls Database → triggers Notifier
    ▼
Database (src/database.py)          ← SQLAlchemy ORM, SQLite
    │  CRUD for channels, targets, seen submissions
    ▼
Runner (src/cogs/runner.py)         ← background task loop (1-min interval)
    │  polls active channels → fetches API → filters new → notifies
    ▼
Notifier (src/notifier.py)         ← formats and sends Discord messages
    │  uses Messages (src/messages.py) for templates
    ▼
API (src/api.py)                   ← pinballmap.com + geocoding
    rate-limited HTTP requests
```

**Core flow:** User adds a monitoring target via `!add` command. The Runner's
background loop polls the PinballMap API on each channel's configured interval,
filters out already-seen submissions via the database, and sends new ones to the
Discord channel through the Notifier.

**Key models** (`src/models.py`): `ChannelConfig` (per-channel settings),
`MonitoringTarget` (what to monitor), `SeenSubmission` (deduplication).

## Development Environment

**Python virtual environment is in `venv/` (not `.venv`).**

```bash
# Setup (if venv/ doesn't exist)
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]

# Activate (every session)
source venv/bin/activate
```

## Code Quality

**Ruff is the only Python quality tool. We do not use mypy, black, flake8, or
isort.**

```bash
source venv/bin/activate
ruff format .         # format
ruff check --fix .    # lint + auto-fix
pytest tests/ --ignore=tests/simulation -v  # test
```

Pre-commit hooks enforce: trailing whitespace, EOF, YAML, ruff, prettier
(markdown/YAML), actionlint.

**Always run pre-commit before committing:**

```bash
pre-commit run --all-files
```

## Git Workflow

1. **Never commit directly to main.** All work in feature branches.
2. Branch naming: `feature/description` or `fix/description`.
3. All changes require PR review. Branch protection requires passing CI.
4. Commit attribution for AI agents:

```bash
git commit --author="Claude Code <claude-code@anthropic.com>" -m "$(cat <<'EOF'
commit message here

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <claude-code@anthropic.com>
EOF
)"
```

**Never modify git config.** Use `--author` flag instead.

## Testing

Tests follow a pyramid: unit → integration → simulation.

```bash
pytest tests/ --ignore=tests/simulation -v    # standard run
pytest tests/unit/ -v                         # unit only
pytest tests/integration/ -v                  # integration only
pytest -n auto                                # parallel execution
pytest --cov=src --cov-report=html            # with coverage
```

**Key rules:**

- All mocks must use spec-based factories from `tests/utils/mock_factories.py`.
  Never use raw `Mock()` or `MagicMock()` without specs.
- Each test worker gets an isolated SQLite database.
- API mocking uses `api_mocker` fixture with JSON fixtures in
  `tests/fixtures/api_responses/`.
- See `tests/CLAUDE.md` for full testing guide.

## Bug Fix Workflow

When presented with a production bug:

1. Add a failing test that reproduces the bug
2. Only fix the bug once the test fails
3. Verify the fix makes the test pass

## Local Development

```bash
source venv/bin/activate
python scripts/download_production_db.py  # one-time: get prod data
python local_dev.py                       # start local dev session
```

- Console interface simulates Discord (`!add`, `!list`, `!check`, `!help`)
- Dot commands for control (`.quit`, `.health`, `.status`, `.trigger`)
- File watcher: `echo "!list" >> commands.txt` from another terminal
- Logs: `tail -f logs/bot.log`

## Production Debugging

```bash
gcloud run services logs read dispinmap-bot --region=us-central1 --limit=50
```

## Environment Assumptions

- GCP, Docker, Terraform already installed and authenticated
- Environment variables and secrets already configured
- Working directory is project root unless specified

## Documentation Map

| Audience           | File                                             |
| ------------------ | ------------------------------------------------ |
| Users              | `README.md`, `USER_DOCUMENTATION.md`             |
| Developers         | `docs/LOCAL_DEVELOPMENT.md`, `docs/DATABASE.md`  |
| AI Agents          | This file + directory-specific `CLAUDE.md` files |
| Historical context | `project-lessons.md`                             |

## Rules

- Never use `sys.path.append` for imports
- Never use `--no-verify` on git commands unless explicitly asked
- Don't use GitHub issue labels
- When solving tricky problems, update `project-lessons.md` with new lessons
