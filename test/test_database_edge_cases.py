"""
Test edge cases for Database module including session management, constraints, and error handling
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.database import Database
from src.models import ChannelConfig, MonitoringTarget, SeenSubmission


class TestDatabaseEdgeCases:
    
    def setup_method(self):
        """Setup test database with in-memory SQLite"""
        self.db = Database(":memory:")
    
    def teardown_method(self):
        """Clean up database"""
        self.db.close()
    
    def test_duplicate_target_addition(self):
        """Test that adding duplicate targets raises IntegrityError"""
        channel_id = 12345
        guild_id = 67890
        
        # Add first target
        self.db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
        
        # Adding the same target should raise an exception
        with pytest.raises(Exception, match="already being monitored"):
            self.db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
    
    def test_remove_nonexistent_target(self):
        """Test removing a target that doesn't exist"""
        channel_id = 12345
        
        with pytest.raises(Exception, match="not found"):
            self.db.remove_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
    
    def test_update_nonexistent_target_poll_rate(self):
        """Test updating poll rate for non-existent target"""
        result = self.db.update_monitoring_target_poll_rate(99999, 30)
        assert result is False
    
    def test_mark_duplicate_submissions_seen(self):
        """Test marking the same submission as seen multiple times"""
        channel_id = 12345
        guild_id = 67890
        submission_ids = [1, 2, 3]
        
        # Create channel config first
        self.db.update_channel_config(channel_id, guild_id)
        
        # Mark submissions as seen twice - should not raise errors
        self.db.mark_submissions_seen(channel_id, submission_ids)
        self.db.mark_submissions_seen(channel_id, submission_ids)
        
        # Should still only have 3 unique seen submissions
        seen_ids = self.db.get_seen_submissions(channel_id)
        assert len(seen_ids) == 3
        assert set(seen_ids) == {1, 2, 3}
    
    def test_empty_submission_ids_list(self):
        """Test marking empty list of submissions as seen"""
        channel_id = 12345
        
        # Should not raise any errors
        self.db.mark_submissions_seen(channel_id, [])
        
        seen_ids = self.db.get_seen_submissions(channel_id)
        assert seen_ids == []
    
    def test_filter_submissions_empty_list(self):
        """Test filtering empty list of submissions"""
        channel_id = 12345
        
        result = self.db.filter_new_submissions(channel_id, [])
        assert result == []
    
    def test_get_active_channels_no_targets(self):
        """Test getting active channels when no targets exist"""
        channel_id = 12345
        guild_id = 67890
        
        # Create active channel config but no targets
        self.db.update_channel_config(channel_id, guild_id, is_active=True)
        
        active_channels = self.db.get_active_channels()
        assert len(active_channels) == 0  # Should be filtered out due to no targets
    
    def test_get_monitoring_targets_empty_channel(self):
        """Test getting targets for channel with no targets"""
        channel_id = 12345
        
        targets = self.db.get_monitoring_targets(channel_id)
        assert targets == []
    
    def test_clear_monitoring_targets_empty_channel(self):
        """Test clearing targets for channel with no targets"""
        channel_id = 12345
        
        # Should not raise errors
        self.db.clear_monitoring_targets(channel_id)
    
    def test_clear_seen_submissions_empty_channel(self):
        """Test clearing seen submissions for channel with no submissions"""
        channel_id = 12345
        
        # Should not raise errors
        self.db.clear_seen_submissions(channel_id)
    
    def test_update_channel_monitoring_targets_poll_rate_no_targets(self):
        """Test updating poll rate for channel with no targets"""
        channel_id = 12345
        
        result = self.db.update_channel_monitoring_targets_poll_rate(channel_id, 30)
        assert result == 0  # No targets updated
    
    def test_channel_config_update_nonexistent(self):
        """Test updating non-existent channel config creates new one"""
        channel_id = 12345
        guild_id = 67890
        
        # Should create new config
        self.db.update_channel_config(channel_id, guild_id, is_active=True, poll_rate_minutes=45)
        
        config = self.db.get_channel_config(channel_id)
        assert config is not None
        assert config['is_active'] is True
        assert config['poll_rate_minutes'] == 45
    
    def test_channel_config_update_existing(self):
        """Test updating existing channel config"""
        channel_id = 12345
        guild_id = 67890
        
        # Create initial config
        self.db.update_channel_config(channel_id, guild_id, is_active=False, poll_rate_minutes=60)
        
        # Update existing config
        self.db.update_channel_config(channel_id, guild_id, is_active=True, notification_types='all')
        
        config = self.db.get_channel_config(channel_id)
        assert config['is_active'] is True
        assert config['notification_types'] == 'all'
        assert config['poll_rate_minutes'] == 60  # Should remain unchanged


class TestDatabaseSessionManagement:
    
    def setup_method(self):
        """Setup test database with in-memory SQLite"""
        self.db = Database(":memory:")
    
    def teardown_method(self):
        """Clean up database"""
        self.db.close()
    
    @patch('src.database.Database.get_session')
    def test_session_error_handling_add_target(self, mock_get_session):
        """Test that database errors in add_monitoring_target are handled properly"""
        mock_session = MagicMock()
        mock_session.commit.side_effect = IntegrityError("Constraint violation", None, None)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_get_session.return_value = mock_session
        
        with pytest.raises(Exception, match="already being monitored"):
            self.db.add_monitoring_target(12345, 'latlong', '30.0,97.0,10')
        
        mock_session.rollback.assert_called_once()
    
    @patch('src.database.Database.get_session')
    def test_session_error_handling_get_config(self, mock_get_session):
        """Test that database errors in get_channel_config return None"""
        mock_session = MagicMock()
        mock_session.get.side_effect = SQLAlchemyError("Database error")
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_get_session.return_value = mock_session
        
        # Should handle error gracefully and return None
        result = self.db.get_channel_config(12345)
        assert result is None
    
    def test_database_init_creates_tables(self):
        """Test that database initialization creates all required tables"""
        # Create a new database instance to test initialization
        test_db = Database(":memory:")
        
        # Test that we can create records in all tables
        channel_id = 12345
        guild_id = 67890
        
        # Create channel config
        test_db.update_channel_config(channel_id, guild_id)
        config = test_db.get_channel_config(channel_id)
        assert config is not None
        
        # Create monitoring target
        test_db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
        targets = test_db.get_monitoring_targets(channel_id)
        assert len(targets) == 1
        
        # Create seen submission
        test_db.mark_submissions_seen(channel_id, [1])
        seen = test_db.get_seen_submissions(channel_id)
        assert len(seen) == 1
        
        test_db.close()
    
    def test_database_close(self):
        """Test that database close disposes engine properly"""
        test_db = Database(":memory:")
        
        with patch.object(test_db.engine, 'dispose') as mock_dispose:
            test_db.close()
            mock_dispose.assert_called_once()


class TestDatabaseConstraints:
    
    def setup_method(self):
        """Setup test database with in-memory SQLite"""
        self.db = Database(":memory:")
    
    def teardown_method(self):
        """Clean up database"""
        self.db.close()
    
    def test_unique_channel_target_constraint(self):
        """Test that unique constraint on channel_id + target_type + target_name works"""
        channel_id = 12345
        
        # Add first target
        self.db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
        
        # Adding same target should fail
        with pytest.raises(Exception, match="already being monitored"):
            self.db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
        
        # Adding different target should succeed
        self.db.add_monitoring_target(channel_id, 'latlong', '31.0,98.0,15')
        
        targets = self.db.get_monitoring_targets(channel_id)
        assert len(targets) == 2
    
    def test_unique_channel_submission_constraint(self):
        """Test that unique constraint on channel_id + submission_id works"""
        channel_id = 12345
        guild_id = 67890
        
        # Create channel config first
        self.db.update_channel_config(channel_id, guild_id)
        
        # Mark submission as seen
        self.db.mark_submissions_seen(channel_id, [123])
        
        # Marking same submission again should not create duplicate
        self.db.mark_submissions_seen(channel_id, [123])
        
        seen_ids = self.db.get_seen_submissions(channel_id)
        assert len(seen_ids) == 1
        assert seen_ids[0] == 123
    
    def test_target_ordering_consistency(self):
        """Test that targets are returned in consistent order (by ID)"""
        channel_id = 12345
        
        # Add targets in specific order
        target_names = ['30.0,97.0,10', '31.0,98.0,15', '32.0,99.0,20']
        for target_name in target_names:
            self.db.add_monitoring_target(channel_id, 'latlong', target_name)
        
        # Get targets multiple times and verify order is consistent
        targets1 = self.db.get_monitoring_targets(channel_id)
        targets2 = self.db.get_monitoring_targets(channel_id)
        
        assert len(targets1) == 3
        assert len(targets2) == 3
        
        # Order should be consistent (by ID)
        for i in range(3):
            assert targets1[i]['target_name'] == targets2[i]['target_name']
            assert targets1[i]['id'] == targets2[i]['id']