#!/usr/bin/env python3
"""
Convenience entry point for local development mode.

This script allows running local development from the project root:
    python local_dev.py

Instead of having to run:
    python src/local_dev/local_dev.py
"""

if __name__ == "__main__":
    import asyncio
    from src.local_dev.local_dev import main

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import sys
        sys.exit(1)
