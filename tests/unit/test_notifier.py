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

    @pytest.mark.parametrize(
        "filter_type, submissions, expected_count, expected_types",
        [
            pytest.param(
                "machines",
                [
                    {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
                    {"submission_type": "remove_machine", "machine_name": "Pinball 2"},
                    {"submission_type": "new_condition", "machine_name": "Pinball 3"},
                    {"submission_type": "other_type", "machine_name": "Pinball 4"},
                ],
                2,
                ["new_lmx", "remove_machine"],
                id="machines",
            ),
            pytest.param(
                "comments",
                [
                    {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
                    {"submission_type": "new_condition", "machine_name": "Pinball 2"},
                    {"submission_type": "other_type", "machine_name": "Pinball 3"},
                ],
                1,
                ["new_condition"],
                id="comments",
            ),
            pytest.param(
                "all",
                [
                    {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
                    {"submission_type": "new_condition", "machine_name": "Pinball 2"},
                    {"submission_type": "other_type", "machine_name": "Pinball 3"},
                ],
                3,
                ["new_lmx", "new_condition", "other_type"],
                id="all",
            ),
            pytest.param(
                "unknown_type",
                [
                    {"submission_type": "new_lmx", "machine_name": "Pinball 1"},
                    {"submission_type": "new_condition", "machine_name": "Pinball 2"},
                ],
                2,
                ["new_lmx", "new_condition"],
                id="unknown-falls-back-to-all",
            ),
        ],
    )
    def test_filter_submissions_by_type(
        self, notifier, filter_type, submissions, expected_count, expected_types
    ):
        """Test filtering submissions by various types"""
        result = notifier._filter_submissions_by_type(submissions, filter_type)

        assert len(result) == expected_count
        assert [s["submission_type"] for s in result] == expected_types

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

            mock_fetch.assert_called_once_with(location_id=123, use_min_date=False)
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

            mock_fetch.assert_called_once_with(45.5, -122.6, 25, use_min_date=False)
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

    @pytest.mark.parametrize(
        "submission, expected_strings, unexpected_strings",
        [
            pytest.param(
                {
                    "submission_type": "new_lmx",
                    "machine_name": "Test Machine",
                    "location_name": "Test Location",
                    "user_name": "Test User",
                },
                ["Test Machine", "Test Location", "Test User", "added"],
                [],
                id="new_lmx",
            ),
            pytest.param(
                {
                    "submission_type": "remove_machine",
                    "machine_name": "Test Machine",
                    "location_name": "Test Location",
                    "user_name": "Test User",
                },
                ["Test Machine", "Test Location", "Test User", "removed"],
                [],
                id="remove_machine",
            ),
            pytest.param(
                {
                    "submission_type": "new_condition",
                    "machine_name": "Test Machine",
                    "location_name": "Test Location",
                    "user_name": "Test User",
                    "comment": "Great condition!",
                },
                [
                    "Test Machine",
                    "Test Location",
                    "Test User",
                    "Great condition!",
                    "💬",
                ],
                [],
                id="new_condition_with_comment",
            ),
            pytest.param(
                {
                    "submission_type": "new_condition",
                    "machine_name": "Test Machine",
                    "location_name": "Test Location",
                    "user_name": "Test User",
                },
                ["Test Machine", "Test Location", "Test User"],
                ["💬"],
                id="new_condition_without_comment",
            ),
            pytest.param(
                {
                    "submission_type": "unknown_type",
                    "machine_name": "Test Machine",
                    "location_name": "Test Location",
                    "user_name": "Test User",
                },
                ["Test Machine", "Test Location", "Test User", "unknown_type"],
                [],
                id="unknown_type",
            ),
        ],
    )
    def test_format_submission(
        self, notifier, submission, expected_strings, unexpected_strings
    ):
        """Test formatting submissions of various types"""
        result = notifier.format_submission(submission)

        for expected in expected_strings:
            assert expected in result or expected.lower() in result.lower(), (
                f"Expected '{expected}' in '{result}'"
            )
        for unexpected in unexpected_strings:
            assert unexpected not in result, (
                f"Did not expect '{unexpected}' in '{result}'"
            )

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
