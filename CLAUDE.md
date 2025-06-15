# CLAUDE.md

This file provides guidance to Claude or other AI assistants when working with code in this repository.

## Project Overview
This is a Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and posts automated updates to configured Discord channels. The bot supports multiple channels with different notification types and customizable search parameters. It is designed for deployment on Google Cloud Platform (GCP) but can also be run locally.

## Core Technologies
- **Language**: Python 3.11+
- **Discord API**: `discord.py`
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
├── migrations/             # Database migration scripts
├── src/                    # Main source code
│   ├── __init__.py
│   ├── api.py              # Pinball Map and Geocoding API clients
│   ├── commands.py         # Bot command logic
│   ├── database.py         # Database models and session management
│   ├── main.py             # Main application entry point and Discord client setup
│   ├── messages.py         # Centralized user-facing messages
│   ├── monitor.py          # Background monitoring task
│   └── utils.py            # Shared utilities
├── terraform/              # Terraform scripts for GCP infrastructure
├── tests/                  # Test suite
│   ├── func/               # Functional tests
│   ├── integration/        # Integration tests
│   ├── unit/               # Unit tests
│   └── utils/              # Test utilities and fixtures
├── .env.example            # Example environment file
├── AGENT_TASKS.md          # Agent-managed task list
├── bot.py                  # Main executable for the bot
├── conftest.py             # Pytest configuration
├── Dockerfile              # Container definition for deployment
├── pytest.ini              # Pytest configuration
├── README.md               # Project README
├── requirements.txt        # Python dependencies
└── setup.py                # Project setup script
```

## Setup and Running

### Local Development
1.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up environment variables**:
    -   Copy `.env.example` to `.env`.
    -   Add your Discord bot token to the `.env` file: `DISCORD_BOT_TOKEN=your_token_here`
4.  **Run the bot**:
    ```bash
    python bot.py
    ```

### Running Tests
- **Run all tests**:
    ```bash
    python -m pytest -v
    ```
- **Run tests in parallel**:
    ```bash
    python -m pytest -n auto
    ```

## Bot Commands
The bot uses slash commands prefixed with `!`.

**Target Monitoring:**
- `!add location <name_or_id>` - Monitor specific locations by ID or name
- `!add city <name> [radius]` - Monitor city areas with optional radius
- `!add coordinates <lat> <lon> [radius]` - Monitor coordinate areas with optional radius
- `!rm <index>` - Remove target by index (use `!list` to see indices)

**General Commands:**
- `!list` - Show all monitored targets with their indices
- `!export` - Export channel configuration as copy-pasteable commands
- `!poll_rate <minutes> [target_index]` - Set polling rate for channel or specific target
- `!notifications <type> [target_index]` - Set notification types (machines, comments, all)
- `!check` - Immediately check for new submissions across all targets

## Development Guidelines
-   **Follow Existing Style**: Adhere to the existing code style and patterns.
-   **Use Type Hints**: All new code should include type hints.
-   **Centralized Messages**: All user-facing strings should be added to `src/messages.py` and referenced from there.
-   **Test Coverage**: New features should be accompanied by corresponding tests.
-   **Dependencies**: Add any new packages to `requirements.txt`.
-   **Task Management**: For major changes, update `AGENT_TASKS.md` to reflect the work.
