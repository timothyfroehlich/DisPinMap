# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Python Discord bot that monitors the pinballmap.com API for changes in pinball machine locations near Austin, Texas, and posts updates to a Discord channel.

## Common Development Commands
- **Activate virtual environment**: `source venv/bin/activate`
- **Install dependencies**: `pip install -r requirements.txt`
- **Run the bot**: `python bot.py`

## Setup Requirements
- Create a `.env` file based on `.env.example` with your Discord bot token
- Set up Discord bot application at https://discord.com/developers/applications

## Project Architecture
- **Main bot file**: `bot.py` (to be created) - contains the Discord bot logic
- **API Integration**: Bot integrates with pinballmap.com API to monitor machine locations
- **Location Focus**: Specifically monitors Austin, Texas area
- **Discord Integration**: Posts updates about new/removed machines to configured Discord channel

## Dependencies
- `discord.py` - Discord API wrapper
- `requests` - HTTP library for API calls

## Configuration Requirements
- Discord bot token setup required
- Discord channel ID configuration needed
- Austin, TX geographic area targeting