#!/usr/bin/env python3
"""
Discord Pinball Map Bot Launcher
Simple entry point that loads and runs the main bot
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main bot
from main import main

if __name__ == '__main__':
    main()