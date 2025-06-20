#!/usr/bin/env python3
"""
Discord Pinball Map Bot Launcher
Simple entry point that loads and runs the main bot
"""

import asyncio

from src.main import main

if __name__ == "__main__":
    asyncio.run(main())
