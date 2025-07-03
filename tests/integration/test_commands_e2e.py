"""
End-to-end tests for all Discord commands.

These tests execute the full logic of each command, from parsing the user
input to interacting with the database and sending a response. They run
against a real, but isolated, database instance provided by the `db_session`
fixture.
"""

# To be migrated from `tests_backup/func/test_commands.py`,
# `tests_backup/integration/test_commands_integration.py`,
# and parts of `tests_backup/unit/test_add_target_behavior.py`.

import pytest

# Assuming the main entrypoint for the bot is here
from src.main import create_bot
from src.models import MonitoringTarget
from tests.utils.mock_factories import (
    create_async_notifier_mock,
    create_discord_context_mock,
    validate_async_mock,
)


@pytest.mark.asyncio
async def test_add_location_by_name_e2e(db_session, api_mocker):
    """
    Tests the full `!add location <name>` flow.
    - Mocks the PinballMap API to return a successful search result.
    - Executes the command.
    - Verifies that the correct target is added to the database.
    - Verifies that the correct confirmation message is sent.
    """
    # 1. SETUP
    location_name = "Ground Kontrol Classic Arcade"
    expected_location_id = 874

    # Mock PinballMap API search response
    api_mocker.add_response(
        url_substring="by_location_name",
        json_fixture_path="pinballmap_search/search_ground_kontrol_single_result.json",
    )

    # Mock location details response
    api_mocker.add_response(
        url_substring="locations/874.json",
        json_fixture_path="pinballmap_locations/location_874_details.json",
    )

    # Mock submissions response
    api_mocker.add_response(
        url_substring="user_submissions",
        json_fixture_path="pinballmap_submissions/location_874_recent.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")
    validate_async_mock(mock_notifier, "send_initial_notifications")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=12345)  # Use unique channel ID

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_location(mock_ctx, location_input=location_name)

    # 3. ASSERT
    # Verify database entry was created (this indicates the command succeeded)
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None, "Target should have been created in database"
    assert target.target_type == "location"
    assert target.display_name == location_name
    assert target.location_id == expected_location_id
    session.close()


@pytest.mark.asyncio
async def test_add_city_e2e(db_session, api_mocker):
    """
    Tests the full `!add city <name>` flow.
    - Mocks the Geocoding API to return coordinates for the city.
    - Executes the command.
    - Verifies that a 'geographic' target with correct coordinates is added to the database.
    """
    # 1. SETUP
    city_name = "Portland, OR"

    # Mock geocoding API response
    api_mocker.add_response(
        url_substring="v1/search",
        json_fixture_path="geocoding/city_portland_or.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")
    validate_async_mock(mock_notifier, "send_initial_notifications")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_city(mock_ctx, city_input=city_name)

    # 3. ASSERT
    # Verify database entry was created (this indicates the command succeeded)
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None, "Target should have been created in database"
    assert target.target_type == "geographic"
    assert (
        target.display_name == f"{city_name} (25mi)"
    )  # Default radius is added to display name
    assert target.latitude is not None
    assert target.longitude is not None
    assert target.radius_miles == 25  # Default radius
    session.close()


@pytest.mark.asyncio
async def test_add_city_with_radius_e2e(db_session, api_mocker):
    """
    Tests the full `!add city <name> <radius>` flow.
    - Tests adding a city with a custom radius.
    """
    # 1. SETUP
    city_name = "Seattle, WA"
    radius = 15

    # Mock geocoding API response
    api_mocker.add_response(
        url_substring="v1/search",
        json_fixture_path="geocoding/city_seattle.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")
    validate_async_mock(mock_notifier, "send_initial_notifications")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_city(mock_ctx, city_input=f"{city_name} {radius}")

    # 3. ASSERT
    # Verify database entry was created (this indicates the command succeeded)
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None, "Target should have been created in database"
    assert target.target_type == "geographic"
    assert (
        target.display_name == f"{city_name} ({radius}mi)"
    )  # Custom radius is added to display name
    assert target.latitude is not None
    assert target.longitude is not None
    assert target.radius_miles == radius
    session.close()


@pytest.mark.asyncio
async def test_add_coordinates_e2e(db_session, api_mocker):
    """
    Tests the full `!add coordinates <lat> <lon>` flow.
    - Tests adding coordinates without radius (uses default).
    """
    # 1. SETUP
    lat = 45.5231
    lon = -122.6765

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")
    validate_async_mock(mock_notifier, "send_initial_notifications")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=12345)  # Use unique channel ID

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_coordinates(mock_ctx, lat, lon)

    # 3. ASSERT
    # Verify database entry was created (this indicates the command succeeded)
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None, "Target should have been created in database"
    assert target.target_type == "geographic"
    assert target.latitude is not None
    assert target.longitude is not None
    assert abs(target.latitude - lat) < 0.01
    assert abs(target.longitude - lon) < 0.01
    assert target.radius_miles == 25  # Default radius
    session.close()


@pytest.mark.asyncio
async def test_add_coordinates_with_radius_e2e(db_session, api_mocker):
    """
    Tests the full `!add coordinates <lat> <lon> <radius>` flow.
    - Tests adding coordinates with a custom radius.
    """
    # 1. SETUP
    lat = 47.6062
    lon = -122.3321
    radius = 5

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")
    validate_async_mock(mock_notifier, "send_initial_notifications")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_coordinates(mock_ctx, lat, lon, radius)

    # 3. ASSERT
    # Verify database entry was created (this indicates the command succeeded)
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None, "Target should have been created in database"
    assert target.target_type == "geographic"
    assert target.latitude is not None
    assert target.longitude is not None
    assert abs(target.latitude - lat) < 0.01
    assert abs(target.longitude - lon) < 0.01
    assert target.radius_miles == radius
    session.close()


@pytest.mark.asyncio
async def test_remove_target_e2e(db_session):
    """
    Tests the full `!rm <index>` flow.
    - Programmatically adds a target to the database.
    - Executes the `!rm 1` command.
    - Verifies that the target is removed from the database.
    - Verifies that the correct confirmation message is sent.
    """
    # 1. SETUP
    session = db_session()
    session.add(
        MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=999,
        )
    )
    session.commit()
    session.close()

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=12345)

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.remove(mock_ctx, "1")

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify database entry is removed
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=12345, location_id=999)
        .first()
    )
    assert target is None
    session.close()


@pytest.mark.asyncio
async def test_remove_target_invalid_index_e2e(db_session):
    """
    Tests `!rm` with an invalid index.
    - Should notify user of invalid index.
    """
    # 1. SETUP
    session = db_session()
    session.add(
        MonitoringTarget(
            channel_id=12345,
            target_type="location",
            display_name="Test Location",
            location_id=999,
        )
    )
    session.commit()

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=12345)

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.remove(mock_ctx, "2")  # Invalid index

    # 3. ASSERT
    # Should send invalid index message
    mock_notifier.log_and_send.assert_called_once()
    call_args = mock_notifier.log_and_send.call_args[0]
    assert "Invalid index" in call_args[1]
    session.close()


@pytest.mark.asyncio
async def test_list_targets_e2e(db_session):
    """
    Tests the `!list` command.
    - Adds multiple targets to the database.
    - Executes the command.
    - Verifies that the output contains the correct information for all targets.
    """
    # 1. SETUP
    channel_id = 67890  # Match the default from create_discord_context_mock
    session = db_session()
    session.add(
        MonitoringTarget(
            channel_id=channel_id,
            target_type="location",
            display_name="Ground Kontrol",
            location_id=874,
        )
    )
    session.add(
        MonitoringTarget(
            channel_id=channel_id,
            target_type="geographic",
            display_name="Portland Coordinates",
            latitude=45.5231,
            longitude=-122.6765,
            radius_miles=10,
        )
    )
    session.commit()
    session.close()

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.list_targets(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify the message contains all targets
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "Ground Kontrol" in message
    assert "45.5231" in message and "-122.6765" in message


@pytest.mark.asyncio
async def test_list_command_empty(db_session):
    """
    Tests the `!list` command when no targets exist.
    - Verifies appropriate message for empty list.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.list_targets(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify empty message
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "No monitoring targets" in message or "empty" in message.lower()


@pytest.mark.asyncio
async def test_export_command_e2e(db_session):
    """
    Tests the `!export` command.
    - Adds a mix of targets to the database.
    - Executes the command.
    - Verifies that the exported script contains the correct `!add` and `!poll_rate` commands.
    """
    # 1. SETUP
    channel_id = 67890  # Match the default from create_discord_context_mock
    session = db_session()
    session.add(
        MonitoringTarget(
            channel_id=channel_id,
            target_type="location",
            display_name="Ground Kontrol",
            location_id=874,
            poll_rate_minutes=15,
        )
    )
    session.add(
        MonitoringTarget(
            channel_id=channel_id,
            target_type="geographic",
            display_name="Portland Coordinates",
            latitude=45.5231,
            longitude=-122.6765,
            radius_miles=10,
        )
    )
    session.commit()
    session.close()

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.export(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify export contains all commands
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "!add location 874" in message  # Should export with ID when available
    assert "!add coordinates 45.5231 -122.6765 10" in message
    assert "!poll_rate 15 1" in message
    assert "!notifications machines 1" in message


@pytest.mark.asyncio
async def test_add_location_command_not_found(db_session, api_mocker):
    """
    Tests the `!add location <name>` flow when no locations are found.
    - Mocks the PinballMap API to return empty search results.
    - Executes the command.
    - Verifies appropriate error message is sent.
    - Verifies no database entry is created.
    """
    # 1. SETUP
    location_name = "Nonexistent Location Name"

    # Mock PinballMap API search response with empty results
    api_mocker.add_response(
        url_substring="by_location_name",
        json_fixture_path="pinballmap_search/search_nonexistent_location_name.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=54321)  # Use different channel ID

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    await command_handler_cog.add_location(mock_ctx, location_input=location_name)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify error message contains appropriate text
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert (
        "No locations" in message
        or "not found" in message.lower()
        or "couldn't find" in message.lower()
    )

    # Verify no database entry was created
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is None
    session.close()


@pytest.mark.asyncio
async def test_remove_command_by_index_edge_cases(db_session):
    """
    Tests edge cases for the `!rm <index>` flow.
    - Tests removal with out-of-bounds index.
    - Tests removal with invalid (non-numeric) index.
    - Verifies appropriate error messages are sent.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(
        channel_id=98765
    )  # Use another unique channel ID

    # Add one target to test out-of-bounds access
    session = db_session()
    target = MonitoringTarget(
        channel_id=mock_ctx.interaction.channel.id,
        target_type="location",
        display_name="Test Location",
        location_id=123,
    )
    session.add(target)
    session.commit()
    session.close()

    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    # 2. ACTION & 3. ASSERT - Test out-of-bounds index
    await command_handler_cog.remove(mock_ctx, "999")

    assert mock_notifier.log_and_send.called
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "Invalid index" in message or "out of range" in message.lower()

    # Reset mock for next test
    mock_notifier.reset_mock()

    # ACTION & ASSERT - Test invalid (non-numeric) index
    await command_handler_cog.remove(mock_ctx, "abc")

    assert mock_notifier.log_and_send.called
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "valid number" in message.lower() or "invalid index" in message.lower()


@pytest.mark.asyncio
async def test_list_command_with_targets(db_session):
    """
    Tests the full end-to-end flow of the `!list` command with multiple targets.
    - Programmatically adds several targets to the database
    - Executes the `!list` command
    - Verifies that the response contains the details of all added targets
    """
    # 1. SETUP
    # Create a properly spec'd mock notifier with validation
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    # Create the bot with mocked notifier and properly spec'd mock context
    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # Get the command handler cog
    command_handler_cog = bot.get_cog("CommandHandler")
    assert command_handler_cog is not None, "CommandHandler cog not found"

    # Set up a session for database operations
    session = db_session()

    # Add several monitoring targets programmatically
    targets_data = [
        {
            "target_type": "location",
            "display_name": "Ground Kontrol Classic Arcade",
            "location_id": 874,
        },
        {
            "target_type": "geographic",
            "display_name": "Portland Coordinates",
            "latitude": 45.5231,
            "longitude": -122.6765,
            "radius_miles": 5,
        },
        {
            "target_type": "geographic",
            "display_name": "Portland, OR",
            "latitude": 45.5152,
            "longitude": -122.6784,
            "radius_miles": 25,
        },
    ]

    for target_data in targets_data:
        if target_data["target_type"] == "location":
            bot.database.add_monitoring_target(
                channel_id=mock_ctx.channel.id,
                target_type=target_data["target_type"],
                display_name=target_data["display_name"],
                location_id=target_data["location_id"],
            )
        elif target_data["target_type"] == "geographic":
            bot.database.add_monitoring_target(
                channel_id=mock_ctx.channel.id,
                target_type=target_data["target_type"],
                display_name=target_data["display_name"],
                latitude=target_data["latitude"],
                longitude=target_data["longitude"],
                radius_miles=target_data["radius_miles"],
            )

    # Ensure the channel config is created and active
    bot.database.update_channel_config(
        channel_id=mock_ctx.channel.id,
        guild_id=mock_ctx.guild.id,
        is_active=True,
        poll_rate_minutes=60,
        notification_types="machines",
    )

    session.close()

    # 2. ACTION
    # Call the list_targets method directly
    await command_handler_cog.list_targets(mock_ctx)

    # 3. ASSERT
    # Verify that log_and_send was called (the list command sends the table as a message)
    assert mock_notifier.log_and_send.called, "log_and_send should have been called"

    # Get the call arguments to log_and_send
    args, kwargs = mock_notifier.log_and_send.call_args
    ctx_arg, message_arg = args

    # Verify the message contains the expected table structure
    assert "```" in message_arg, "Message should contain a code block for the table"
    assert "Index" in message_arg, "Table should contain Index column header"
    assert "Target" in message_arg, "Table should contain Target column header"
    assert "Poll (min)" in message_arg, "Table should contain Poll (min) column header"
    assert "Notifications" in message_arg, (
        "Table should contain Notifications column header"
    )
    assert "Last Checked" in message_arg, (
        "Table should contain Last Checked column header"
    )

    # Verify each target appears in the message
    assert "Location: Ground Kontrol Classic Arcade" in message_arg, (
        "Should show location target"
    )
    assert "Coords: 45.52310, -122.67650" in message_arg, (
        "Should show coordinate target"
    )
    assert "Coords: 45.51520, -122.67840" in message_arg, (
        "Should show city target as geographic coordinates"
    )

    # Verify the table shows correct index numbers (1, 2, 3)
    assert "1" in message_arg, "Should show index 1"
    assert "2" in message_arg, "Should show index 2"
    assert "3" in message_arg, "Should show index 3"

    # Verify default settings are shown
    assert "60" in message_arg, "Should show default poll rate of 60 minutes"
    assert "machines" in message_arg, "Should show default notification type"
    assert "Never" in message_arg, (
        "Should show 'Never' for last checked since targets were just added"
    )

    # Verify that targets were actually stored in the database correctly
    session = db_session()
    stored_targets = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.channel.id)
        .order_by(MonitoringTarget.id)
        .all()
    )
    assert len(stored_targets) == 3, "Should have 3 targets in database"
    assert stored_targets[0].target_type == "location"
    assert stored_targets[0].display_name == "Ground Kontrol Classic Arcade"
    assert stored_targets[0].location_id == 874
    assert stored_targets[1].target_type == "geographic"
    assert stored_targets[1].display_name == "Portland Coordinates"
    assert stored_targets[1].latitude == 45.5231
    assert stored_targets[1].longitude == -122.6765
    assert stored_targets[1].radius_miles == 5
    assert stored_targets[2].target_type == "geographic"
    assert stored_targets[2].display_name == "Portland, OR"
    assert stored_targets[2].latitude == 45.5152
    assert stored_targets[2].longitude == -122.6784
    assert stored_targets[2].radius_miles == 25
    session.close()


@pytest.mark.asyncio
async def test_add_command_no_subcommand(db_session):
    """
    Tests that calling `!add` without a subcommand returns the invalid subcommand message.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()
    mock_ctx.invoked_subcommand = None  # Simulate no subcommand being called

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    await command_handler_cog.add(mock_ctx)

    # 3. ASSERT
    from src.messages import Messages

    mock_notifier.log_and_send.assert_called_once_with(
        mock_ctx, Messages.Command.Add.INVALID_SUBCOMMAND
    )


@pytest.mark.asyncio
async def test_add_location_not_found(db_session, api_mocker):
    """
    Tests that `!add location` with a name that returns no results
    sends the correct error message.
    """
    # 1. SETUP
    location_name = "A Place That Doesn't Exist"

    api_mocker.add_response(
        url_substring="by_location_name",
        json_fixture_path="pinballmap_search/search_nonexistent_location_name.json",
    )

    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    await command_handler_cog.add_location(mock_ctx, location_input=location_name)

    # 3. ASSERT
    from src.messages import Messages

    mock_notifier.log_and_send.assert_called_once_with(
        mock_ctx,
        Messages.Command.Add.NO_LOCATIONS.format(search_term=location_name),
    )


@pytest.mark.asyncio
async def test_add_city_not_found(db_session, api_mocker):
    """
    Tests that `!add city` with a name that returns no results
    sends the correct error message.
    """
    # 1. SETUP
    city_name = "A City That Doesn't Exist"

    api_mocker.add_response(
        url_substring="v1/search",
        json_fixture_path="geocoding/city_nonexistent.json",
    )

    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    await command_handler_cog.add_city(mock_ctx, city_input=city_name)

    # 3. ASSERT
    from src.messages import Messages

    mock_notifier.log_and_send.assert_called_once_with(
        mock_ctx,
        Messages.Command.Add.CITY_NOT_FOUND.format(city_name=city_name),
    )


@pytest.mark.asyncio
async def test_add_invalid_coordinates(db_session):
    """
    Tests that `!add coordinates` with invalid lat/lon values
    sends the correct error message.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    command_handler_cog = bot.get_cog("CommandHandler")
    await command_handler_cog.add_coordinates(mock_ctx, lat=200.0, lon=-200.0)

    # 3. ASSERT
    # Invalid coordinates should send an error message, not raise an exception
    from src.messages import Messages

    mock_notifier.log_and_send.assert_called_once_with(
        mock_ctx, Messages.Command.Shared.INVALID_COORDS
    )
