#!/usr/bin/env python3
"""
Enhanced logging configuration for local development
"""

import logging
import logging.handlers
import os
import sys


class ConsoleAndFileFormatter(logging.Formatter):
    """Custom formatter that adds context prefixes for different log sources"""

    def __init__(self):
        super().__init__(
            fmt="[%(asctime)s] [%(name)s] %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        # Add context prefixes based on logger name
        if record.name.startswith("discord"):
            record.name = "DISCORD"
        elif "monitor" in record.name.lower() or "runner" in record.name.lower():
            record.name = "MONITOR"
        elif "console" in record.name.lower():
            record.name = "CONSOLE"
        elif record.name == "__main__" or record.name == "main":
            record.name = "BOT"
        elif record.name.startswith("src."):
            record.name = record.name.replace("src.", "").upper()

        return super().format(record)


def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log") -> None:
    """
    Set up logging for local development with both console and file output

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file with rotation
    """
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Create custom formatter
    formatter = ConsoleAndFileFormatter()

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler - for interactive output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler - for persistent logging
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Configure Discord.py logging to be less verbose unless DEBUG mode
    if level > logging.DEBUG:
        logging.getLogger("discord").setLevel(logging.WARNING)
        logging.getLogger("discord.http").setLevel(logging.WARNING)
        logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    else:
        logging.getLogger("discord").setLevel(logging.INFO)

    # Log startup message
    logger = logging.getLogger("local_logging")
    logger.info(f"✅ Logging configured - Level: {log_level}, File: {log_file}")
    logger.info("📁 Log rotation: 10MB max, 5 backup files")

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)
