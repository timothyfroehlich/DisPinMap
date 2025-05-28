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
- **Background Monitoring**: Continuously polls pinballmap.com API at configurable intervals (default: 1 hour)
- **Multi-Channel Support**: Each Discord channel can have independent configuration
- **Notification Types**: 
  - Machine additions/removals
  - Machine comments and condition updates
- **Configurable Search**: Custom location center point and search radius per channel
- **Data Persistence**: Retains all configurations and tracking data across bot restarts
- **Change Detection**: Tracks machine states to identify additions, removals, and updates

## Project Architecture
- **Main bot file**: `bot.py` - Discord bot logic and command handlers
- **Background Tasks**: Async polling system for continuous API monitoring
- **Data Storage**: SQLite database for channel configs and machine state tracking
- **API Integration**: pinballmap.com API integration with error handling and rate limiting
- **Configuration System**: Per-channel settings for location, radius, poll rate, and notification preferences

## Dependencies
- `discord.py` - Discord API wrapper
- `requests` - HTTP library for API calls
- `sqlite3` - Database for persistent storage
- `asyncio` - For background tasks and scheduling

## Configuration Commands
**Multiple Target Monitoring:**
- `!region add <name>` / `!region remove <name>` - Monitor entire pinball regions
- `!latlong add <lat> <lon> <radius>` / `!latlong remove <lat> <lon>` - Monitor coordinate areas
- `!location add <name>` / `!location remove <name>` - Monitor specific pinball venues

**General Commands:**
- `!regions` - List all available pinball regions
- `!interval <minutes>` - Set polling interval (minimum 15 minutes)
- `!notifications <type>` - Set notification types (machines, comments, all)
- `!status` - Show current channel configuration and all monitored targets
- `!start` - Start monitoring all configured targets
- `!stop` - Stop monitoring for this channel
- `!check` - Immediately check for changes across all targets
- `!test` - Run 30-second simulation for testing

## Setup Requirements
- Discord bot token in `.env` file
- Bot permissions: Send Messages, Read Message History, Use External Emojis
- Channels configured via bot commands before monitoring starts

## Development Status
**Last Updated**: May 28, 2025

**✅ Completed Features**:
- Complete multiple target monitoring system supporting regions, coordinates, and individual venues
- Region-based location setting with 98 global pinball regions and fuzzy search
- Individual pinball venue monitoring with cross-region search
- Coordinate-based monitoring with custom radius settings
- Modular architecture with focused files (src/, test/ directories)
- Background polling system with configurable intervals
- Machine addition/removal detection and notifications
- Configuration commands with add/remove functionality for each target type
- Comprehensive status display and immediate check functionality
- Test simulation system for development and demonstration

**Current Architecture**:
- `bot.py` - Simple launcher in root
- `src/main.py` - Main Discord bot with command handlers
- `src/database.py` - SQLite database with monitoring targets support
- `src/api.py` - Pinball Map API integration with region/location search
- `src/monitor.py` - Background monitoring and notification system
- `test/test_simulation.py` - Testing and simulation tools