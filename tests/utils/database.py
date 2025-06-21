"""
Database utilities for testing.

This module provides utilities for setting up test databases, cleaning up test data,
and verifying database state. It supports both SQLite and PostgreSQL databases.
"""

import os
from typing import Any, Dict, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from src.database import Database
from src.models import Base, ChannelConfig, MonitoringTarget, SeenSubmission


def get_test_db_url(db_type: str) -> str:
    """Get test database URL from environment or use default."""
    if db_type in ["postgres", "postgresql"]:
        return os.getenv(
            "TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test_db"
        )
    else:
        return "sqlite:///:memory:"


def create_test_engine(db_type: str):
    """Create test database engine."""
    return create_engine(
        get_test_db_url(db_type),
        poolclass=NullPool,  # Disable connection pooling for tests
        echo=False,
    )


def setup_test_database(
    db_type: str = "sqlite", db_path: Optional[str] = None
) -> Database:
    """
    Set up a test database.

    Args:
        db_type: Type of database to use ('sqlite', 'postgres', or 'postgresql')
        db_path: Path to SQLite database file (only used for SQLite)

    Returns:
        Database instance configured for testing
    """
    if db_type == "sqlite":
        if db_path is None:
            db_path = ":memory:"
        # Create a fresh SQLite database instance
        db = Database(db_path)
    elif db_type in ["postgres", "postgresql"]:
        # For PostgreSQL, we need to set the DATABASE_URL environment variable
        # since the Database class uses environment variables for PostgreSQL config
        os.environ["DATABASE_URL"] = get_test_db_url(db_type)
        db = Database()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    # Create tables
    db.init_database()

    return db


def cleanup_test_database(db: Database):
    """
    Clean up test database by removing all test data.

    Args:
        db: Database instance to clean
    """
    try:
        with db.get_session() as session:
            session.query(MonitoringTarget).delete()
            session.query(SeenSubmission).delete()
            session.query(ChannelConfig).delete()
            session.commit()
    except Exception:
        # Ignore errors if tables don't exist
        pass


@pytest.fixture(scope="session")
def db_engine(db_type):
    """Create test database engine."""
    engine = create_test_engine(db_type)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    """Clean up database after each test."""
    yield
    # Clean up all tables
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture
def test_db():
    """Fixture that provides a test database instance."""
    db = setup_test_database()
    yield db
    cleanup_test_database(db)


def verify_database_target(
    db: Database,
    channel_id: int,
    expected_count: int,
    target_type: Optional[str] = None,
):
    """
    Verify that the expected number of targets exist in the database.

    Args:
        db: Database instance to check
        channel_id: Channel ID to check targets for
        expected_count: Expected number of targets
        target_type: Optional target type to verify
    """
    targets = db.get_monitoring_targets(channel_id)
    assert (
        len(targets) == expected_count
    ), f"Expected {expected_count} targets, got {len(targets)}"

    if target_type and expected_count > 0:
        assert any(
            t.get("target_type") == target_type for t in targets
        ), f"No target of type '{target_type}' found in {targets}"


def verify_channel_config(
    db: Database, channel_id: int, expected_values: Dict[str, Any]
):
    """
    Verify channel configuration values.

    Args:
        db: Database instance to check
        channel_id: Channel ID to check
        expected_values: Dictionary of expected values
    """
    config = db.get_channel_config(channel_id)
    assert config is not None, f"No config found for channel {channel_id}"

    for key, value in expected_values.items():
        assert (
            config.get(key) == value
        ), f"Expected {key}={value}, got {config.get(key)}"
