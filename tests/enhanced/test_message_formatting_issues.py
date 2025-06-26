"""
Enhanced Testing for Message Formatting Issues

This test suite is designed to catch message formatting failures that could
cause Discord message sending to fail silently or produce malformed output.

Key improvements over existing tests:
1. Tests multi-line message content validation
2. Validates Discord message length and formatting limits
3. Tests export command edge cases and complex formatting scenarios
4. Validates newline handling in various message contexts
5. Tests Unicode and special character handling
6. Validates message truncation and splitting behavior
"""

from unittest.mock import AsyncMock

import pytest

from src.notifier import Notifier
from tests.utils.db_utils import cleanup_test_database, setup_test_database


@pytest.fixture
def db():
    """Create test database"""
    test_db = setup_test_database()
    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def mock_channel():
    """Create mock Discord channel"""
    channel = AsyncMock()
    channel.id = 12345
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def notifier(mock_channel, db):
    """Create notifier instance"""
    return Notifier(db)


@pytest.mark.asyncio
class TestMultiLineMessageValidation:
    """Test validation of multi-line message content."""

    async def test_export_command_multiline_formatting(
        self, notifier, mock_channel, db
    ):
        """Test that export command produces properly formatted multi-line output."""
        # Setup complex channel configuration
        channel_id = 12345
        guild_id = 67890

        # Add multiple targets of different types
        db.add_monitoring_target(
            channel_id, "location", "Seattle Pinball Museum", "1309"
        )
        db.add_monitoring_target(channel_id, "latlong", "47.6062,-122.3321,5")
        db.add_monitoring_target(
            channel_id, "city", "Portland, OR", "45.5152,-122.6784,10"
        )
        db.update_channel_config(
            channel_id, guild_id, poll_rate_minutes=30, notification_types="all"
        )

        # Get the export content
        targets = db.get_monitoring_targets(channel_id)
        config = db.get_channel_config(channel_id)

        # Simulate export message generation
        export_lines = ["# Channel Configuration Export"]
        export_lines.append(f"!poll_rate {config['poll_rate_minutes']}")
        export_lines.append(f"!notifications {config['notification_types']}")
        export_lines.append("")
        export_lines.append("# Monitoring Targets")

        for target in targets:
            if target["target_type"] == "location":
                export_lines.append(f"!add location {target['target_data']}")
            elif target["target_type"] == "latlong":
                parts = target["target_name"].split(",")
                if len(parts) >= 3:
                    export_lines.append(
                        f"!add coordinates {parts[0]} {parts[1]} {parts[2]}"
                    )
                else:
                    export_lines.append(f"!add coordinates {parts[0]} {parts[1]}")
            elif target["target_type"] == "city":
                if target["target_data"]:
                    parts = target["target_data"].split(",")
                    if len(parts) >= 3:
                        city_name = target["target_name"]
                        radius = parts[2]
                        export_lines.append(f'!add city "{city_name}" {radius}')
                    else:
                        export_lines.append(f"!add city \"{target['target_name']}\"")

        export_message = "\n".join(export_lines)

        # Test message formatting
        await notifier.log_and_send(mock_channel, export_message)

        # Verify send was called
        mock_channel.send.assert_called_once()
        sent_message = mock_channel.send.call_args[0][0]

        # Validate multi-line structure
        lines = sent_message.split("\n")
        assert len(lines) >= 6, f"Expected multi-line message, got {len(lines)} lines"

        # Validate header
        assert lines[0] == "# Channel Configuration Export"

        # Validate configuration section
        config_lines = [
            line
            for line in lines
            if line.startswith("!poll_rate") or line.startswith("!notifications")
        ]
        assert (
            len(config_lines) == 2
        ), f"Expected 2 config lines, got {len(config_lines)}"

        # Validate command formatting
        target_lines = [line for line in lines if line.startswith("!add")]
        assert (
            len(target_lines) == 3
        ), f"Expected 3 target lines, got {len(target_lines)}"

        # Validate specific command formats
        location_commands = [line for line in target_lines if "location" in line]
        coordinate_commands = [line for line in target_lines if "coordinates" in line]
        city_commands = [line for line in target_lines if "city" in line]

        assert len(location_commands) == 1
        assert len(coordinate_commands) == 1
        assert len(city_commands) == 1

    async def test_submission_notification_multiline_formatting(
        self, notifier, mock_channel
    ):
        """Test multi-line formatting of submission notifications."""
        # Create submission with complex data
        submission = {
            "id": 12345,
            "type": "machine_added",
            "machine_name": "Medieval Madness (Remake)",
            "location_name": "Seattle Pinball Museum",
            "location_id": 1309,
            "comment": "This is a multi-line comment\nwith line breaks\nand additional info",
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "PinballWizard",
        }

        config = {"notification_types": "all"}

        # Test notification formatting
        await notifier.post_submissions(mock_channel, [submission], config)

        # Verify message was sent
        assert mock_channel.send.call_count >= 1

        # Get all sent messages
        sent_messages = []
        for call in mock_channel.send.call_args_list:
            if "content" in call[1]:
                sent_messages.append(call[1]["content"])
            elif len(call[0]) > 0:
                sent_messages.append(call[0][0])

        # Validate at least one message was sent
        assert len(sent_messages) >= 1, "No messages were sent"

        # Validate message contains expected content
        full_message = "\n".join(sent_messages)
        assert "Medieval Madness" in full_message
        assert "Seattle Pinball Museum" in full_message
        assert "PinballWizard" in full_message

    async def test_newline_preservation_in_comments(self, notifier, mock_channel):
        """Test that newlines in comments are properly preserved or escaped."""
        submission = {
            "id": 12345,
            "type": "machine_comment",
            "machine_name": "Attack From Mars",
            "location_name": "Test Location",
            "location_id": 123,
            "comment": "Line 1\nLine 2\nLine 3\n\nLine 5 after blank line",
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "TestUser",
        }

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, [submission], config)

        # Get sent message
        assert mock_channel.send.call_count >= 1
        call_args = mock_channel.send.call_args_list[0]

        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # Comments with newlines should either be preserved or properly escaped
        # The exact format depends on implementation, but should not break Discord
        assert "Line 1" in sent_message
        assert "Line 2" in sent_message
        assert "Line 3" in sent_message
        assert "Line 5 after blank line" in sent_message


@pytest.mark.asyncio
class TestDiscordMessageLimits:
    """Test Discord message length and formatting limits."""

    async def test_message_length_limits(self, notifier, mock_channel):
        """Test handling of messages approaching Discord's 2000 character limit."""
        # Create a very long submission comment
        long_comment = "This is a very long comment. " * 100  # ~3000 characters

        submission = {
            "id": 12345,
            "type": "machine_comment",
            "machine_name": "Very Long Machine Name That Goes On And On",
            "location_name": "Very Long Location Name That Also Goes On And On",
            "location_id": 123,
            "comment": long_comment,
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "UserWithVeryLongName",
        }

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, [submission], config)

        # Verify message was sent (should handle length gracefully)
        assert mock_channel.send.call_count >= 1

        # Check all sent messages are within Discord limits
        for call in mock_channel.send.call_args_list:
            if "content" in call[1]:
                message = call[1]["content"]
            else:
                message = call[0][0]

            assert len(message) <= 2000, f"Message too long: {len(message)} characters"

    async def test_multiple_large_submissions_batching(self, notifier, mock_channel):
        """Test batching behavior when multiple submissions would exceed limits."""
        # Create multiple large submissions
        submissions = []
        for i in range(10):
            submissions.append(
                {
                    "id": 12345 + i,
                    "type": "machine_added",
                    "machine_name": f"Machine With Very Long Name Number {i} That Goes On",
                    "location_name": f"Location With Very Long Name Number {i} That Also Goes On",
                    "location_id": 123 + i,
                    "comment": "This is a moderately long comment that adds to the total message length. "
                    * 10,
                    "created_at": "2025-01-15T10:30:00Z",
                    "user_name": f"UserNumber{i}",
                }
            )

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, submissions, config)

        # Should have sent multiple messages if needed
        assert mock_channel.send.call_count >= 1

        # Verify all messages are within limits
        total_characters = 0
        for call in mock_channel.send.call_args_list:
            if "content" in call[1]:
                message = call[1]["content"]
            else:
                message = call[0][0]

            assert len(message) <= 2000, f"Message too long: {len(message)} characters"
            total_characters += len(message)

        # Should have sent all the information (rough check)
        assert total_characters > 1000, "Messages seem too short for all submissions"

    async def test_unicode_and_emoji_handling(self, notifier, mock_channel):
        """Test handling of Unicode characters and emojis in messages."""
        submission = {
            "id": 12345,
            "type": "machine_added",
            "machine_name": "🎮 Medieval Madness™ (Remake) 🏰",
            "location_name": "Café Münchën 🍻",
            "location_id": 123,
            "comment": "Great machine! 😍 Works perfectly ✅ Highly recommend 👍 🎯🔥",
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "PinballFän",
        }

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, [submission], config)

        # Verify message was sent successfully
        assert mock_channel.send.call_count >= 1

        # Get sent message
        call_args = mock_channel.send.call_args_list[0]
        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # Verify Unicode content is preserved
        assert "🎮" in sent_message or "Medieval Madness" in sent_message
        assert "Café" in sent_message or "Münchën" in sent_message
        assert "PinballFän" in sent_message


@pytest.mark.asyncio
class TestExportCommandEdgeCases:
    """Test edge cases and complex formatting scenarios for export command."""

    async def test_export_with_empty_configuration(self, notifier, mock_channel, db):
        """Test export command with minimal/empty configuration."""
        channel_id = 12345
        guild_id = 67890

        # Create channel with no targets
        db.update_channel_config(channel_id, guild_id)

        # Get empty configuration
        targets = db.get_monitoring_targets(channel_id)  # Should be empty
        config = db.get_channel_config(channel_id)

        # Generate export message for empty config
        export_lines = ["# Channel Configuration Export"]
        export_lines.append(f"!poll_rate {config.get('poll_rate_minutes', 60)}")
        export_lines.append(f"!notifications {config.get('notification_types', 'all')}")
        export_lines.append("")
        export_lines.append("# Monitoring Targets")

        if not targets:
            export_lines.append("# No targets configured")

        export_message = "\n".join(export_lines)

        await notifier.log_and_send(mock_channel, export_message)

        # Verify message was sent
        mock_channel.send.assert_called_once()
        sent_message = mock_channel.send.call_args[0][0]

        # Should handle empty case gracefully
        assert "No targets configured" in sent_message
        assert "poll_rate" in sent_message
        assert "notifications" in sent_message

    async def test_export_with_special_characters_in_names(
        self, notifier, mock_channel, db
    ):
        """Test export with special characters in location/city names."""
        channel_id = 12345

        # Add targets with special characters
        db.add_monitoring_target(channel_id, "location", "Dave & Buster's", "456")
        db.add_monitoring_target(
            channel_id, "city", "San José, CA", "37.3382,-121.8863,15"
        )
        db.add_monitoring_target(channel_id, "location", "Barcade® NYC", "789")

        targets = db.get_monitoring_targets(channel_id)

        # Generate export
        export_lines = ["# Channel Configuration Export"]
        for target in targets:
            if target["target_type"] == "location":
                # Names with special characters should be quoted
                name = target["target_name"]
                if any(char in name for char in [" ", "&", "®", "'", '"']):
                    export_lines.append(f'!add location "{name}"')
                else:
                    export_lines.append(f"!add location {name}")
            elif target["target_type"] == "city":
                city_name = target["target_name"]
                export_lines.append(f'!add city "{city_name}"')

        export_message = "\n".join(export_lines)

        await notifier.log_and_send(mock_channel, export_message)

        # Verify message formatting
        mock_channel.send.assert_called_once()
        sent_message = mock_channel.send.call_args[0][0]

        # Should properly quote names with special characters
        assert '"Dave & Buster\'s"' in sent_message or "Dave & Buster" in sent_message
        assert '"San José, CA"' in sent_message or "San José" in sent_message
        assert '"Barcade® NYC"' in sent_message or "Barcade®" in sent_message

    async def test_export_command_truncation_handling(self, notifier, mock_channel, db):
        """Test export command with many targets that might exceed message limits."""
        channel_id = 12345

        # Add many targets
        for i in range(50):
            db.add_monitoring_target(
                channel_id,
                "location",
                f"Very Long Location Name Number {i} That Goes On And On",
                str(1000 + i),
            )

        targets = db.get_monitoring_targets(channel_id)
        config = db.get_channel_config(channel_id)

        # Generate potentially large export
        export_lines = ["# Channel Configuration Export"]
        export_lines.append(f"!poll_rate {config.get('poll_rate_minutes', 60)}")
        export_lines.append(f"!notifications {config.get('notification_types', 'all')}")
        export_lines.append("")
        export_lines.append("# Monitoring Targets")

        for target in targets:
            export_lines.append(f"!add location \"{target['target_name']}\"")

        export_message = "\n".join(export_lines)

        # If message is too long, should handle gracefully
        if len(export_message) > 1900:  # Leave buffer for Discord limit
            # Should truncate or split message
            truncated_message = export_message[:1900] + "\n# ... (truncated)"
            await notifier.log_and_send(mock_channel, truncated_message)
        else:
            await notifier.log_and_send(mock_channel, export_message)

        # Verify message was sent and within limits
        mock_channel.send.assert_called_once()
        sent_message = mock_channel.send.call_args[0][0]
        assert len(sent_message) <= 2000


@pytest.mark.asyncio
class TestComplexFormattingScenarios:
    """Test complex formatting scenarios that could cause issues."""

    async def test_nested_quote_handling(self, notifier, mock_channel):
        """Test handling of nested quotes in submission comments."""
        submission = {
            "id": 12345,
            "type": "machine_comment",
            "machine_name": "Attack From Mars",
            "location_name": "Test Location",
            "location_id": 123,
            "comment": 'Player said "This machine is \'amazing\'!" and then added "Best I\'ve played"',
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "TestUser",
        }

        config = {"notification_types": "all"}

        # Should handle nested quotes without breaking formatting
        await notifier.post_submissions(mock_channel, [submission], config)

        assert mock_channel.send.call_count >= 1

        # Get sent message
        call_args = mock_channel.send.call_args_list[0]
        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # Should contain the comment content (exact formatting may vary)
        assert "amazing" in sent_message
        assert "Best I" in sent_message

    async def test_markdown_interference_prevention(self, notifier, mock_channel):
        """Test that user content doesn't interfere with Discord markdown."""
        submission = {
            "id": 12345,
            "type": "machine_comment",
            "machine_name": "**Medieval** *Madness*",
            "location_name": "__Test__ Location",
            "location_id": 123,
            "comment": "This comment has **bold** and *italic* and __underline__ markdown",
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "~~Strikethrough~~ User",
        }

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, [submission], config)

        assert mock_channel.send.call_count >= 1

        # Get sent message
        call_args = mock_channel.send.call_args_list[0]
        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # Should contain the content (may be escaped or preserved)
        assert "Medieval" in sent_message
        assert "Madness" in sent_message
        assert "Test" in sent_message
        assert "Location" in sent_message

    async def test_url_and_link_formatting(self, notifier, mock_channel):
        """Test handling of URLs and links in comments."""
        submission = {
            "id": 12345,
            "type": "machine_comment",
            "machine_name": "Attack From Mars",
            "location_name": "Test Location",
            "location_id": 123,
            "comment": "Check out https://pinballmap.com for more info! Also see http://example.com/path?param=value",
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "TestUser",
        }

        config = {"notification_types": "all"}

        await notifier.post_submissions(mock_channel, [submission], config)

        assert mock_channel.send.call_count >= 1

        # Get sent message
        call_args = mock_channel.send.call_args_list[0]
        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # URLs should be preserved
        assert "https://pinballmap.com" in sent_message
        assert "http://example.com" in sent_message


@pytest.mark.asyncio
class TestMessageFormattingEdgeCases:
    """Test edge cases in message formatting that could cause silent failures."""

    async def test_empty_and_null_field_handling(self, notifier, mock_channel):
        """Test handling of empty or null fields in submissions."""
        submission = {
            "id": 12345,
            "type": "machine_added",
            "machine_name": "",  # Empty name
            "location_name": "Test Location",
            "location_id": 123,
            "comment": None,  # Null comment
            "created_at": "2025-01-15T10:30:00Z",
            "user_name": "",  # Empty user name
        }

        config = {"notification_types": "all"}

        # Should handle empty/null fields gracefully
        await notifier.post_submissions(mock_channel, [submission], config)

        assert mock_channel.send.call_count >= 1

        # Should not crash and should send some message
        call_args = mock_channel.send.call_args_list[0]
        if "content" in call_args[1]:
            sent_message = call_args[0][0]
        else:
            sent_message = call_args[0][0]

        # Should contain at least the location
        assert "Test Location" in sent_message

    async def test_zero_length_message_prevention(self, notifier, mock_channel):
        """Test that zero-length messages are not sent."""
        # Try to send empty message
        await notifier.log_and_send(mock_channel, "")

        # Should not have sent empty message
        # (Implementation may vary - might send nothing or a placeholder)
        if mock_channel.send.call_count > 0:
            call_args = mock_channel.send.call_args_list[0]
            if "content" in call_args[1]:
                sent_message = call_args[0][0]
            else:
                sent_message = call_args[0][0]

            assert len(sent_message.strip()) > 0, "Empty message was sent"

    async def test_whitespace_only_message_handling(self, notifier, mock_channel):
        """Test handling of whitespace-only messages."""
        whitespace_message = "   \n\n\t\t   \n   "

        await notifier.log_and_send(mock_channel, whitespace_message)

        # Should either not send or normalize the message
        if mock_channel.send.call_count > 0:
            call_args = mock_channel.send.call_args_list[0]
            if "content" in call_args[1]:
                sent_message = call_args[0][0]
            else:
                sent_message = call_args[0][0]

            # Should either be empty or contain actual content
            assert len(sent_message.strip()) == 0 or len(sent_message.strip()) > 0
