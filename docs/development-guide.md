# Development Guide

## Project Overview

This is a Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and posts automated updates to configured Discord channels. The bot supports multiple channels with different notification types and customizable search parameters. It is designed for deployment on Google Cloud Platform (GCP) but can also be run locally.

## Agent Persona and Guiding Principles

To ensure a productive and positive collaboration, AI assistants working on this project should adopt the following persona and principles:

* **Be a Proactive Partner, Not Just a Tool:** Don't just execute commands. Actively participate in the problem-solving process. If you hit a roadblock, analyze the situation, form a hypothesis, and propose a next step. The goal is to drive the task forward, not just wait for instructions.
* **Value User Guidance:** The user has valuable context. When they offer a suggestion (e.g., "check the logs first," "look in the git history"), treat it as expert advice. Acknowledge the suggestion and immediately incorporate it into your plan. This is a collaborative effort.
* **Don't make snap decisions about odd looking code** The app has been mostly coded by LLM Agents, which lose their context or crash. This leaves tasks in a half-finished state. Always ask for clarification before removing or changing code that looks odd.
* **Use Comprehensive Verification:** After major changes (especially infrastructure), run thorough verification checks to ensure complete success. Don't assume success based on partial indicators.

## Core Technologies
- **Language**: Python 3.11+
- **Discord API**: `discord.py` - Use [Discord.py documentation](https://discordpy.readthedocs.io/) for all bot development
- **Database**: SQLAlchemy ORM with support for SQLite (local) and PostgreSQL (GCP)
- **API Communication**: `requests` and `aiohttp`
- **Testing**: `pytest` with `pytest-asyncio` and `pytest-xdist`
- **Deployment**: Docker, Terraform, GCP (Cloud Run, Cloud SQL, Secret Manager)

## Project Structure
```
DisPinMap/
├── .github/
│   └── copilot-instructions.md
├── data/                   # Data storage (e.g., SQLite DB)
├── docs/                   # Project documentation
├── migrations/             # Database migration scripts
├── src/                    # Main source code
│   ├── __init__.py
│   ├── api.py              # Pinball Map and Geocoding API clients
│   ├── cogs/               # Discord.py command cogs
│   │   ├── config.py       # Configuration commands (poll_rate, notifications)
│   │   └── monitoring.py   # Monitoring commands (add, remove, list, export)
│   ├── database.py         # Database models and session management
│   ├── logging.py          # Logging configuration
│   ├── main.py             # Main application entry point and Discord client setup
│   ├── messages.py         # Centralized user-facing messages
│   ├── models.py           # SQLAlchemy database models
│   ├── monitor.py          # Background monitoring task (as cog)
│   ├── notifier.py         # Discord message formatting and sending
│   └── utils.py            # Shared utilities
├── terraform/              # Terraform scripts for GCP infrastructure
├── tests/                  # Test suite
│   ├── func/               # Functional tests
│   ├── integration/        # Integration tests
│   ├── unit/               # Unit tests
│   └── utils/              # Test utilities and fixtures
├── .env.example            # Example environment file
├── bot.py                  # Main executable for the bot
├── conftest.py             # Pytest configuration
├── Dockerfile              # Container definition for deployment
├── pytest.ini              # Pytest configuration
├── README.md               # Project README
├── requirements.txt        # Python dependencies
└── setup.py                # Project setup script
```

## Coding Standards

1. **Type Safety**
   - Use type hints consistently
   - Run mypy for type checking
   - Document complex types

2. **Testing**
   - Write unit tests for new features
   - Maintain test coverage above 95%
   - Use pytest for testing

3. **Documentation**
   - Document all public functions and classes
   - Keep README.md updated
   - Document API endpoints and parameters
   - Centralize user-facing strings in `src/messages.py`

4. **Error Handling**
   - Use proper exception handling
   - Log errors with context
   - Implement graceful degradation

5. **Date/Time Handling**
   - All `DateTime` columns in SQLAlchemy models must be timezone-aware. Use `DateTime(timezone=True)`.
   - When creating new `datetime` objects for database insertion or comparison, always create timezone-aware objects using `datetime.now(timezone.utc)`.
   - When retrieving `datetime` objects from the database (especially with SQLite), they may be timezone-naive. Before performing timezone-sensitive operations like `.timestamp()`, ensure the object is aware by setting its timezone: `dt_object.replace(tzinfo=timezone.utc)`. This prevents bugs where the local system time is incorrectly used.

## Development Guidelines

### Branch Management and Code Review Requirements
**CRITICAL: All code changes MUST follow these branch and review requirements:**

1. **Branch Creation Required**
   - **NEVER commit directly to main branch**
   - Create a feature branch for ALL changes: `git checkout -b feature/description` or `fix/description`
   - Use descriptive branch names that clearly indicate the purpose

2. **Pull Request Process**
   - **ALL changes must go through pull request review**
   - Create PR with clear title and description
   - Include test results and verification steps
   - Link to any related issues or documentation
   - Wait for approval before merging

3. **Code Review Requirements**
   - At least one reviewer must approve all PRs
   - Address all review comments before merging
   - Ensure CI/CD checks pass
   - Verify tests cover new functionality

### General Development Process
1. **Before Starting Work**
   - Read all documentation for context
   - Check existing issues
   - Review related documentation
   - **Create feature branch** before making any changes
   - **COMMIT ALL CHANGES** before starting major migrations or refactoring

2. **During Development**
   - Follow coding standards
   - Write tests for new features
   - Update documentation
   - Add dependencies to requirements.txt
   - **Make frequent commits** with descriptive messages during major work
   - Create rollback points at key milestones

3. **Before Creating Pull Request**
   - Run all tests locally
   - Check type hints
   - Update documentation if needed
   - Document significant changes
   - Ensure branch is up to date with main

## Environment Setup
- Python 3.11+
- PostgreSQL (optional)
- Docker (for containerization)
- GCP tools (for deployment)

### Python Virtual Environment Setup
**REQUIRED: Always use a virtual environment for development:**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate when done
deactivate
```

**Important:** Always activate the virtual environment before running any Python commands or installing packages.

## Environment Variables
The bot uses environment variables for configuration, managed through a `.env` file in the project root. Create a `.env` file based on `.env.example` with the following required variables:

```bash
# Required Variables
DISCORD_TOKEN=your_discord_bot_token    # Discord bot token from Discord Developer Portal
DB_TYPE=sqlite                          # Database type: 'sqlite' for local, 'postgresql' for GCP

# Optional Variables (for GCP deployment)
DB_HOST=your_db_host                    # PostgreSQL host (required for DB_TYPE=postgresql)
DB_PORT=5432                            # PostgreSQL port
DB_NAME=your_db_name                    # Database name
DB_USER=your_db_user                    # Database user
DB_PASSWORD=your_db_password            # Database password
```

The `.env` file is automatically loaded by the bot using python-dotenv. Make sure to:
1. Never commit the `.env` file to version control
2. Keep `.env.example` updated with all required variables
3. Set appropriate values for your environment (local development vs GCP)

## Common Commands
```bash
# Run tests
pytest

# Run tests in parallel
pytest -n auto

# Type checking
mypy src/

# Start bot
python3 bot.py
```

## Notes for AI Assistants
1. Always check all documentation for context before making changes
2. Update task status when completing significant work
3. Follow the coding standards and guidelines
4. Add new dependencies to requirements.txt
5. Document significant changes in this file
6. **Determining GitHub Repository for Tools**: When using tools that interact with GitHub (e.g., creating issues), if the owner and repository name are not immediately obvious, use the command `git remote -v` in the terminal. This will show the fetch and push URLs, which contain the owner and repository name (e.g., `https://github.com/OWNER/REPO.git`).
