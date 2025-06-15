"""
Test PostgreSQL-specific functionality for Database module
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.database import Database


class TestDatabasePostgres:

    def setup_method(self):
        """Setup test environment"""
        # Save original environment
        self.original_env = dict(os.environ)

        # Set PostgreSQL environment variables
        os.environ.update({
            'DB_TYPE': 'postgres',
            'DB_INSTANCE_CONNECTION_NAME': 'test-instance',
            'DB_USER': 'test-user',
            'DB_PASS': 'test-pass',
            'DB_NAME': 'test-db'
        })

    def teardown_method(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('google.cloud.sql.connector.Connector')
    def test_postgres_engine_creation(self, mock_connector):
        """Test that PostgreSQL engine is created correctly"""
        # Mock the connector
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance

        # Create database instance
        db = Database()

        # Verify connector was called with correct parameters
        mock_connector_instance.connect.assert_called_once_with(
            'test-instance',
            'pg8000',
            user='test-user',
            password='test-pass',
            db='test-db'
        )

        db.close()

    @patch('google.cloud.sql.connector.Connector')
    def test_missing_environment_variables(self, mock_connector):
        """Test that missing environment variables raise appropriate error"""
        # Remove required environment variable
        del os.environ['DB_INSTANCE_CONNECTION_NAME']

        # Attempt to create database instance
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Database()

    @patch('google.cloud.sql.connector.Connector')
    def test_postgres_connection_error(self, mock_connector):
        """Test handling of PostgreSQL connection errors"""
        # Mock connector to raise an error
        mock_connector_instance = MagicMock()
        mock_connector_instance.connect.side_effect = Exception("Connection failed")
        mock_connector.return_value = mock_connector_instance

        # Attempt to create database instance
        with pytest.raises(Exception, match="Connection failed"):
            Database()

    @patch('google.cloud.sql.connector.Connector')
    def test_postgres_operations(self, mock_connector):
        """Test basic database operations with PostgreSQL"""
        # Mock the connector
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance

        # Create database instance
        db = Database()

        # Test channel config operations
        channel_id = 12345
        guild_id = 67890

        # Create channel config
        db.update_channel_config(channel_id, guild_id, is_active=True)
        config = db.get_channel_config(channel_id)
        assert config is not None
        assert config['is_active'] is True

        # Test monitoring target operations
        db.add_monitoring_target(channel_id, 'latlong', '30.0,97.0,10')
        targets = db.get_monitoring_targets(channel_id)
        assert len(targets) == 1
        assert targets[0]['target_type'] == 'latlong'

        # Test seen submissions
        db.mark_submissions_seen(channel_id, [1, 2, 3])
        seen = db.get_seen_submissions(channel_id)
        assert len(seen) == 3
        assert set(seen) == {1, 2, 3}

        db.close()
