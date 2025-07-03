"""
Schema validation tests for SQLAlchemy models.

Tests database constraints, data integrity rules, and schema consistency.
These tests validate that our database schema is properly defined and
constraints work as expected.
"""

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.models import Base, ChannelConfig, MonitoringTarget


class TestSchemaValidation:
    """Test database schema validation and constraints"""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing with foreign key support"""
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            # Enable foreign key constraints in SQLite
            connect_args={"check_same_thread": False},
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(bind=engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_schema_creation_success(self, engine):
        """Test that schema creates without errors"""
        # Schema creation should succeed
        Base.metadata.create_all(bind=engine)

        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "channel_configs" in tables
        assert "monitoring_targets" in tables
        assert "seen_submissions" in tables

    def test_monitoring_target_location_constraints(self, session):
        """Test location target constraints work correctly"""
        # Create channel config first
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Valid location target should work
        location_target = MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=123,
            # No coordinates for location targets
            latitude=None,
            longitude=None,
        )
        session.add(location_target)
        session.commit()

        assert location_target.id is not None
        assert location_target.is_location_target()
        assert not location_target.is_geographic_target()

    def test_monitoring_target_geographic_constraints(self, session):
        """Test geographic target constraints work correctly"""
        # Create channel config first
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Valid geographic target should work
        geo_target = MonitoringTarget(
            channel_id=12345,
            target_type="geographic",
            display_name="Test Coordinates",
            # No location_id for geographic targets
            location_id=None,
            latitude=30.2672,
            longitude=-97.7431,
            radius_miles=25,
        )
        session.add(geo_target)
        session.commit()

        assert geo_target.id is not None
        assert geo_target.is_geographic_target()
        assert not geo_target.is_location_target()

    def test_coordinate_validation_constraints(self, session):
        """Test coordinate range validation"""
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Valid coordinates should work
        valid_target = MonitoringTarget(
            channel_id=12345,
            target_type="geographic",
            display_name="Valid Coords",
            latitude=45.0,  # Valid latitude
            longitude=90.0,  # Valid longitude
            radius_miles=50,  # Valid radius
        )
        session.add(valid_target)
        session.commit()
        assert valid_target.id is not None

    def test_invalid_target_type_constraint(self, session):
        """Test that invalid target types are rejected"""
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Invalid target type should fail
        with pytest.raises((IntegrityError, ValueError)):
            invalid_target = MonitoringTarget(
                channel_id=12345,
                target_type="invalid_type",  # Should fail constraint
                display_name="Invalid Target",
                location_id=123,
            )
            session.add(invalid_target)
            session.commit()

    def test_mixed_data_constraint_violation(self, session):
        """Test that location targets cannot have coordinates"""
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Location target with coordinates should fail
        with pytest.raises(IntegrityError):
            mixed_target = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Mixed Data",
                location_id=123,
                latitude=30.0,  # Should not be allowed for location targets
                longitude=-97.0,
            )
            session.add(mixed_target)
            session.commit()

    def test_uniqueness_constraints(self, session):
        """Test uniqueness constraints prevent duplicates"""
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)
        session.commit()

        # Create first target
        target1 = MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=123,
        )
        session.add(target1)
        session.commit()

        # Duplicate location target should fail
        with pytest.raises(IntegrityError):
            target2 = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Different Name",  # Different name but same location_id
                location_id=123,  # Duplicate location_id in same channel
            )
            session.add(target2)
            session.commit()

    def test_foreign_key_constraints(self, session):
        """Test foreign key relationships work correctly"""
        # Target without channel config should fail
        with pytest.raises(IntegrityError):
            orphan_target = MonitoringTarget(
                channel_id=99999,  # Non-existent channel
                target_type="location",
                display_name="Orphan Target",
                location_id=123,
            )
            session.add(orphan_target)
            session.commit()

    def test_model_helper_methods(self, session):
        """Test model helper methods work correctly"""
        config = ChannelConfig(channel_id=12345, guild_id=67890)
        session.add(config)

        # Test geographic target helpers
        geo_target = MonitoringTarget(
            channel_id=12345,
            target_type="geographic",
            display_name="Test Coords",
            latitude=30.2672,
            longitude=-97.7431,
            radius_miles=25,
        )
        session.add(geo_target)
        session.commit()

        # Test coordinate retrieval
        coords = geo_target.get_coordinates()
        assert coords == (30.2672, -97.7431, 25)

        # Test coordinate formatting
        formatted = geo_target.format_coordinates()
        assert "30.26720" in formatted
        assert "25mi" in formatted

        # Test location target helpers
        location_target = MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=456,
        )
        session.add(location_target)
        session.commit()

        # Location targets should not have coordinates
        assert location_target.get_coordinates() is None
        assert location_target.get_location_id() == 456

    def test_schema_constraints_comprehensive(self, session):
        """Comprehensive test of all schema constraints"""
        # Create valid channel config
        config = ChannelConfig(
            channel_id=12345,
            guild_id=67890,
            poll_rate_minutes=60,
            notification_types="machines",
            is_active=True,
        )
        session.add(config)
        session.commit()

        # Test valid location target
        location_target = MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Ground Kontrol",
            location_id=874,
        )
        session.add(location_target)

        # Test valid geographic target
        geo_target = MonitoringTarget(
            channel_id=12345,
            target_type="geographic",
            display_name="Downtown Austin",
            latitude=30.2672,
            longitude=-97.7431,
            radius_miles=10,
        )
        session.add(geo_target)

        session.commit()

        # Verify both targets were created successfully
        targets = session.query(MonitoringTarget).filter_by(channel_id=12345).all()
        assert len(targets) == 2

        location_targets = [t for t in targets if t.target_type == "location"]
        geo_targets = [t for t in targets if t.target_type == "geographic"]

        assert len(location_targets) == 1
        assert len(geo_targets) == 1

        # Verify relationships work
        assert location_targets[0].channel_config.channel_id == 12345
        assert geo_targets[0].channel_config.guild_id == 67890
