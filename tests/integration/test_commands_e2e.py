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
    validate_async_mock(mock_notifier, "post_initial_submissions")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock(channel_id=12345)  # Use unique channel ID

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "location", location_name)

    # 3. ASSERT
    assert mock_notifier.post_initial_submissions.called

    # Verify database entry
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "location"
    assert target.target_name == location_name
    assert target.location_id == expected_location_id
    session.close()


@pytest.mark.asyncio
async def test_add_city_e2e(db_session, api_mocker):
    """
    Tests the full `!add city <name>` flow.
    - Mocks the Geocoding API to return coordinates for the city.
    - Executes the command.
    - Verifies that a 'city' target with correct coordinates is added to the database.
    """
    # 1. SETUP
    city_name = "Portland, OR"
    expected_lat = 45.5231
    expected_lon = -122.6765

    # Mock geocoding API response
    api_mocker.add_response(
        url_substring="geocode",
        json_fixture_path="geocoding/city_portland_or.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "city", city_name)

    # 3. ASSERT
    assert mock_notifier.post_initial_submissions.called

    # Verify database entry
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "city"
    assert target.target_name == city_name
    assert abs(target.latitude - expected_lat) < 0.01
    assert abs(target.longitude - expected_lon) < 0.01
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
    expected_lat = 47.6062
    expected_lon = -122.3321

    # Mock geocoding API response
    api_mocker.add_response(
        url_substring="geocode",
        json_fixture_path="geocoding/city_seattle.json",
    )

    # Create mock notifier and bot
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "city", city_name, str(radius))

    # 3. ASSERT
    assert mock_notifier.post_initial_submissions.called

    # Verify database entry
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "city"
    assert target.target_name == city_name
    assert target.radius_miles == radius
    assert abs(target.latitude - expected_lat) < 0.01
    assert abs(target.longitude - expected_lon) < 0.01
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

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "coordinates", str(lat), str(lon))

    # 3. ASSERT
    assert mock_notifier.post_initial_submissions.called

    # Verify database entry
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "coordinates"
    assert abs(target.latitude - lat) < 0.01
    assert abs(target.longitude - lon) < 0.01
    assert target.radius_miles == 100  # Default radius
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

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "coordinates", str(lat), str(lon), str(radius))

    # 3. ASSERT
    assert mock_notifier.post_initial_submissions.called

    # Verify database entry
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "coordinates"
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
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # Add a target to the database
    session = db_session()
    target = MonitoringTarget(
        channel_id=mock_ctx.interaction.channel.id,
        target_type="location",
        target_name="Test Location",
        location_id=123,
    )
    session.add(target)
    session.commit()
    target_id = target.id
    session.close()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.remove(mock_ctx, "1")

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify target was removed from database
    session = db_session()
    target = session.query(MonitoringTarget).filter_by(id=target_id).first()
    assert target is None
    session.close()


@pytest.mark.asyncio
async def test_remove_target_invalid_index_e2e(db_session):
    """
    Tests the `!rm <index>` flow with invalid index.
    - Verifies error handling for invalid index.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.remove(mock_ctx, "1")

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify error message was sent
    call_args = mock_notifier.log_and_send.call_args[0]
    assert "No targets found" in call_args[1] or "Invalid index" in call_args[1]


@pytest.mark.asyncio
async def test_list_targets_e2e(db_session):
    """
    Tests the full `!list` flow.
    - Programmatically adds several targets to the database.
    - Executes the `!list` command.
    - Verifies that the response message contains the details of all added targets.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # Add multiple targets to the database
    session = db_session()
    targets = [
        MonitoringTarget(
            channel_id=mock_ctx.interaction.channel.id,
            target_type="location",
            target_name="Funland",
            location_id=123,
            poll_rate_minutes=60,
        ),
        MonitoringTarget(
            channel_id=mock_ctx.interaction.channel.id,
            target_type="coordinates",
            target_name="Coords: 40.71, -74.00",
            latitude=40.71,
            longitude=-74.00,
            poll_rate_minutes=30,
        ),
        MonitoringTarget(
            channel_id=mock_ctx.interaction.channel.id,
            target_type="city",
            target_name="Austin, TX",
            latitude=30.2672,
            longitude=-97.7431,
        ),
    ]
    for target in targets:
        session.add(target)
    session.commit()
    session.close()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.list(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify the message contains all targets
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "Funland" in message
    assert "40.71, -74.00" in message
    assert "Austin, TX" in message
    assert "60" in message  # Poll rate
    assert "30" in message  # Poll rate


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
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.list(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify empty message
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "No monitoring targets" in message or "empty" in message.lower()


@pytest.mark.asyncio
async def test_export_command_e2e(db_session):
    """
    Tests the full `!export` flow.
    - Adds targets with various configurations to the database.
    - Executes the `!export` command.
    - Verifies that the exported configuration contains all the commands needed to recreate the setup.
    """
    # 1. SETUP
    mock_notifier = create_async_notifier_mock()
    validate_async_mock(mock_notifier, "log_and_send")

    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # Add targets with various configurations
    session = db_session()
    targets = [
        MonitoringTarget(
            channel_id=mock_ctx.interaction.channel.id,
            target_type="location",
            target_name="Ground Kontrol Classic Arcade",
            location_id=874,
            poll_rate_minutes=15,
            notification_types="machines",
        ),
        MonitoringTarget(
            channel_id=mock_ctx.interaction.channel.id,
            target_type="city",
            target_name="Portland, OR",
            latitude=45.5231,
            longitude=-122.6765,
            radius_miles=10,
        ),
    ]
    for target in targets:
        session.add(target)
    session.commit()
    session.close()

    # 2. ACTION
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.export(mock_ctx)

    # 3. ASSERT
    assert mock_notifier.log_and_send.called

    # Verify export contains all commands
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "!add location" in message
    assert "Ground Kontrol Classic Arcade" in message
    assert "!add city" in message
    assert "Portland, OR" in message
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
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    await monitoring_cog.add(mock_ctx, "location", location_name)

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
        target_name="Test Location",
        location_id=123,
    )
    session.add(target)
    session.commit()
    session.close()

    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    # 2. ACTION & 3. ASSERT - Test out-of-bounds index
    await monitoring_cog.remove(mock_ctx, "999")

    assert mock_notifier.log_and_send.called
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "Invalid index" in message or "out of range" in message.lower()

    # Reset mock for next test
    mock_notifier.reset_mock()

    # ACTION & ASSERT - Test invalid (non-numeric) index
    await monitoring_cog.remove(mock_ctx, "abc")

    assert mock_notifier.log_and_send.called
    call_args = mock_notifier.log_and_send.call_args[0]
    message = call_args[1]
    assert "valid number" in message.lower() or "invalid index" in message.lower()


# Note: This test function is duplicated - removing this stub as test_list_command_empty is already implemented above


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

    # Get the monitoring cog
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    # Set up a session for database operations
    session = db_session()

    # Add several monitoring targets programmatically
    targets_data = [
        {
            "target_type": "location",
            "target_name": "Ground Kontrol Classic Arcade",
            "location_id": 874,
        },
        {
            "target_type": "latlong",
            "target_name": "45.5231,-122.6765,5",
            "location_id": None,
        },
        {
            "target_type": "city",
            "target_name": "Portland, OR",
            "location_id": None,
        },
    ]

    for target_data in targets_data:
        bot.database.add_monitoring_target(
            channel_id=mock_ctx.channel.id,
            target_type=target_data["target_type"],
            target_name=target_data["target_name"],
            target_data=(
                str(target_data["location_id"]) if target_data["location_id"] else None
            ),
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
    await monitoring_cog.list_targets(mock_ctx)

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
    assert (
        "Notifications" in message_arg
    ), "Table should contain Notifications column header"
    assert (
        "Last Checked" in message_arg
    ), "Table should contain Last Checked column header"

    # Verify each target appears in the message
    assert (
        "Location: Ground Kontrol Classic Arcade" in message_arg
    ), "Should show location target"
    assert "Coords: 45.5231, -122.6765" in message_arg, "Should show coordinate target"
    assert "City: Portland, OR" in message_arg, "Should show city target"

    # Verify the table shows correct index numbers (1, 2, 3)
    assert "1" in message_arg, "Should show index 1"
    assert "2" in message_arg, "Should show index 2"
    assert "3" in message_arg, "Should show index 3"

    # Verify default settings are shown
    assert "60" in message_arg, "Should show default poll rate of 60 minutes"
    assert "machines" in message_arg, "Should show default notification type"
    assert (
        "Never" in message_arg
    ), "Should show 'Never' for last checked since targets were just added"

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
    assert stored_targets[0].target_name == "Ground Kontrol Classic Arcade"
    assert stored_targets[0].location_id == 874
    assert stored_targets[1].target_type == "latlong"
    assert stored_targets[1].target_name == "45.5231,-122.6765,5"
    assert stored_targets[2].target_type == "city"
    assert stored_targets[2].target_name == "Portland, OR"
    session.close()
