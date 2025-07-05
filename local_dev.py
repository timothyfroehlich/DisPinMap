#!/usr/bin/env python3
"""
Convenience entry point for local development mode.

This script allows running local development from the project root:
    python local_dev.py

Instead of having to run:
    python src/local_dev/local_dev.py
"""

if __name__ == "__main__":
    from src.local_dev.local_dev import main

    main()
