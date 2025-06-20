"""
Unit tests for logging functionality
"""

import logging
import os
import tempfile
import time
from datetime import datetime

import pytest

from src.log_config import ColoredFormatter  # Changed from src.logging
from tests.utils.assertions import assert_timestamp_format


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def log_file(temp_log_dir):
    """Create a log file in the temporary directory"""
    log_path = os.path.join(temp_log_dir, "test.log")
    return log_path


@pytest.fixture
def file_handler(log_file):
    """Create a file handler for testing"""
    handler = logging.FileHandler(log_file)
    handler.setFormatter(ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s"))
    return handler


@pytest.fixture
def test_logger(file_handler):
    """Create a test logger with file handler"""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    yield logger
    logger.removeHandler(file_handler)


class TestLoggingFormat:
    def test_colored_formatter(self):
        """Test that ColoredFormatter formats log messages correctly"""
        formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/fake/path/test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)

        # Split the formatted message into timestamp and content
        timestamp, content = formatted.split(" - ", 1)

        # Verify timestamp format
        assert_timestamp_format(timestamp)

        # Verify content
        assert "INFO" in content
        assert "Test message" in content
        assert "test.py" not in content

    def test_log_levels(self):
        """Test that different log levels are formatted correctly"""
        formatter = ColoredFormatter("%(levelname)s: %(message)s")
        levels = [
            (logging.DEBUG, "Debug message"),
            (logging.INFO, "Info message"),
            (logging.WARNING, "Warning message"),
            (logging.ERROR, "Error message"),
            (logging.CRITICAL, "Critical message"),
        ]

        for level, message in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="/fake/path/test.py",
                lineno=10,
                msg=message,
                args=(),
                exc_info=None,
            )
            formatted = formatter.format(record)
            assert logging.getLevelName(level) in formatted
            assert message in formatted


class TestLogOutput:
    def test_log_file_creation(self, test_logger, log_file):
        """Test that log files are created correctly"""
        test_message = "Test log message"
        test_logger.info(test_message)

        assert os.path.exists(log_file)
        with open(log_file, "r") as f:
            content = f.read()
            assert test_message in content

    def test_log_level_filtering(self, test_logger, log_file):
        """Test that log levels are filtered correctly"""
        test_logger.setLevel(logging.WARNING)

        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")

        with open(log_file, "r") as f:
            content = f.read()
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content

    def test_log_message_content(self, test_logger, log_file):
        """Test that log messages contain all required information"""
        test_message = "Test message with context"
        test_logger.info(test_message)

        with open(log_file, "r") as f:
            content = f.read()
            assert test_message in content
            assert "INFO" in content
            assert datetime.now().strftime("%Y-%m-%d") in content


class TestLogRotation:
    def test_size_based_rotation(self, temp_log_dir):
        """Test file size-based log rotation"""
        from logging.handlers import RotatingFileHandler

        log_file = os.path.join(temp_log_dir, "rotation_test.log")
        handler = RotatingFileHandler(
            log_file, maxBytes=100, backupCount=2  # Small size to trigger rotation
        )
        handler.setFormatter(
            ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        logger = logging.getLogger("rotation_test")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Write enough logs to trigger rotation
        for i in range(10):
            logger.info(
                f"Test message {i} " * 10
            )  # Make message large enough to trigger rotation

        # Check that rotation files were created
        assert os.path.exists(log_file)
        assert os.path.exists(f"{log_file}.1")
        assert os.path.exists(f"{log_file}.2")

        # Cleanup
        logger.removeHandler(handler)

    def test_time_based_rotation(self, temp_log_dir):
        """Test time-based log rotation"""
        from logging.handlers import TimedRotatingFileHandler

        log_file = os.path.join(temp_log_dir, "time_rotation_test.log")
        handler = TimedRotatingFileHandler(
            log_file,
            when="S",  # Rotate every second for testing
            interval=1,
            backupCount=2,
        )
        handler.setFormatter(
            ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        logger = logging.getLogger("time_rotation_test")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Write some logs
        logger.info("First message")
        time.sleep(2)  # Wait for rotation
        logger.info("Second message")

        # Check that rotation files were created
        assert os.path.exists(log_file)
        assert (
            len(
                [
                    f
                    for f in os.listdir(temp_log_dir)
                    if f.startswith("time_rotation_test.log.")
                ]
            )
            > 0
        )

        # Cleanup
        logger.removeHandler(handler)

    def test_old_log_cleanup(self, temp_log_dir):
        """Test cleanup of old log files"""
        from logging.handlers import RotatingFileHandler

        log_file = os.path.join(temp_log_dir, "cleanup_test.log")
        handler = RotatingFileHandler(
            log_file, maxBytes=100, backupCount=2  # Keep only 2 backup files
        )
        handler.setFormatter(
            ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        logger = logging.getLogger("cleanup_test")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Write enough logs to trigger multiple rotations
        for i in range(10):
            logger.info(f"Test message {i} " * 10)

        # Check that only the specified number of backup files exist
        backup_files = [
            f for f in os.listdir(temp_log_dir) if f.startswith("cleanup_test.log.")
        ]
        assert len(backup_files) <= 2

        # Cleanup
        logger.removeHandler(handler)
