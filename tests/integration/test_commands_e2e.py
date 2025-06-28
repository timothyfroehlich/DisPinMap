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


def test_add_location_by_name_e2e(db_session, api_mocker):
    """
    Tests the full `!add location <name>` flow.
    - Mocks the PinballMap API to return a successful search result.
    - Executes the command.
    - Verifies that the correct target is added to the database.
    - Verifies that the correct confirmation message is sent.
    """
    pass


def test_add_city_e2e(db_session, api_mocker):
    """
    Tests the full `!add city <name>` flow.
    - Mocks the Geocoding API.
    - Executes the command.
    - Verifies that a 'city' target with correct coordinates is added to the database.
    """
    pass


def test_remove_target_e2e(db_session):
    """
    Tests the full `!rm <index>` flow.
    - Programmatically adds a target to the database.
    - Executes the `!rm 1` command.
    - Verifies that the target is removed from the database.
    - Verifies that the correct confirmation message is sent.
    """
    pass


def test_list_targets_e2e(db_session):
    """
    Tests the full `!list` flow.
    - Programmatically adds several targets to the database.
    - Executes the `!list` command.
    - Verifies that the response message contains the details of all added targets.
    """
    pass


def test_check_command_e2e(db_session, api_mocker):
    """
    Tests the full `!check` manual polling flow.
    - Adds a target to the database.
    - Mocks the PinballMap API to return new submissions.
    - Executes the `!check` command.
    - Verifies that a notification message with the new submissions is generated.
    """
    pass


@pytest.mark.asyncio
async def test_add_location_command_success(db_session, api_mocker):
    """
    Tests the full end-to-end flow of the `!add location` command
    for a successful case where a single location is found.
    """
    # 1. SETUP
    # Configure the API mocker for the location search and subsequent calls
    search_term = "Ground Kontrol Classic Arcade"
    location_id = 874
    api_mocker.add_response(
        url_substring="by_location_name=Ground%20Kontrol%20Classic%20Arcade",
        json_fixture_path="pinballmap_search/search_ground_kontrol_single_result.json",
    )
    api_mocker.add_response(
        url_substring=f"locations/{location_id}.json",
        json_fixture_path="pinballmap_locations/location_874_details.json",
    )
    api_mocker.add_response(
        url_substring=f"user_submissions/location.json?id={location_id}",
        json_fixture_path="pinballmap_submissions/location_874_empty.json",
    )

    # Create a properly spec'd mock notifier with validation
    mock_notifier = create_async_notifier_mock()

    # Validate the mock is properly set up for async usage
    validate_async_mock(mock_notifier, "log_and_send")

    # Create the bot with mocked notifier and properly spec'd mock context
    bot = await create_bot(db_session, notifier=mock_notifier)
    mock_ctx = create_discord_context_mock()

    # Debug: Verify our spec'd mocks are properly assigned
    print(f"DEBUG: bot.notifier type: {type(bot.notifier)}")
    print(
        f"DEBUG: bot.notifier spec: {getattr(bot.notifier, '_spec_class', 'No spec')}"
    )

    # Check the monitoring cog's notifier
    monitoring_cog = bot.get_cog("Monitoring")
    if monitoring_cog:
        print(f"DEBUG: monitoring_cog.notifier type: {type(monitoring_cog.notifier)}")
        print(
            f"DEBUG: monitoring_cog.notifier spec: {getattr(monitoring_cog.notifier, '_spec_class', 'No spec')}"
        )
    else:
        print("DEBUG: No Monitoring cog found")

    # 2. ACTION
    # Get the monitoring cog and call the add method directly with proper context
    monitoring_cog = bot.get_cog("Monitoring")
    assert monitoring_cog is not None, "Monitoring cog not found"

    # Call the add method with the cog instance as self
    await monitoring_cog.add(mock_ctx, "location", search_term)

    # 3. ASSERT
    # Verify that post_initial_submissions was called (which is the correct call for this flow)
    assert (
        mock_notifier.post_initial_submissions.called
    ), "post_initial_submissions should have been called"

    # Get the call arguments to post_initial_submissions
    args, kwargs = mock_notifier.post_initial_submissions.call_args
    ctx_arg, submissions_arg, target_type_arg = args

    # Verify the arguments match expected pattern
    assert submissions_arg == [], "Should be empty submissions list"
    assert "location **Ground Kontrol Classic Arcade** (ID: 874)" in target_type_arg

    # Assert that the target was saved to the database correctly
    session = db_session()
    target = (
        session.query(MonitoringTarget)
        .filter_by(channel_id=mock_ctx.interaction.channel.id)
        .first()
    )
    assert target is not None
    assert target.target_type == "location"
    assert target.target_name == "Ground Kontrol Classic Arcade"
    assert target.location_id == location_id
    session.close()


def test_add_location_command_not_found(db_session, api_mocker):
    pass


def test_remove_command_by_index(db_session):
    pass


def test_list_command_empty(db_session):
    pass


def test_list_command_with_targets(db_session):
    pass
