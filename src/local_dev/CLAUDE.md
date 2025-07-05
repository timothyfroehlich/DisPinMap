# Local Development Package

**This package is completely isolated from production code and excluded from
coverage.**

## Purpose

The `src/local_dev/` package contains all development-only utilities for testing
and debugging the Discord bot without requiring a full Discord environment.

## Package Isolation

- **No production dependencies**: The main bot code has zero dependencies on
  this package
- **Coverage excluded**: Entire package excluded from code coverage in
  `pyproject.toml`
- **Development only**: Only used during local testing and debugging

## Key Files

- **`local_dev.py`** - Main entry point for local development mode
- **`console_discord.py`** - Console interface simulating Discord interactions
- **`file_watcher.py`** - External command interface via file watching
- **`local_logging.py`** - Enhanced logging with rotation for local testing
- **`__init__.py`** - Package initialization and exports

## Usage

```bash
# From project root (recommended)
python local_dev.py

# Or directly
python src/local_dev/local_dev.py
```

## Architecture

```
src/local_dev/           # Isolated development package
├── __init__.py          # Package exports
├── local_dev.py         # Main entry point
├── console_discord.py   # Console Discord simulation
├── file_watcher.py      # External command interface
├── local_logging.py     # Development logging
└── CLAUDE.md           # This documentation

# Convenience entry point
local_dev.py             # Root-level entry script
```

## Key Features

- **Thread-safe command processing**: Uses `loop.call_soon_threadsafe()` for
  asyncio coordination
- **External command interface**: Send commands via file watching without
  interrupting bot
- **Enhanced logging**: Rotating logs with timestamp categorization
- **Production database**: Download and use real data from Cloud Run backups

## Isolation Verification

- ✅ No imports of `src.local_dev` from main code
- ✅ Coverage exclusion in `pyproject.toml`
- ✅ Main bot imports successfully without local_dev
- ✅ Self-contained package with all dependencies declared
