"""
Logging configuration and formatters for the DisPinMap application.
"""

import logging
from colorama import Fore, Style, init

# Initialize colorama
init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on level."""

    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        """Format the log record with colors."""
        # Get the original format
        formatted = super().format(record)

        # Split the message into timestamp and content
        parts = formatted.split(' - ', 1)
        if len(parts) == 2:
            timestamp, content = parts
            # Only color the content part
            if record.levelno in self.COLORS:
                content = self.COLORS[record.levelno] + content + Style.RESET_ALL
            formatted = f"{timestamp} - {content}"
        else:
            # If we can't split, color the whole message
            if record.levelno in self.COLORS:
                formatted = self.COLORS[record.levelno] + formatted + Style.RESET_ALL

        return formatted
