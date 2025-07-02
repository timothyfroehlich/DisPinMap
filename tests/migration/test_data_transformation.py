"""
Test data transformation pipeline for schema redesign migration.

Tests the export, transformation, and import pipeline that will migrate
data from the current schema to the new normalized schema.

Tests cover:
- Export from current schema format
- Transformation logic for each target type
- Import to new schema with validation
- Data integrity and completeness validation
"""

import pytest
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import both old and new models for testing
from src.models import MonitoringTarget as OldMonitoringTarget, ChannelConfig as OldChannelConfig
from src.models_new import MonitoringTarget as NewMonitoringTarget, ChannelConfig as NewChannelConfig
from src.models_new import Base as NewBase


class TestDataTransformationPipeline:
    """Test the complete data transformation pipeline"""

    def setup_method(self):
        """Set up test databases for old and new schemas"""
        # Create separate engines for old and new schemas
        self.old_engine = create_engine("sqlite:///:memory:")
        self.new_engine = create_engine("sqlite:///:memory:")
        
        # Create old schema tables using original models
        from src.models import Base as OldBase
        OldBase.metadata.create_all(self.old_engine)
        
        # Create new schema tables using new models
        NewBase.metadata.create_all(self.new_engine)
        
        # Create session makers
        self.OldSession = sessionmaker(bind=self.old_engine)
        self.NewSession = sessionmaker(bind=self.new_engine)

    def create_sample_old_data(self, session):
        """Create sample data in old schema format for testing"""
        # Create channel config
        channel_config = OldChannelConfig(
            channel_id=12345,
            guild_id=67890,
            poll_rate_minutes=30,
            notification_types="machines,submissions"
        )
        session.add(channel_config)
        session.flush()

        # Create various types of monitoring targets in old format
        targets = [
            # Location target (unchanged in new schema)
            OldMonitoringTarget(
                channel_id=12345,
                target_type="location",
                target_name="Arcade Location Name",
                location_id=123,
                poll_rate_minutes=60,
                notification_types="machines"
            ),
            
            # Geographic target with coordinates (needs transformation)
            OldMonitoringTarget(
                channel_id=12345,
                target_type="latlong",
                target_name="30.26715,-97.74306,5",  # Austin, TX with 5 mile radius
                location_id=None,
                poll_rate_minutes=45,
                notification_types="submissions"
            ),
            
            # Another geographic target
            OldMonitoringTarget(
                channel_id=12345,
                target_type="city",  # This should become 'geographic'
                target_name="40.7128,-74.0060,10",  # NYC with 10 mile radius
                location_id=None,
                poll_rate_minutes=30,
                notification_types="machines,submissions"
            ),
        ]
        
        for target in targets:
            session.add(target)
        
        session.commit()
        return targets

    def test_export_current_data(self):
        """Test exporting data from current schema format"""
        with self.OldSession() as session:
            targets = self.create_sample_old_data(session)
            
            # Export all targets
            exported_targets = []
            for target in session.query(OldMonitoringTarget).all():
                exported_data = {
                    'id': target.id,
                    'channel_id': target.channel_id,
                    'target_type': target.target_type,
                    'target_name': target.target_name,
                    'location_id': target.location_id,
                    'poll_rate_minutes': target.poll_rate_minutes,
                    'notification_types': target.notification_types,
                    'last_checked_at': target.last_checked_at.isoformat() if target.last_checked_at else None,
                    'created_at': target.created_at.isoformat() if target.created_at else None,
                }
                exported_targets.append(exported_data)
            
            # Verify export completeness
            assert len(exported_targets) == 3
            assert all(target['channel_id'] == 12345 for target in exported_targets)
            
            # Verify different target types are present
            types = [target['target_type'] for target in exported_targets]
            assert 'location' in types
            assert 'latlong' in types
            assert 'city' in types

    def test_transform_location_target(self):
        """Test transformation of location targets (should be unchanged)"""
        old_data = {
            'id': 1,
            'channel_id': 12345,
            'target_type': 'location',
            'target_name': 'Test Arcade',
            'location_id': 123,
            'poll_rate_minutes': 60,
            'notification_types': 'machines',
            'last_checked_at': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        # Transform to new format
        transformed = self.transform_target_data(old_data)
        
        # Verify transformation
        assert transformed['target_type'] == 'location'
        assert transformed['display_name'] == 'Test Arcade'
        assert transformed['location_id'] == 123
        assert transformed['latitude'] is None
        assert transformed['longitude'] is None
        assert transformed['radius_miles'] is None

    def test_transform_geographic_target_latlong(self):
        """Test transformation of latlong targets to geographic format"""
        old_data = {
            'id': 2,
            'channel_id': 12345,
            'target_type': 'latlong',
            'target_name': '30.26715,-97.74306,5',
            'location_id': None,
            'poll_rate_minutes': 45,
            'notification_types': 'submissions',
            'last_checked_at': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        # Transform to new format
        transformed = self.transform_target_data(old_data)
        
        # Verify transformation
        assert transformed['target_type'] == 'geographic'
        assert transformed['latitude'] == 30.26715
        assert transformed['longitude'] == -97.74306
        assert transformed['radius_miles'] == 5
        assert transformed['location_id'] is None
        assert 'Austin' in transformed['display_name'] or '30.26715' in transformed['display_name']

    def test_transform_geographic_target_city(self):
        """Test transformation of city targets to geographic format"""
        old_data = {
            'id': 3,
            'channel_id': 12345,
            'target_type': 'city',  # Should become 'geographic'
            'target_name': '40.7128,-74.0060,10',
            'location_id': None,
            'poll_rate_minutes': 30,
            'notification_types': 'machines,submissions',
            'last_checked_at': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        # Transform to new format
        transformed = self.transform_target_data(old_data)
        
        # Verify transformation
        assert transformed['target_type'] == 'geographic'
        assert transformed['latitude'] == 40.7128
        assert transformed['longitude'] == -74.0060
        assert transformed['radius_miles'] == 10
        assert transformed['location_id'] is None

    def test_import_to_new_schema(self):
        """Test importing transformed data to new schema"""
        # Create transformed data
        transformed_targets = [
            {
                'channel_id': 12345,
                'target_type': 'location',
                'display_name': 'Test Arcade',
                'location_id': 123,
                'latitude': None,
                'longitude': None,
                'radius_miles': None,
                'poll_rate_minutes': 60,
                'notification_types': 'machines',
                'last_checked_at': None,
            },
            {
                'channel_id': 12345,
                'target_type': 'geographic',
                'display_name': 'Austin, TX Area',
                'location_id': None,
                'latitude': 30.26715,
                'longitude': -97.74306,
                'radius_miles': 5,
                'poll_rate_minutes': 45,
                'notification_types': 'submissions',
                'last_checked_at': None,
            }
        ]
        
        with self.NewSession() as session:
            # Create channel config first
            channel_config = NewChannelConfig(
                channel_id=12345,
                guild_id=67890,
                poll_rate_minutes=30,
                notification_types="machines,submissions"
            )
            session.add(channel_config)
            session.flush()
            
            # Import transformed targets
            for target_data in transformed_targets:
                target = NewMonitoringTarget(**target_data)
                session.add(target)
            
            session.commit()
            
            # Verify import
            imported_targets = session.query(NewMonitoringTarget).all()
            assert len(imported_targets) == 2
            
            # Verify location target
            location_target = next((t for t in imported_targets if t.target_type == 'location'), None)
            assert location_target is not None
            assert location_target.location_id == 123
            assert location_target.display_name == 'Test Arcade'
            
            # Verify geographic target
            geo_target = next((t for t in imported_targets if t.target_type == 'geographic'), None)
            assert geo_target is not None
            assert geo_target.latitude == 30.26715
            assert geo_target.longitude == -97.74306
            assert geo_target.radius_miles == 5

    def test_data_validation_constraints(self):
        """Test that new schema constraints work correctly"""
        with self.NewSession() as session:
            # Create channel config first
            channel_config = NewChannelConfig(
                channel_id=12345,
                guild_id=67890,
            )
            session.add(channel_config)
            session.flush()
            
            # Test valid location target
            valid_location = NewMonitoringTarget(
                channel_id=12345,
                target_type='location',
                display_name='Valid Location',
                location_id=123,
                poll_rate_minutes=60,
                notification_types='machines'
            )
            session.add(valid_location)
            
            # Test valid geographic target
            valid_geographic = NewMonitoringTarget(
                channel_id=12345,
                target_type='geographic',
                display_name='Valid Geographic',
                latitude=30.0,
                longitude=-97.0,
                radius_miles=10,
                poll_rate_minutes=45,
                notification_types='submissions'
            )
            session.add(valid_geographic)
            
            # Commit should succeed
            session.commit()
            
            # Verify targets were created
            targets = session.query(NewMonitoringTarget).all()
            assert len(targets) == 2

    def test_invalid_data_rejection(self):
        """Test that invalid data is properly rejected by constraints"""
        with self.NewSession() as session:
            # Create channel config first
            channel_config = NewChannelConfig(
                channel_id=12345,
                guild_id=67890,
            )
            session.add(channel_config)
            session.flush()
            
            # Test invalid latitude (should raise ValueError)
            with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
                invalid_target = NewMonitoringTarget(
                    channel_id=12345,
                    target_type='geographic',
                    display_name='Invalid Latitude',
                    latitude=100.0,  # Invalid: > 90
                    longitude=-97.0,
                    radius_miles=10,
                )
                session.add(invalid_target)
                session.commit()

    def test_end_to_end_transformation(self):
        """Test complete end-to-end transformation pipeline"""
        # 1. Create old data
        with self.OldSession() as old_session:
            self.create_sample_old_data(old_session)
            
            # 2. Export all targets
            exported_targets = []
            for target in old_session.query(OldMonitoringTarget).all():
                exported_data = {
                    'id': target.id,
                    'channel_id': target.channel_id,
                    'target_type': target.target_type,
                    'target_name': target.target_name,
                    'location_id': target.location_id,
                    'poll_rate_minutes': target.poll_rate_minutes,
                    'notification_types': target.notification_types,
                    'last_checked_at': target.last_checked_at,
                    'created_at': target.created_at,
                }
                exported_targets.append(exported_data)
        
        # 3. Transform data
        transformed_targets = []
        for old_data in exported_targets:
            transformed = self.transform_target_data(old_data)
            transformed_targets.append(transformed)
        
        # 4. Import to new schema
        with self.NewSession() as new_session:
            # Create channel config
            channel_config = NewChannelConfig(
                channel_id=12345,
                guild_id=67890,
                poll_rate_minutes=30,
                notification_types="machines,submissions"
            )
            new_session.add(channel_config)
            new_session.flush()
            
            # Import transformed targets
            for target_data in transformed_targets:
                target = NewMonitoringTarget(**target_data)
                new_session.add(target)
            
            new_session.commit()
            
            # 5. Verify completeness and correctness
            imported_targets = new_session.query(NewMonitoringTarget).all()
            assert len(imported_targets) == 3  # Same number as original
            
            # Verify each target type was transformed correctly
            location_targets = [t for t in imported_targets if t.target_type == 'location']
            geographic_targets = [t for t in imported_targets if t.target_type == 'geographic']
            
            assert len(location_targets) == 1
            assert len(geographic_targets) == 2
            
            # Verify no 'city' or 'latlong' targets remain
            assert all(t.target_type in ('location', 'geographic') for t in imported_targets)

    def transform_target_data(self, old_data):
        """
        Transform a single target from old to new schema format.
        This implements the transformation logic described in the plan.
        """
        base_transformed = {
            'channel_id': old_data['channel_id'],
            'poll_rate_minutes': old_data['poll_rate_minutes'],
            'notification_types': old_data['notification_types'],
            'last_checked_at': old_data['last_checked_at'],
        }
        
        # Handle location targets (unchanged)
        if old_data['target_type'] == 'location':
            return {
                **base_transformed,
                'target_type': 'location',
                'display_name': old_data['target_name'],
                'location_id': old_data['location_id'],
                'latitude': None,
                'longitude': None,
                'radius_miles': None,
            }
        
        # Handle geographic targets (latlong and city types)
        elif old_data['target_type'] in ('latlong', 'city'):
            # Parse coordinates from target_name: "lat,lon,radius"
            try:
                parts = old_data['target_name'].split(',')
                latitude = float(parts[0])
                longitude = float(parts[1])
                radius_miles = int(parts[2]) if len(parts) > 2 else 25
                
                # Generate display name (in real implementation, this might use reverse geocoding)
                display_name = f"Location at {latitude:.5f}, {longitude:.5f}"
                
                return {
                    **base_transformed,
                    'target_type': 'geographic',
                    'display_name': display_name,
                    'location_id': None,
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_miles': radius_miles,
                }
            except (ValueError, IndexError) as e:
                raise ValueError(f"Invalid coordinate format in target_name: {old_data['target_name']}") from e
        
        else:
            raise ValueError(f"Unknown target_type: {old_data['target_type']}")