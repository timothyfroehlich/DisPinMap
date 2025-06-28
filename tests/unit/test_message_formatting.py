"""
Unit tests for message formatting functions.

These tests ensure that all message formatting functions produce the expected
output for various input scenarios.
"""

from src.messages import Messages


def test_format_submission_notification_machine_added():
    """Test formatting a machine added notification"""
    machine_name = "The Addams Family"
    location_name = "Ground Kontrol"
    user_name = "testuser"

    result = Messages.Notification.Machine.ADDED.format(
        machine_name=machine_name, location_name=location_name, user_name=user_name
    )

    assert machine_name in result
    assert location_name in result
    assert user_name in result
    assert "added" in result.lower()


def test_format_submission_notification_with_comment():
    """Test formatting a submission notification with a comment"""
    machine_name = "The Addams Family"
    location_name = "Ground Kontrol"
    user_name = "testuser"
    comment = "Great condition!"

    result = Messages.Notification.Condition.UPDATED.format(
        machine_name=machine_name,
        location_name=location_name,
        comment_text=f"\n💬 {comment}",
        user_name=user_name,
    )

    assert machine_name in result
    assert location_name in result
    assert user_name in result
    assert comment in result
    assert "💬" in result


def test_format_list_targets_message():
    """Test formatting the list targets message"""
    targets = [
        {
            "index": 1,
            "target_type": "location",
            "target_name": "Funland",
            "poll_rate_minutes": 60,
            "notification_types": "machines",
            "last_checked": "5 minutes ago",
        },
        {
            "index": 2,
            "target_type": "coordinates",
            "target_name": "Coords: 40.71, -74.00",
            "poll_rate_minutes": 30,
            "notification_types": "all",
            "last_checked": "2 hours ago",
        },
    ]

    # Test with targets
    result = Messages.Command.List.TARGETS.format(targets=targets)
    assert "Funland" in result
    assert "40.71, -74.00" in result
    assert "60" in result
    assert "30" in result

    # Test empty list
    empty_result = Messages.Command.List.EMPTY
    assert (
        "no monitoring targets" in empty_result.lower()
        or "empty" in empty_result.lower()
    )


def test_message_truncation_for_long_content():
    """Test that long content is properly truncated"""
    long_machine_name = "A" * 1000
    long_location_name = "B" * 1000
    long_user_name = "C" * 1000

    result = Messages.Notification.Machine.ADDED.format(
        machine_name=long_machine_name,
        location_name=long_location_name,
        user_name=long_user_name,
    )

    # Should not exceed Discord's message limit (2000 characters)
    assert len(result) <= 2000


def test_handle_empty_or_null_fields():
    """Test handling of empty or null fields"""
    result = Messages.Notification.Machine.ADDED.format(
        machine_name="", location_name=None, user_name="testuser"
    )

    # Should handle empty/null gracefully
    assert "testuser" in result
    # Should not crash with empty/null values


def test_format_export_message():
    """Test formatting the export command message"""
    # Test export with channel defaults
    channel_config = {"poll_rate_minutes": 30, "notification_types": "all"}

    targets = [
        {
            "index": 1,
            "target_type": "location",
            "target_name": "Ground Kontrol Classic Arcade",
            "location_id": 874,
            "poll_rate_minutes": 15,
            "notification_types": "machines",
        },
        {
            "index": 2,
            "target_type": "city",
            "target_name": "Portland, OR",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "radius_miles": 10,
        },
    ]

    # Test export message formatting
    result = Messages.Command.Export.CONFIGURATION.format(
        channel_config=channel_config, targets=targets
    )

    # Should contain channel defaults
    assert "!poll_rate 30" in result
    assert "!notifications all" in result

    # Should contain target commands
    assert "!add location" in result
    assert "Ground Kontrol Classic Arcade" in result
    assert "!add city" in result
    assert "Portland, OR" in result

    # Should contain per-target overrides
    assert "!poll_rate 15 1" in result
    assert "!notifications machines 1" in result


def test_format_export_message_no_targets():
    """Test export message when no targets exist"""
    channel_config = {"poll_rate_minutes": 60, "notification_types": "machines"}

    result = Messages.Command.Export.CONFIGURATION.format(
        channel_config=channel_config, targets=[]
    )

    # Should contain only channel defaults
    assert "!poll_rate 60" in result
    assert "!notifications machines" in result

    # Should not contain any target commands
    assert "!add" not in result


def test_format_export_message_no_channel_config():
    """Test export message when no channel config exists"""
    result = Messages.Command.Export.CONFIGURATION.format(
        channel_config=None, targets=[]
    )

    # Should handle None channel config gracefully
    assert "configuration" in result.lower()


def test_format_remove_confirmation():
    """Test formatting remove target confirmation message"""
    target_name = "Ground Kontrol Classic Arcade"
    target_type = "location"

    result = Messages.Command.Remove.SUCCESS.format(
        target_name=target_name, target_type=target_type
    )

    assert target_name in result
    assert target_type in result
    assert "removed" in result.lower()


def test_format_remove_invalid_index():
    """Test formatting remove target invalid index message"""
    max_index = 3

    result = Messages.Command.Remove.INVALID_INDEX.format(max_index=max_index)

    assert str(max_index) in result
    assert "invalid" in result.lower() or "index" in result.lower()


def test_format_remove_no_targets():
    """Test formatting remove target when no targets exist"""
    result = Messages.Command.Remove.NO_TARGETS

    assert "no targets" in result.lower() or "empty" in result.lower()


def test_format_check_command_results():
    """Test formatting check command results"""
    new_submissions = [
        {
            "submission_type": "new_lmx",
            "machine_name": "The Addams Family",
            "location_name": "Ground Kontrol",
            "user_name": "testuser",
        }
    ]

    result = Messages.Command.Check.RESULTS.format(
        new_count=len(new_submissions), submissions=new_submissions
    )

    assert "The Addams Family" in result
    assert "Ground Kontrol" in result
    assert "testuser" in result
    assert "1" in result  # new_count


def test_format_check_no_new_submissions():
    """Test formatting check command when no new submissions"""
    result = Messages.Command.Check.NO_NEW

    assert "no new" in result.lower() or "up to date" in result.lower()


def test_format_add_success():
    """Test formatting add command success message"""
    target_type = "location"
    target_name = "Ground Kontrol Classic Arcade"
    target_id = 874

    result = Messages.Command.Add.SUCCESS.format(
        target_type=target_type, target_name=target_name, target_id=target_id
    )

    assert target_type in result
    assert target_name in result
    assert str(target_id) in result
    assert "added" in result.lower()


def test_format_add_not_found():
    """Test formatting add command not found message"""
    target_type = "location"
    target_name = "Nonexistent Location"

    result = Messages.Command.Add.NOT_FOUND.format(
        target_type=target_type, target_name=target_name
    )

    assert target_type in result
    assert target_name in result
    assert "not found" in result.lower() or "could not find" in result.lower()


def test_format_add_multiple_results():
    """Test formatting add command when multiple results found"""
    target_type = "location"
    target_name = "Dave and Busters"
    results = [
        {"name": "Dave & Buster's - Portland", "id": 123},
        {"name": "Dave & Buster's - Seattle", "id": 456},
    ]

    result = Messages.Command.Add.MULTIPLE_RESULTS.format(
        target_type=target_type, target_name=target_name, results=results
    )

    assert target_type in result
    assert target_name in result
    assert "multiple" in result.lower() or "several" in result.lower()
    assert "Portland" in result
    assert "Seattle" in result
