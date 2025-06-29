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

# Import and re-export the api_mocker fixture
from tests.utils.api_mocker import api_mocker  # noqa: F401


@pytest.fixture(scope="function")
def db_session(request):
    """
    Yields a SQLAlchemy session object that is isolated for each test function.

    This is the core fixture that enables parallel test execution. It achieves
    isolation by creating a separate temporary SQLite database file for each
    `pytest-xdist` worker. It's safe to use when not running in parallel.

    Args:
        request: The pytest request object, used to access context.
    """
    # Check if the 'worker_id' attribute exists, which is provided by pytest-xdist
    if hasattr(request.config, "workerinput"):
        worker_id = request.config.workerinput["workerid"]
    else:
        worker_id = "master"

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


# This makes api_mocker available to all tests without explicit import
