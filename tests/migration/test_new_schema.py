"""
Test new schema validation and constraints.

Tests all data integrity constraints, validation rules, and edge cases
for the new normalized database schema.

Tests cover:
- All constraint validations work correctly
- Data integrity rules are enforced
- Edge cases and invalid data rejection
- Helper methods and validation functions
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.models import Base, ChannelConfig, MonitoringTarget


class TestNewSchemaValidation:
    """Test all validation constraints and rules in the new schema"""

    def setup_method(self):
        """Set up test database with new schema"""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_channel_config(self, session, channel_id=12345):
        """Helper to create a channel config for testing"""
        channel_config = ChannelConfig(
            channel_id=channel_id,
            guild_id=67890,
            poll_rate_minutes=30,
            notification_types="machines,submissions",
        )
        session.add(channel_config)
        session.flush()
        return channel_config

    def test_valid_location_target(self):
        """Test creating valid location targets"""
        with self.Session() as session:
            self.create_channel_config(session)

            target = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Valid Arcade",
                location_id=123,
                poll_rate_minutes=60,
                notification_types="machines",
            )
            session.add(target)
            session.commit()

            # Verify target was created successfully
            saved_target = session.query(MonitoringTarget).first()
            assert saved_target.target_type == "location"
            assert saved_target.location_id == 123
            assert saved_target.latitude is None
            assert saved_target.longitude is None
            # Note: radius_miles has a default of 25 in the current schema

    def test_valid_geographic_target(self):
        """Test creating valid geographic targets"""
        with self.Session() as session:
            self.create_channel_config(session)

            target = MonitoringTarget(
                channel_id=12345,
                target_type="geographic",
                display_name="Austin Area",
                latitude=30.26715,
                longitude=-97.74306,
                radius_miles=5,
                poll_rate_minutes=45,
                notification_types="submissions",
            )
            session.add(target)
            session.commit()

            # Verify target was created successfully
            saved_target = session.query(MonitoringTarget).first()
            assert saved_target.target_type == "geographic"
            assert saved_target.latitude == 30.26715
            assert saved_target.longitude == -97.74306
            assert saved_target.radius_miles == 5
            assert saved_target.location_id is None

    def test_invalid_target_type(self):
        """Test that invalid target types are rejected"""
        with self.Session() as session:
            self.create_channel_config(session)

            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="invalid_type",
                    display_name="Invalid Target",
                    location_id=123,
                )
                session.add(target)
                session.commit()

    def test_latitude_validation(self):
        """Test latitude validation constraints"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test invalid latitude > 90
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Latitude High",
                    latitude=100.0,
                    longitude=-97.0,
                    radius_miles=10,
                )
                session.add(target)
                session.commit()

            session.rollback()

            # Test invalid latitude < -90
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Latitude Low",
                    latitude=-100.0,
                    longitude=-97.0,
                    radius_miles=10,
                )
                session.add(target)
                session.commit()

    def test_longitude_validation(self):
        """Test longitude validation constraints"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test invalid longitude > 180
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Longitude High",
                    latitude=30.0,
                    longitude=200.0,
                    radius_miles=10,
                )
                session.add(target)
                session.commit()

            session.rollback()

            # Test invalid longitude < -180
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Longitude Low",
                    latitude=30.0,
                    longitude=-200.0,
                    radius_miles=10,
                )
                session.add(target)
                session.commit()

    def test_radius_validation(self):
        """Test radius_miles validation constraints"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test invalid radius = 0
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Radius Zero",
                    latitude=30.0,
                    longitude=-97.0,
                    radius_miles=0,
                )
                session.add(target)
                session.commit()

            session.rollback()

            # Test invalid radius > 100
            with pytest.raises(IntegrityError):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Invalid Radius High",
                    latitude=30.0,
                    longitude=-97.0,
                    radius_miles=150,
                )
                session.add(target)
                session.commit()

    def test_edge_case_coordinates(self):
        """Test edge case coordinate values"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test boundary values that should be valid
            valid_edge_cases = [
                (90.0, 180.0, 1),  # Max lat, max lon, min radius
                (-90.0, -180.0, 100),  # Min lat, min lon, max radius
                (0.0, 0.0, 50),  # Equator and prime meridian
            ]

            for i, (lat, lon, radius) in enumerate(valid_edge_cases):
                target = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name=f"Edge Case {i}",
                    latitude=lat,
                    longitude=lon,
                    radius_miles=radius,
                )
                session.add(target)

            session.commit()

            # Verify all edge cases were accepted
            targets = session.query(MonitoringTarget).all()
            assert len(targets) == 3

    def test_unique_location_constraint(self):
        """Test unique constraint for location targets"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Create first location target
            target1 = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="First Location",
                location_id=123,
            )
            session.add(target1)
            session.commit()

            # Try to create duplicate location target - should fail
            with pytest.raises(IntegrityError):
                target2 = MonitoringTarget(
                    channel_id=12345,
                    target_type="location",
                    display_name="Duplicate Location",
                    location_id=123,  # Same location_id and channel_id
                )
                session.add(target2)
                session.commit()

    def test_unique_geographic_constraint(self):
        """Test unique constraint for geographic targets"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Create first geographic target
            target1 = MonitoringTarget(
                channel_id=12345,
                target_type="geographic",
                display_name="First Area",
                latitude=30.0,
                longitude=-97.0,
                radius_miles=10,
            )
            session.add(target1)
            session.commit()

            # Try to create duplicate geographic target - should fail
            with pytest.raises(IntegrityError):
                target2 = MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Duplicate Area",
                    latitude=30.0,  # Same coordinates
                    longitude=-97.0,  # Same coordinates
                    radius_miles=10,  # Same radius
                )
                session.add(target2)
                session.commit()

    def test_different_channels_allow_duplicates(self):
        """Test that different channels can have same targets"""
        with self.Session() as session:
            # Create two channel configs
            self.create_channel_config(session, channel_id=12345)
            self.create_channel_config(session, channel_id=54321)

            # Create same location target for both channels - should succeed
            target1 = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Shared Location",
                location_id=123,
            )
            target2 = MonitoringTarget(
                channel_id=54321,
                target_type="location",
                display_name="Shared Location",
                location_id=123,  # Same location_id but different channel
            )
            session.add(target1)
            session.add(target2)
            session.commit()

            # Verify both were created
            targets = session.query(MonitoringTarget).all()
            assert len(targets) == 2

    def test_helper_methods(self):
        """Test helper methods on MonitoringTarget model"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test location target helper methods
            location_target = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Test Location",
                location_id=123,
            )
            session.add(location_target)

            # Test geographic target helper methods
            geo_target = MonitoringTarget(
                channel_id=12345,
                target_type="geographic",
                display_name="Test Area",
                latitude=30.26715,
                longitude=-97.74306,
                radius_miles=5,
            )
            session.add(geo_target)
            session.commit()

            # Test location target helpers
            assert location_target.is_location_target() is True
            assert location_target.is_geographic_target() is False
            assert location_target.get_location_id() == 123
            assert location_target.get_coordinates() is None
            assert location_target.format_coordinates() is None
            assert location_target.validate_data_consistency() is True

            # Test geographic target helpers
            assert geo_target.is_location_target() is False
            assert geo_target.is_geographic_target() is True
            assert geo_target.get_location_id() is None
            assert geo_target.get_coordinates() == (30.26715, -97.74306, 5)
            coord_display = geo_target.format_coordinates()
            assert "30.26715" in coord_display
            assert "5mi" in coord_display
            assert geo_target.validate_data_consistency() is True

    def test_data_consistency_validation(self):
        """Test validate_data_consistency method with invalid combinations"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test invalid location target (missing location_id)
            invalid_location = MonitoringTarget(
                channel_id=12345,
                target_type="location",
                display_name="Invalid Location",
                # location_id is None but should be set for location targets
            )
            assert invalid_location.validate_data_consistency() is False

            # Test invalid geographic target (missing coordinates)
            invalid_geo = MonitoringTarget(
                channel_id=12345,
                target_type="geographic",
                display_name="Invalid Geographic",
                latitude=30.0,
                # longitude is None but should be set for geographic targets
                radius_miles=10,
            )
            assert invalid_geo.validate_data_consistency() is False

    def test_repr_methods(self):
        """Test string representation methods"""
        # Test location target repr
        location_target = MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=123,
        )
        repr_str = repr(location_target)
        assert "type='location'" in repr_str
        assert "location_id=123" in repr_str
        assert "Test Location" in repr_str

        # Test geographic target repr
        geo_target = MonitoringTarget(
            channel_id=12345,
            target_type="geographic",
            display_name="Test Area",
            latitude=30.26715,
            longitude=-97.74306,
            radius_miles=5,
        )
        repr_str = repr(geo_target)
        assert "type='geographic'" in repr_str
        assert "30.26715" in repr_str
        assert "-97.74306" in repr_str
        assert "5mi" in repr_str

    def test_schema_integrity_comprehensive(self):
        """Comprehensive test of all schema integrity rules"""
        with self.Session() as session:
            self.create_channel_config(session)

            # Test all valid combinations
            valid_targets = [
                # Valid location target
                MonitoringTarget(
                    channel_id=12345,
                    target_type="location",
                    display_name="Valid Location",
                    location_id=123,
                    poll_rate_minutes=60,
                    notification_types="machines",
                ),
                # Valid geographic target with all fields
                MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Valid Geographic",
                    latitude=30.0,
                    longitude=-97.0,
                    radius_miles=10,
                    poll_rate_minutes=45,
                    notification_types="submissions",
                ),
                # Valid geographic target with boundary values
                MonitoringTarget(
                    channel_id=12345,
                    target_type="geographic",
                    display_name="Boundary Geographic",
                    latitude=-90.0,
                    longitude=180.0,
                    radius_miles=1,
                    poll_rate_minutes=30,
                    notification_types="machines,submissions",
                ),
            ]

            # All should be added successfully
            for target in valid_targets:
                session.add(target)

            session.commit()

            # Verify all targets were created
            saved_targets = session.query(MonitoringTarget).all()
            assert len(saved_targets) == 3

            # Verify each target maintains data integrity
            for target in saved_targets:
                assert target.validate_data_consistency() is True
                if target.is_location_target():
                    assert target.location_id is not None
                    assert target.latitude is None
                    assert target.longitude is None
                elif target.is_geographic_target():
                    assert target.location_id is None
                    assert target.latitude is not None
                    assert target.longitude is not None
                    assert target.radius_miles is not None
