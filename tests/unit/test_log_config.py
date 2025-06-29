"""
Tests for log_config module
"""

import logging
from unittest.mock import Mock

import pytest

from src.log_config import ColoredFormatter


class TestColoredFormatter:
    """Test the ColoredFormatter class"""

    def test_colored_formatter_initialization(self):
        """Test that ColoredFormatter can be instantiated"""
        formatter = ColoredFormatter()
        assert isinstance(formatter, ColoredFormatter)
        assert hasattr(formatter, "COLORS")

    def test_colors_mapping(self):
        """Test that COLORS mapping contains expected log levels"""
        formatter = ColoredFormatter()
        expected_levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]

        for level in expected_levels:
            assert level in formatter.COLORS

    def test_format_with_standard_message(self):
        """Test formatting a standard log message with timestamp and content"""
        formatter = ColoredFormatter()

        # Create a mock record
        record = Mock()
        record.levelno = logging.INFO
        record.getMessage.return_value = "Test message"

        # Mock the parent format method to return a standard format
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                logging.Formatter,
                "format",
                lambda self, record: "2024-01-01 12:00:00 - Test message",
            )

            result = formatter.format(record)

            # Should contain color codes for INFO level (green)
            assert "\033[32m" in result  # Green color code
            assert "\033[0m" in result  # Reset color code
            # The message should be colored, so the original text should be in the result
            assert "Test message" in result

    def test_format_with_non_standard_message(self):
        """Test formatting a message that doesn't follow timestamp - content format"""
        formatter = ColoredFormatter()

        # Create a mock record
        record = Mock()
        record.levelno = logging.ERROR
        record.getMessage.return_value = "Error message"

        # Mock the parent format method to return a non-standard format
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                logging.Formatter,
                "format",
                lambda self, record: "Just a simple message",
            )

            result = formatter.format(record)

            # Should color the entire message for ERROR level (red)
            assert "\033[31m" in result  # Red color code
            assert "\033[0m" in result  # Reset color code
            assert "Just a simple message" in result

    def test_format_with_different_log_levels(self):
        """Test formatting with different log levels"""
        formatter = ColoredFormatter()

        test_cases = [
            (logging.DEBUG, "\033[34m"),  # Blue
            (logging.INFO, "\033[32m"),  # Green
            (logging.WARNING, "\033[33m"),  # Yellow
            (logging.ERROR, "\033[31m"),  # Red
            (logging.CRITICAL, "\033[31m"),  # Red (the bright part is added separately)
        ]

        for level, expected_color in test_cases:
            record = Mock()
            record.levelno = level
            record.getMessage.return_value = f"Message for level {level}"

            with pytest.MonkeyPatch().context() as m:
                m.setattr(
                    logging.Formatter,
                    "format",
                    lambda self, record: f"2024-01-01 12:00:00 - {record.getMessage()}",
                )

                result = formatter.format(record)

                assert expected_color in result
                assert "\033[0m" in result  # Reset color code

    def test_format_with_unknown_log_level(self):
        """Test formatting with a log level not in COLORS mapping"""
        formatter = ColoredFormatter()

        # Create a mock record with an unknown level
        record = Mock()
        record.levelno = 999  # Unknown level
        record.getMessage.return_value = "Unknown level message"

        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                logging.Formatter,
                "format",
                lambda self, record: "2024-01-01 12:00:00 - Unknown level message",
            )

            result = formatter.format(record)

            # Should not contain any color codes
            assert "\033[" not in result
            assert "2024-01-01 12:00:00 - Unknown level message" == result
