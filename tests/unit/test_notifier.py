"""
Tests for notifier module
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.database import Database
from src.notifier import Notifier


class TestNotifier:
    """Test the Notifier class"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        return Mock(spec=Database)

    @pytest.fixture
    def notifier(self, mock_db):
        """Create a Notifier instance with mock database"""
        return Notifier(mock_db)

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Discord context"""
        ctx = Mock()
        ctx.send = AsyncMock()
        ctx.author.name = "TestUser"
        ctx.author.id = 123456
        ctx.channel.name = "test-channel"
        ctx.channel.id = 789012
        return ctx

    @pytest.mark.asyncio
    async def test_log_and_send(self, notifier, mock_ctx):
        """Test log_and_send method"""
        message = "Test message"

        await notifier.log_and_send(mock_ctx, message)

        mock_ctx.send.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_log_and_send_without_author_channel(self, notifier):
        """Test log_and_send with context that doesn't have author/channel attributes"""
        ctx = Mock()
        ctx.send = AsyncMock()
        message = "Test message"

        await notifier.log_and_send(ctx, message)

        ctx.send.assert_called_once_with(message)

    def test_filter_submissions_by_type_machines(self, notifier):
        """Test filtering submissions for machines type"""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "remove_machine", "machine_name": "Pinball 2"},
            {"submission_type": "new_condition", "machine_name": "Pinball 3"},
            {"submission_type": "other_type", "machine_name": "Pinball 4"},
        ]

        result = notifier._filter_submissions_by_type(submissions, "machines")

        assert len(result) == 2
        assert result[0]["submission_type"] == "new_lmx"
        assert result[1]["submission_type"] == "remove_machine"

    def test_filter_submissions_by_type_comments(self, notifier):
        """Test filtering submissions for comments type"""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "new_condition", "machine_name": "Pinball 2"},
            {"submission_type": "other_type", "machine_name": "Pinball 3"},
        ]

        result = notifier._filter_submissions_by_type(submissions, "comments")

        assert len(result) == 1
        assert result[0]["submission_type"] == "new_condition"

    def test_filter_submissions_by_type_all(self, notifier):
        """Test filtering submissions for all type"""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "new_condition", "machine_name": "Pinball 2"},
            {"submission_type": "other_type", "machine_name": "Pinball 3"},
        ]

        result = notifier._filter_submissions_by_type(submissions, "all")

        assert len(result) == 3
        assert result == submissions

    def test_filter_submissions_by_type_unknown(self, notifier):
        """Test filtering submissions for unknown type"""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "new_condition", "machine_name": "Pinball 2"},
        ]

        result = notifier._filter_submissions_by_type(submissions, "unknown_type")

        assert len(result) == 2
        assert result == submissions

    @pytest.mark.asyncio
    @patch("src.notifier.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_send_initial_notifications_location_with_submissions(
        self, mock_fetch, notifier, mock_ctx, mock_db
    ):
        """Test send_initial_notifications for a location with submissions."""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "new_condition", "machine_name": "Pinball 2"},
        ]
        mock_fetch.return_value = submissions
        mock_db.get_channel_config.return_value = {"notification_types": "all"}

        with patch.object(
            notifier, "post_submissions", new_callable=AsyncMock
        ) as mock_post:
            await notifier.send_initial_notifications(
                ctx=mock_ctx,
                display_name="Test Location",
                location_id=123,
                target_type="location",
            )

            mock_fetch.assert_called_once_with(location_id=123)
            mock_post.assert_called_once()
            # Verify that the correct message was sent
            mock_ctx.send.assert_any_call(
                "✅ Found 2 recent submission(s) for **Test Location**:"
            )

    @pytest.mark.asyncio
    @patch("src.notifier.fetch_submissions_for_coordinates", new_callable=AsyncMock)
    async def test_send_initial_notifications_city_no_submissions(
        self, mock_fetch, notifier, mock_ctx, mock_db
    ):
        """Test send_initial_notifications for a city with no submissions."""
        mock_fetch.return_value = []
        mock_db.get_channel_config.return_value = {"notification_types": "all"}

        with patch.object(
            notifier, "post_submissions", new_callable=AsyncMock
        ) as mock_post:
            await notifier.send_initial_notifications(
                ctx=mock_ctx,
                display_name="Test City",
                latitude=45.5,
                longitude=-122.6,
                radius_miles=25,
                target_type="geographic",
            )

            mock_fetch.assert_called_once_with(45.5, -122.6, 25)
            mock_post.assert_not_called()
            mock_ctx.send.assert_called_once_with(
                "ℹ️ No recent submissions found for **Test City**."
            )

    @pytest.mark.asyncio
    @patch("src.notifier.fetch_submissions_for_location", new_callable=AsyncMock)
    async def test_send_initial_notifications_filtered(
        self, mock_fetch, notifier, mock_ctx, mock_db
    ):
        """Test send_initial_notifications with filtered submissions."""
        submissions = [
            {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
            {"submission_type": "new_condition", "machine_name": "Pinball 2"},
        ]
        mock_fetch.return_value = submissions
        mock_db.get_channel_config.return_value = {"notification_types": "machines"}

        with patch.object(
            notifier, "post_submissions", new_callable=AsyncMock
        ) as mock_post:
            await notifier.send_initial_notifications(
                ctx=mock_ctx,
                display_name="Test Location",
                location_id=123,
                target_type="location",
            )

            mock_post.assert_called_once()
            call_args, _ = mock_post.call_args
            assert len(call_args[1]) == 1
            assert call_args[1][0]["submission_type"] == "new_lmx"

    def test_format_submission_new_lmx(self, notifier):
        """Test formatting new_lmx submission"""
        submission = {
            "submission_type": "new_lmx",
            "machine_name": "Test Machine",
            "location_name": "Test Location",
            "user_name": "Test User",
        }

        result = notifier.format_submission(submission)

        assert "Test Machine" in result
        assert "Test Location" in result
        assert "Test User" in result
        assert "added" in result.lower()

    def test_format_submission_remove_machine(self, notifier):
        """Test formatting remove_machine submission"""
        submission = {
            "submission_type": "remove_machine",
            "machine_name": "Test Machine",
            "location_name": "Test Location",
            "user_name": "Test User",
        }

        result = notifier.format_submission(submission)

        assert "Test Machine" in result
        assert "Test Location" in result
        assert "Test User" in result
        assert "removed" in result.lower()

    def test_format_submission_new_condition_with_comment(self, notifier):
        """Test formatting new_condition submission with comment"""
        submission = {
            "submission_type": "new_condition",
            "machine_name": "Test Machine",
            "location_name": "Test Location",
            "user_name": "Test User",
            "comment": "Great condition!",
        }

        result = notifier.format_submission(submission)

        assert "Test Machine" in result
        assert "Test Location" in result
        assert "Test User" in result
        assert "Great condition!" in result
        assert "💬" in result

    def test_format_submission_new_condition_without_comment(self, notifier):
        """Test formatting new_condition submission without comment"""
        submission = {
            "submission_type": "new_condition",
            "machine_name": "Test Machine",
            "location_name": "Test Location",
            "user_name": "Test User",
        }

        result = notifier.format_submission(submission)

        assert "Test Machine" in result
        assert "Test Location" in result
        assert "Test User" in result
        assert "💬" not in result

    def test_format_submission_unknown_type(self, notifier):
        """Test formatting submission with unknown type"""
        submission = {
            "submission_type": "unknown_type",
            "machine_name": "Test Machine",
            "location_name": "Test Location",
            "user_name": "Test User",
        }

        result = notifier.format_submission(submission)

        assert "Test Machine" in result
        assert "Test Location" in result
        assert "Test User" in result
        assert "unknown_type" in result

    def test_format_submission_missing_fields(self, notifier):
        """Test formatting submission with missing fields"""
        submission = {
            "submission_type": "new_lmx"
            # Missing machine_name, location_name, user_name
        }

        result = notifier.format_submission(submission)

        assert "Unknown Machine" in result
        assert "Unknown Location" in result
        assert "Anonymous" in result
