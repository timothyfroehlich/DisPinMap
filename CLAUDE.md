# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Python Discord bot that continuously monitors the pinballmap.com API for changes in pinball machine locations and posts automated updates to configured Discord channels. The bot supports multiple channels with different notification types and customizable search parameters.

## Common Development Commands
- **Activate virtual environment**: `source venv/bin/activate`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run the bot**: `python bot.py`

## Setup Requirements
- Create a `.env` file based on `.env.example` with your Discord bot token
- Set up Discord bot application at https://discord.com/developers/applications

## Core Features
- **Background Monitoring**: Continuously polls pinballmap.com user submissions API at configurable intervals (default: 1 hour)
- **Multi-Channel Support**: Each Discord channel can have independent configuration
- **Submission Types**: 
  - Machine additions/removals (new_lmx, remove_machine)
  - Machine condition updates (new_condition)
- **Efficient Targeting**: Direct coordinate-based and location-specific monitoring
- **Data Persistence**: Retains all configurations and seen submission tracking across bot restarts
- **Duplicate Prevention**: Tracks seen submission IDs to prevent repeat notifications

## Project Architecture
- **Main bot file**: `bot.py` - Discord bot logic and command handlers
- **Background Tasks**: Async polling system for continuous API monitoring
- **Data Storage**: SQLAlchemy ORM with SQLite backend for channel configs and submission tracking
- **API Integration**: pinballmap.com user submissions API with error handling and rate limiting
- **Command System**: Shared command logic between Discord bot and CLI testing
- **Configuration System**: Per-channel settings for targets, poll rate, and notification preferences

## Dependencies
- `discord.py` - Discord API wrapper
- `requests` - HTTP library for API calls
- `sqlalchemy` - Modern Python SQL toolkit and ORM for database operations
- `asyncio` - For background tasks and scheduling

## Configuration Commands
**Target Monitoring:**
- `!latlong add <lat> <lon> <radius>` / `!latlong remove <lat> <lon>` - Monitor coordinate areas
- `!location add <id_or_name>` / `!location remove <id>` - Monitor specific locations by ID or name

**General Commands:**
- `!interval <minutes>` - Set polling interval (minimum 15 minutes)
- `!notifications <type>` - Set notification types (machines, comments, all)
- `!status` - Show current channel configuration and all monitored targets
- `!start` - Start monitoring all configured targets
- `!stop` - Stop monitoring for this channel
- `!check` - Immediately check for new submissions across all targets
- `!test` - Run 30-second simulation for testing

## Setup Requirements
- Discord bot token in `.env` file
- Bot permissions: Send Messages, Read Message History, Use External Emojis
- Channels configured via bot commands before monitoring starts

## Development Status
**Last Updated**: May 28, 2025

**✅ Completed Features**:
- Efficient submission-based monitoring using pinballmap.com user submissions API
- Coordinate-based monitoring with custom radius settings (uses list_within_range API)
- Individual location monitoring by ID or name search (uses location API)
- Modular architecture with shared command logic between Discord bot and CLI testing
- Background polling system with configurable intervals and 24-hour lookback
- Submission tracking to prevent duplicate notifications
- Configuration commands with add/remove functionality for coordinates and locations
- Comprehensive status display and immediate check functionality
- CLI testing system for development without Discord server

**Current Architecture**:
- `bot.py` - Simple launcher in root
- `src/main.py` - Main Discord bot with command handlers (uses shared CommandHandler)
- `src/commands.py` - Shared command logic for both Discord bot and CLI testing
- `src/database.py` - SQLite database with submission tracking and monitoring targets
- `src/api.py` - Pinball Map user submissions API integration with date filtering
- `src/monitor.py` - Background monitoring and notification system using submissions
- `test_cli.py` - CLI testing tool for command validation
- `test/test_simulation.py` - Testing and simulation tools