"""
Core fixtures for the DisPinMap test suite.

This file contains the foundational fixtures that will be used across unit,
integration, and simulation tests. The most critical fixture here is
`db_session`, which provides isolated database sessions for parallel testing.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import (  # Assuming your models use a declarative base from this module
    Base,
)


@pytest.fixture(scope="session")
def db_session(worker_id):
    """
    Yields a SQLAlchemy session object that is isolated for each parallel test worker.

    This is the core fixture that enables parallel test execution. It achieves
    isolation by creating a separate temporary SQLite database file for each
    `pytest-xdist` worker.

    Args:
        worker_id: The ID of the `pytest-xdist` worker. 'master' if not running in parallel.
    """
    if worker_id == "master":
        # If not running in parallel, use a standard in-memory database
        db_url = "sqlite://"
    else:
        # For parallel workers, create a unique file-based database
        # This ensures complete isolation between processes.
        db_path = f"test_db_{worker_id}.sqlite"
        db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)  # Create all tables defined in your models
    SessionFactory = sessionmaker(bind=engine)

    yield SessionFactory  # Provide the session factory to tests

    engine.dispose()
    if worker_id != "master" and os.path.exists(db_path):
        os.remove(db_path)  # Clean up the temporary database file


# We can add the api_mocker fixture here later.
# For now, the db_session is the priority.
