# Source Code Agent Instructions

## Key Files

- **main.py** - Discord bot initialization, cog loading, startup logic
- **models.py** - SQLAlchemy models: ChannelConfig, MonitoringTarget
- **database.py** - Database operations, session management, CRUD
- **api.py** - External API clients (Pinball Map, Geocoding)
- **notifier.py** - Discord notification logic and message sending
- **messages.py** - Response templates and formatting functions
- **log_config.py** - Centralized logging configuration

### Local Development Files

- **local_dev.py** - Local development entry point with console interface
- **local_logging.py** - Enhanced logging with rotation for local testing
- **console_discord.py** - Console Discord interface for stdin/stdout interaction

## Command Architecture

- **Handler**: `cogs/command_handler.py` - Discord command processing
- **Runner**: `cogs/runner.py` - Background monitoring loop
- **Pattern**: Commands validate args → call database → trigger notifications

## API Client Patterns

- **Rate limiting**: Use `rate_limited_request()` function
- **Error handling**: Wrap API calls in try/catch with logging
- **Caching**: Responses cached in fixtures for testing
- **Mock-friendly**: Designed for easy testing with `api_mocker`

## Database Patterns

- **Sessions**: Always use context managers or fixtures
- **Models**: SQLAlchemy ORM with relationships
- **Migrations**: Alembic in `/alembic` directory
- **Testing**: Isolated databases per test worker

## Notification Flow

1. Monitor loop detects changes
2. Notifier formats messages using templates from `messages.py`
3. Discord client sends to configured channels
4. Errors logged with context for debugging

## Common Commands

```bash
# Run the bot in production mode
python bot.py

# Run the bot in local development mode (with console interface)
python src/local_dev.py

# Database migrations
alembic upgrade head

# Run tests with coverage
pytest --cov=src

# Check for critical issues
grep -r "target_data" src/  # Should return nothing!
```

## Local Development Patterns

### Console Interface Usage
```python
# In console_discord.py - simulates Discord interactions
fake_message = FakeMessage(command)
await self.command_handler.add_location(fake_message, *args)
```

### Enhanced Logging
```python
# Use local_logging.py for development
from src.local_logging import setup_logging, get_logger
setup_logging("DEBUG", "logs/bot.log")
logger = get_logger("module_name")
```

### Database Access in Local Mode
```python
# Use the same Database class, but with local SQLite file
database = Database()  # Reads from .env.local DATABASE_PATH
with database.get_session() as session:
    targets = session.query(MonitoringTarget).all()
```

## Code Style

- Use type hints for function parameters and returns
- Async/await for all Discord and database operations
- Error logging with context (channel_id, user_id, etc.)
- Never use `src.path.append` for imports
