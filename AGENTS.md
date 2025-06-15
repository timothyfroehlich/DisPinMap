# AI Assistant Guidelines and Task Tracking

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

## Coding Standards
1. **Type Safety**
   - Use type hints consistently
   - Run mypy for type checking
   - Document complex types

2. **Testing**
   - Write unit tests for new features
   - Maintain test coverage above 95%
   - Use pytest for testing
   - Run tests in parallel with pytest-xdist

3. **Documentation**
   - Document all public functions and classes
   - Keep README.md updated
   - Document API endpoints and parameters
   - Centralize user-facing strings in `src/messages.py`

4. **Error Handling**
   - Use proper exception handling
   - Log errors with context
   - Implement graceful degradation

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

## Task Tracking

### Completed Tasks
- ✅ GCP Deployment
  - Infrastructure setup
  - Database migration
  - Secret management
  - Docker configuration

- ✅ Command System Improvements
  - Unified add/remove commands
  - Enhanced listing & removal UX
  - Export functionality
  - Poll rate & notification settings

- ✅ Testing Infrastructure
  - Comprehensive test suite
  - Integration tests
  - Performance benchmarks
  - CI/CD pipeline

### Current Tasks
- 🔄 Test Fixes
  - Monitor test mocks
  - Logging timestamp parsing
  - PostgreSQL integration tests

### Future Tasks
- 📝 Performance Optimization
  - Database query optimization
  - Caching implementation
  - Background task scheduling

- 📝 Enhanced Error Handling
  - Retry logic for Discord API
  - Graceful degradation
  - Rate limiting

## Development Guidelines
1. **Before Starting Work**
   - Read this file for context
   - Check existing issues
   - Review related documentation
   - **COMMIT ALL CHANGES** before starting major migrations or refactoring

2. **During Development**
   - Follow coding standards
   - Write tests for new features
   - Update documentation
   - Add dependencies to requirements.txt
   - **Make frequent commits** with descriptive messages during major work
   - Create rollback points at key milestones

3. **Before Committing**
   - Run all tests
   - Check type hints
   - Update this file if needed
   - Document significant changes

## Commit Management
- **Always commit before major migrations**: Create a clean rollback point
- **Use descriptive commit messages**: Include context about what phase of work
- **Commit incrementally**: Don't batch large changes into single commits
- **Create milestone commits**: Mark completion of major components
- **Test before committing**: Ensure changes don't break existing functionality

## Environment Setup
- Python 3.11+
- PostgreSQL (optional)
- Docker (for containerization)
- GCP tools (for deployment)

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
1. Always check this file for context before making changes
2. Update task status when completing significant work
3. Follow the coding standards and guidelines
4. Add new dependencies to requirements.txt
5. Document significant changes in this file

---

Last Updated: 2025-06-15
