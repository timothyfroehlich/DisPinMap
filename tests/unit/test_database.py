"""
Unit tests for Database module including session management, constraints, and error handling
Supports both SQLite and PostgreSQL databases
"""

import os
import tempfile

import pytest

from src.database import ChannelConfig, Database, MonitoringTarget, SeenSubmission
from tests.utils.db_utils import (
    cleanup_test_database,
    setup_test_database,
    verify_channel_config,
    verify_database_target,
)


@pytest.fixture(params=["sqlite", "postgres"])
def db_type(request):
    """Fixture to provide database type for testing"""
    return request.param


@pytest.fixture
def db(db_type):
    """Create test database of specified type"""
    test_db = setup_test_database(db_type)
    yield test_db
    cleanup_test_database(test_db)


class TestDatabaseEdgeCases:
    def test_duplicate_target_addition(self, db):
        """Test that adding duplicate targets raises IntegrityError"""
        channel_id = 12345
        _ = 67890  # guild_id for context

        # Add first target
        db.add_monitoring_target(channel_id, "latlong", "30.0,97.0,10")

        # Adding the same target should raise an exception
        with pytest.raises(Exception, match="already being monitored"):
            db.add_monitoring_target(channel_id, "latlong", "30.0,97.0,10")

    def test_remove_nonexistent_target(self, db):
        """Test removing a target that doesn't exist"""
        channel_id = 12345
        guild_id = 67890

        # Create channel config first
        db.update_channel_config(channel_id, guild_id)

        # Remove nonexistent target - should not raise error
        db.remove_monitoring_target(channel_id, "location", "nonexistent")

        # Verify no targets exist
        verify_database_target(db, channel_id, 0)

    def test_update_nonexistent_target_poll_rate(self, db):
        """Test updating poll rate for non-existent target"""
        result = db.update_monitoring_target_poll_rate(99999, 30)
        assert result is False

    def test_mark_duplicate_submissions_seen(self, db):
        """Test marking the same submission as seen multiple times"""
        channel_id = 12345
        guild_id = 67890
        submission_ids = [1, 2, 3]

        # Create channel config first
        db.update_channel_config(channel_id, guild_id)

        # Mark submissions as seen twice - should not raise errors
        db.mark_submissions_seen(channel_id, submission_ids)
        db.mark_submissions_seen(channel_id, submission_ids)

        # Verify only one record per submission exists
        with db.get_session() as session:
            for submission_id in submission_ids:
                count = (
                    session.query(SeenSubmission)
                    .filter_by(channel_id=channel_id, submission_id=submission_id)
                    .count()
                )
                assert count == 1

    def test_empty_submission_ids_list(self, db):
        """Test handling empty submission IDs list"""
        channel_id = 12345
        guild_id = 67890

        # Create channel config first
        db.update_channel_config(channel_id, guild_id)

        # Mark empty list as seen - should not raise error
        db.mark_submissions_seen(channel_id, [])

        # Verify no records were created
        with db.get_session() as session:
            count = (
                session.query(SeenSubmission).filter_by(channel_id=channel_id).count()
            )
            assert count == 0

    def test_filter_submissions_empty_list(self, db):
        """Test filtering empty list of submissions"""
        channel_id = 12345

        result = db.filter_new_submissions(channel_id, [])
        assert result == []

    def test_get_active_channels_no_targets(self, db):
        """Test getting active channels when no targets exist"""
        channel_id = 12345
        guild_id = 67890

        # Create active channel config but no targets
        db.update_channel_config(channel_id, guild_id, is_active=True)

        active_channels = db.get_active_channels()
        assert len(active_channels) == 0  # Should be filtered out due to no targets

    def test_get_monitoring_targets_empty_channel(self, db):
        """Test getting targets for channel with no targets"""
        channel_id = 12345

        targets = db.get_monitoring_targets(channel_id)
        assert targets == []

    def test_clear_monitoring_targets_empty_channel(self, db):
        """Test clearing targets for channel with no targets"""
        channel_id = 12345

        # Should not raise errors
        db.clear_monitoring_targets(channel_id)

    def test_clear_seen_submissions_empty_channel(self, db):
        """Test clearing seen submissions for channel with no submissions"""
        channel_id = 12345

        # Should not raise errors
        db.clear_seen_submissions(channel_id)

    def test_update_channel_monitoring_targets_poll_rate_no_targets(self, db):
        """Test updating poll rate for channel with no targets"""
        channel_id = 12345

        result = db.update_channel_monitoring_targets_poll_rate(channel_id, 30)
        assert result == 0  # No targets updated

    def test_channel_config_update_nonexistent(self, db):
        """Test updating non-existent channel config creates new one"""
        channel_id = 12345
        guild_id = 67890

        # Should create new config
        db.update_channel_config(
            channel_id, guild_id, is_active=True, poll_rate_minutes=45
        )

        verify_channel_config(
            db, channel_id, {"is_active": True, "poll_rate_minutes": 45}
        )

    def test_channel_config_update_existing(self, db):
        """Test updating existing channel config"""
        channel_id = 12345
        guild_id = 67890

        # Create initial config
        db.update_channel_config(
            channel_id, guild_id, is_active=False, poll_rate_minutes=60
        )

        # Update existing config
        db.update_channel_config(
            channel_id, guild_id, is_active=True, notification_types="all"
        )

        verify_channel_config(
            db,
            channel_id,
            {
                "is_active": True,
                "notification_types": "all",
                "poll_rate_minutes": 60,  # Should remain unchanged
            },
        )


class TestDatabaseSessionManagement:
    def test_database_init_creates_tables(self, db):
        """Test that database initialization creates all required tables"""
        # Verify tables exist by querying them
        with db.get_session() as session:
            session.query(ChannelConfig).first()
            session.query(MonitoringTarget).first()
            session.query(SeenSubmission).first()


class TestDatabaseConstraints:
    def test_unique_channel_submission_constraint(self, db):
        """Test that unique constraint on channel_id + submission_id works"""
        channel_id = 12345
        guild_id = 67890

        # Create channel config first
        db.update_channel_config(channel_id, guild_id)

        # Mark submission as seen
        db.mark_submissions_seen(channel_id, [123])

        # Marking same submission again should not raise error
        db.mark_submissions_seen(channel_id, [123])

        # Verify only one record exists
        with db.get_session() as session:
            count = (
                session.query(SeenSubmission)
                .filter_by(channel_id=channel_id, submission_id=123)
                .count()
            )
            assert count == 1

    def test_target_ordering_consistency(self, db):
        """Test that targets are returned in consistent order (by ID)"""
        channel_id = 12345

        # Add targets in specific order
        target_names = ["30.0,97.0,10", "31.0,98.0,15", "32.0,99.0,20"]
        for target_name in target_names:
            db.add_monitoring_target(channel_id, "latlong", target_name)

        # Get targets multiple times and verify order is consistent
        targets1 = db.get_monitoring_targets(channel_id)
        targets2 = db.get_monitoring_targets(channel_id)

        assert len(targets1) == 3
        assert len(targets2) == 3

        # Order should be consistent (by ID)
        for i in range(3):
            assert targets1[i]["target_name"] == targets2[i]["target_name"]
            assert targets1[i]["id"] == targets2[i]["id"]


class TestPostgreSQLSpecific:
    @pytest.mark.skipif(
        os.getenv("DB_TYPE") != "postgres", reason="PostgreSQL specific test"
    )
    def test_concurrent_connections(self, db):
        """Test handling of concurrent database connections"""
        # Create multiple connections
        connections = []
        for _ in range(5):
            conn = db.get_session()
            connections.append(conn)

        # Verify all connections work
        for conn in connections:
            with conn as session:
                session.query(ChannelConfig).first()

        # Clean up
        for conn in connections:
            conn.close()

    @pytest.mark.skipif(
        os.getenv("DB_TYPE") != "postgres", reason="PostgreSQL specific test"
    )
    def test_connection_pool(self, db):
        """Test connection pool behavior"""
        # Get multiple sessions from the pool
        sessions = []
        for _ in range(5):
            with db.get_session() as session:
                sessions.append(session)
                session.query(ChannelConfig).first()

        # Verify all sessions worked
        assert len(sessions) == 5

    @pytest.mark.skipif(
        os.getenv("DB_TYPE") != "postgres", reason="PostgreSQL specific test"
    )
    def test_transaction_isolation(self, db):
        """Test transaction isolation level"""
        channel_id = 12345
        guild_id = 67890

        # Start a transaction
        with db.get_session() as session1:
            # Create a config in session1
            db.update_channel_config(channel_id, guild_id, is_active=True)

            # Start another session and verify it doesn't see the uncommitted change
            with db.get_session() as _:
                config = db.get_channel_config(channel_id)
                assert config is None  # Should not see uncommitted change

            # Commit the change
            session1.commit()

        # Now verify the change is visible
        config = db.get_channel_config(channel_id)
        assert config is not None
        assert config["is_active"] is True


class TestDatabasePathConfiguration:
    """Test configurable database path functionality"""

    def test_default_database_path(self):
        """Test that Database uses default path when no path specified"""
        # Create database without specifying path
        db = Database()

        # Should use default path for SQLite
        assert "pinball_bot.db" in str(db.engine.url)
        db.close()

    def test_explicit_database_path(self):
        """Test that Database uses explicitly provided path"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create database with explicit path
            db = Database(db_path=temp_path)

            # Should use the provided path
            assert temp_path in str(db.engine.url)
            db.close()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_environment_variable_database_path(self, monkeypatch):
        """Test that Database uses DATABASE_PATH environment variable"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Set environment variable
            monkeypatch.setenv("DATABASE_PATH", temp_path)

            # Create database without explicit path
            db = Database()

            # Should use environment variable path
            assert temp_path in str(db.engine.url)
            db.close()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_explicit_path_overrides_environment(self, monkeypatch):
        """Test that explicit path parameter overrides environment variable"""
        env_path = "/tmp/env_database.db"
        explicit_path = ":memory:"

        # Set environment variable
        monkeypatch.setenv("DATABASE_PATH", env_path)

        # Create database with explicit path
        db = Database(db_path=explicit_path)

        # Should use explicit path, not environment variable
        assert "memory" in str(db.engine.url)
        assert env_path not in str(db.engine.url)
        db.close()

    def test_database_functionality_with_custom_path(self):
        """Test that database operations work correctly with custom path"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create database with custom path
            db = Database(db_path=temp_path)

            # Test basic database operations
            channel_id = 12345
            guild_id = 67890

            # Add a channel config
            db.update_channel_config(channel_id, guild_id, is_active=True)

            # Verify it was saved
            config = db.get_channel_config(channel_id)
            assert config is not None
            assert config["channel_id"] == channel_id
            assert config["guild_id"] == guild_id
            assert config["is_active"] is True

            db.close()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
