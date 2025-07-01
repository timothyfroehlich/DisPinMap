"""
Unit tests for the SQLAlchemy models defined in `src/models.py`.

These tests will verify the logic within the model classes themselves,
such as methods, properties, or relationships, without requiring a
database connection.
"""

# To be migrated from `tests_backup/unit/test_add_target_behavior.py` (logic part)

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import RelationshipProperty

from src.models import ChannelConfig, MonitoringTarget, SeenSubmission


def test_monitoring_target_representation():
    """
    Tests the __repr__ or a similar method on the MonitoringTarget model.
    - Creates a model instance in memory.
    - Asserts that its string representation is formatted as expected.
    """
    from datetime import datetime

    # Create a model instance in memory (no database needed)
    target = MonitoringTarget(
        id=1,
        channel_id=12345,
        target_type="location",
        target_name="Ground Kontrol",
        location_id=874,
        poll_rate_minutes=60,
        notification_types="machines",
        last_checked_at=datetime(2024, 1, 1, 12, 0, 0),
        created_at=datetime(2024, 1, 1, 10, 0, 0),
    )

    # Test string representation
    repr_str = repr(target)
    assert "MonitoringTarget" in repr_str
    # The default SQLAlchemy __repr__ typically includes the class name
    # and some identifier information


def test_channel_config_is_active_property():
    """
    Tests any custom logic associated with the ChannelConfig model,
    for example, a property that determines if a channel is active
    based on its targets or other settings.
    """
    from datetime import datetime

    # Create a channel config instance
    config = ChannelConfig(
        channel_id=12345,
        guild_id=11111,
        poll_rate_minutes=60,
        notification_types="machines",
        is_active=True,
        last_poll_at=datetime(2024, 1, 1, 12, 0, 0),
        created_at=datetime(2024, 1, 1, 10, 0, 0),
    )

    # Test the is_active property
    assert config.is_active is True

    # Test changing is_active
    config.is_active = False
    assert config.is_active is False

    # Test other properties work as expected
    assert config.channel_id == 12345
    assert config.guild_id == 11111
    assert config.poll_rate_minutes == 60
    assert config.notification_types == "machines"


def test_model_initialization_defaults():
    """
    Tests that models initialize with correct default values for their fields.
    - Instantiates a model without providing all arguments.
    - Asserts that default values are set correctly.
    """
    # Test that column defaults are defined properly in the schema
    # SQLAlchemy defaults are applied at the database level, not at instantiation

    # Test ChannelConfig column defaults
    config_table = ChannelConfig.__table__
    assert config_table.columns["poll_rate_minutes"].default.arg == 60
    assert config_table.columns["notification_types"].default.arg == "machines"
    assert config_table.columns["is_active"].default.arg is True

    # Test MonitoringTarget column defaults
    target_table = MonitoringTarget.__table__
    assert target_table.columns["poll_rate_minutes"].default.arg == 60
    assert target_table.columns["notification_types"].default.arg == "machines"

    # Test that we can create instances with minimal required fields
    config = ChannelConfig(channel_id=12345, guild_id=11111)
    assert config.channel_id == 12345
    assert config.guild_id == 11111

    target = MonitoringTarget(
        channel_id=12345, target_type="location", target_name="Test Location"
    )
    assert target.channel_id == 12345
    assert target.target_type == "location"
    assert target.target_name == "Test Location"


def test_monitoring_target_model_has_expected_columns():
    """
    Tests that the MonitoringTarget model has the columns we expect.
    This is a basic structural test to catch accidental schema changes.
    """
    # 1. SETUP
    # Get the columns from the SQLAlchemy model's table object
    columns = MonitoringTarget.__table__.columns

    # 2. ASSERT
    # Check for the existence and type of key columns
    assert "id" in columns
    assert isinstance(columns["id"].type, Integer)
    assert columns["id"].primary_key

    assert "channel_id" in columns
    assert isinstance(columns["channel_id"].type, BigInteger)

    assert "target_type" in columns
    assert isinstance(columns["target_type"].type, String)

    assert "target_name" in columns
    assert isinstance(columns["target_name"].type, String)

    assert "last_checked_at" in columns
    assert isinstance(columns["last_checked_at"].type, DateTime)


def test_add_and_remove_seen_submission():
    """Test SeenSubmission model instantiation and basic functionality."""
    from datetime import datetime

    # Test model can be instantiated with correct fields
    seen_submission = SeenSubmission(
        channel_id=12345, submission_id=789, seen_at=datetime.now()
    )

    # Test basic properties
    assert seen_submission.channel_id == 12345
    assert seen_submission.submission_id == 789
    assert isinstance(seen_submission.seen_at, datetime)


def test_model_relationships_are_configured():
    """Test that SQLAlchemy relationships are properly configured."""

    # Test ChannelConfig relationships
    assert hasattr(ChannelConfig, "monitoring_targets")
    assert isinstance(ChannelConfig.monitoring_targets.property, RelationshipProperty)

    assert hasattr(ChannelConfig, "seen_submissions")
    assert isinstance(ChannelConfig.seen_submissions.property, RelationshipProperty)

    # Test MonitoringTarget relationships
    assert hasattr(MonitoringTarget, "channel_config")
    assert isinstance(MonitoringTarget.channel_config.property, RelationshipProperty)

    # Test SeenSubmission relationships
    assert hasattr(SeenSubmission, "channel_config")
    assert isinstance(SeenSubmission.channel_config.property, RelationshipProperty)

    # Test relationship configurations
    # ChannelConfig should have back_populates configured
    assert ChannelConfig.monitoring_targets.property.back_populates == "channel_config"
    assert ChannelConfig.seen_submissions.property.back_populates == "channel_config"

    # Other models should have back_populates configured
    assert (
        MonitoringTarget.channel_config.property.back_populates == "monitoring_targets"
    )
    assert SeenSubmission.channel_config.property.back_populates == "seen_submissions"
