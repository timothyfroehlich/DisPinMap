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
- `!configure location <lat> <lon>` - Set center point for machine searches
- `!configure radius <miles>` - Set search radius in miles
- `!configure poll_rate <minutes>` - Set polling interval (minimum 15 minutes)
- `!configure notifications <type>` - Set notification types (machines, comments, all)
- `!status` - Show current channel configuration
- `!start` - Start monitoring for this channel
- `!stop` - Stop monitoring for this channel

## Setup Requirements
- Discord bot token in `.env` file
- Bot permissions: Send Messages, Read Message History, Use External Emojis
- Channels configured via bot commands before monitoring starts

## Development Status
**Last Updated**: May 26, 2025

**Completed**:
- ✅ Basic Discord bot with `!hello`, `!ping`, `!machines` commands
- ✅ Updated documentation with expanded feature requirements  
- ✅ Database schema design and implementation (`database.py`)
  - Channel configurations with location/radius/poll rate settings
  - Machine tracking for change detection
  - Notification queue system
  - Data persistence across restarts

**Next Steps** (see todo list):
- Background polling system with configurable intervals
- Configuration commands (`!configure`, `!start`, `!stop`, `!status`)
- Integration of database with bot commands
- Machine addition/removal detection and notifications

**Current Architecture**:
- `bot.py` - Main Discord bot with basic commands
- `database.py` - Complete SQLite database layer
- API integration working with pinballmap.com Austin region