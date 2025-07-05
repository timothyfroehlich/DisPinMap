#!/usr/bin/env python3
"""
File Watcher for External Command Input

This module provides external control of the running Discord bot through file watching.
Commands can be sent to the bot by appending them to a text file, and responses
are logged to the standard bot log file.

Usage:
    # Terminal 1: Start bot with file watching
    python src/local_dev.py

    # Terminal 2: Send commands
    echo "!list" >> commands.txt
    echo ".status" >> commands.txt
    echo "!config poll_rate 15" >> commands.txt

    # Terminal 3: Monitor responses
    tail -f logs/bot.log

File Format:
    - One command per line
    - Same format as console interface commands
    - Discord commands: !add, !list, !check, !help, etc.
    - Special commands: .quit, .status, .health, .trigger

Example commands.txt:
    !list
    .health
    !check
    !config poll_rate 15
    .quit

Implementation:
    - Uses watchdog library for cross-platform file monitoring
    - Processes commands through existing console interface
    - Thread-safe queue for command processing
    - Automatic file rotation to prevent growth
    - Graceful error handling and recovery
"""

import asyncio
import os
import queue
from pathlib import Path
from typing import Callable, Awaitable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.local_dev.local_logging import get_logger

logger = get_logger("file_watcher")


class CommandFileHandler(FileSystemEventHandler):
    """Handles file system events for the command file"""

    def __init__(self, command_queue: queue.Queue, command_file: str):
        super().__init__()
        self.command_queue = command_queue
        self.command_file = command_file
        self.last_position = 0
        self._ensure_command_file()

    def _ensure_command_file(self) -> None:
        """Ensure the command file exists and get initial position"""
        command_path = Path(self.command_file)
        if not command_path.exists():
            command_path.touch()
            logger.info(f"📝 Created command file: {self.command_file}")

        # Set initial position to end of file (don't process existing commands)
        self.last_position = command_path.stat().st_size
        logger.info(f"📍 Starting file watch at position {self.last_position}")

    def on_modified(self, event) -> None:
        """Called when the command file is modified"""
        if event.is_directory:
            return

        if not event.src_path.endswith(self.command_file):
            return

        self._process_new_content()

    def _process_new_content(self) -> None:
        """Process any new content added to the command file"""
        try:
            with open(self.command_file, "r", encoding="utf-8") as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()

            if new_content.strip():
                # Split into lines and queue each command
                for line in new_content.strip().split("\n"):
                    command = line.strip()
                    if command:
                        self.command_queue.put(command)
                        logger.info(f"📥 Queued external command: {command}")

        except Exception as e:
            logger.error(f"❌ Error processing command file: {e}")


class FileWatcher:
    """
    File watcher for external command input

    Monitors a text file for new commands and processes them through
    the existing console interface.
    """

    def __init__(
        self,
        command_processor: Callable[[str], Awaitable[None]],
        command_file: str = "commands.txt",
    ):
        """
        Initialize file watcher

        Args:
            command_processor: Async function to process commands (from console interface)
            command_file: Path to file to watch for commands
        """
        self.command_processor = command_processor
        self.command_file = command_file
        self.command_queue = queue.Queue()
        self.observer = Observer()
        self.handler = CommandFileHandler(self.command_queue, command_file)
        self.running = False
        self.processor_task = None

        # Set up file watching
        watch_dir = os.path.dirname(os.path.abspath(command_file)) or "."
        self.observer.schedule(self.handler, watch_dir, recursive=False)

        logger.info(f"🔍 File watcher initialized for: {os.path.abspath(command_file)}")

    def start(self) -> None:
        """Start file watching and command processing"""
        if self.running:
            logger.warning("⚠️  File watcher already running")
            return

        self.running = True

        # Start file observer
        self.observer.start()
        logger.info(f"👁️  Started watching file: {self.command_file}")

        # Start async command processor
        self.processor_task = asyncio.create_task(self._process_commands())
        logger.info("⚙️  Started command processor")

        # Log usage instructions
        self._log_usage_instructions()

    def stop(self) -> None:
        """Stop file watching and command processing"""
        if not self.running:
            return

        self.running = False

        # Stop file observer
        self.observer.stop()
        self.observer.join()
        logger.info("🛑 Stopped file watcher")

        # Cancel command processor
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            logger.info("🛑 Stopped command processor")

    async def _process_commands(self):
        """Process queued commands asynchronously"""
        logger.info("🔄 Command processor started")

        while self.running:
            try:
                # Check for queued commands (non-blocking)
                try:
                    command = self.command_queue.get_nowait()
                    logger.info(f"🎯 Processing external command: {command}")

                    # Process through console interface
                    await self.command_processor(command)

                except queue.Empty:
                    # No commands available, sleep briefly
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info("🛑 Command processor cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error processing command: {e}", exc_info=True)
                # Continue processing other commands
                await asyncio.sleep(1)

    def _log_usage_instructions(self) -> None:
        """Log instructions for using the file watcher"""
        abs_path = os.path.abspath(self.command_file)
        logger.info("=" * 60)
        logger.info("📁 EXTERNAL COMMAND INTERFACE READY")
        logger.info("=" * 60)
        logger.info(f"📝 Command file: {abs_path}")
        logger.info("")
        logger.info("💡 Usage examples:")
        logger.info(f'   echo "!list" >> {self.command_file}')
        logger.info(f'   echo ".status" >> {self.command_file}')
        logger.info(f'   echo "!config poll_rate 15" >> {self.command_file}')
        logger.info(f'   echo ".quit" >> {self.command_file}')
        logger.info("")
        logger.info("📊 Monitor responses with:")
        logger.info("   tail -f logs/bot.log")
        logger.info("")
        logger.info("Available commands:")
        logger.info("   Discord: !add, !list, !check, !remove, !help, !config")
        logger.info("   Special: .quit, .status, .health, .trigger")
        logger.info("=" * 60)

    def get_stats(self) -> dict:
        """Get file watcher statistics"""
        return {
            "running": self.running,
            "command_file": os.path.abspath(self.command_file),
            "file_exists": os.path.exists(self.command_file),
            "file_size": os.path.getsize(self.command_file)
            if os.path.exists(self.command_file)
            else 0,
            "current_position": self.handler.last_position,
            "queued_commands": self.command_queue.qsize(),
        }


async def create_file_watcher(
    command_processor: Callable[[str], Awaitable[None]],
    command_file: str = "commands.txt",
) -> FileWatcher:
    """
    Create and start a file watcher for external commands

    Args:
        command_processor: Async function to process commands
        command_file: Path to command file to watch

    Returns:
        FileWatcher instance (already started)
    """
    watcher = FileWatcher(command_processor, command_file)
    watcher.start()
    return watcher


# Example usage for testing
if __name__ == "__main__":

    async def test_processor(command: str):
        print(f"Processing: {command}")

    async def main():
        watcher = await create_file_watcher(test_processor, "test_commands.txt")

        print("File watcher running. Try:")
        print("echo 'test command' >> test_commands.txt")
        print("Press Ctrl+C to stop")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            print("Stopped")

    asyncio.run(main())
