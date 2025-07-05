"""
Local Development Package

This package contains all local development utilities that are used for testing
and debugging the Discord bot without requiring a full Discord environment.

These modules are only used during local development and should be completely
isolated from production code.

Modules:
    console_discord: Console interface for Discord bot interaction
    file_watcher: External command interface via file watching
    local_logging: Enhanced logging for local development
    local_dev: Main entry point for local development mode

Note: This entire package is excluded from code coverage as it's development-only.
"""

# Import main entry points for convenience
from .local_dev import main as run_local_dev
from .console_discord import create_console_interface
from .file_watcher import create_file_watcher
from .local_logging import setup_logging, get_logger

__all__ = [
    "run_local_dev",
    "create_console_interface",
    "create_file_watcher",
    "setup_logging",
    "get_logger",
]
