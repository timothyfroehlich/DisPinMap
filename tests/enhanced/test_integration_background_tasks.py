"""
Integration Testing Strategy for Background Tasks

This test suite provides integration testing for background tasks, focusing on
end-to-end monitoring functionality and reliability testing that would catch
real-world background task failures.

Key focus areas:
1. Tests that run actual monitoring loops in test environments
2. Tests that verify end-to-end monitoring functionality
3. Performance and reliability testing for background tasks
4. Integration testing between task loops, database, and Discord API
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cogs.monitor import MachineMonitor
from src.cogs.monitoring import MonitoringCog
from src.notifier import Notifier
from tests.utils.db_utils import cleanup_test_database, setup_test_database
from tests.utils.time_mock import MonitoringSimulator, TimeController

logger = logging.getLogger(__name__)


@pytest.fixture
def integration_test_database():
    """Create integration test database with realistic data."""
    test_db = setup_test_database()

    # Add multiple channels with different configurations
    channels = [
        (12345, 67890, "Seattle Channel", 30, "all"),  # 30 min polling
        (12346, 67891, "Portland Channel", 60, "machines"),  # 1 hour polling
        (12347, 67892, "Austin Channel", 45, "comments"),  # 45 min polling
    ]

    for channel_id, guild_id, name, poll_rate, notifications in channels:
        test_db.update_channel_config(
            channel_id,
            guild_id,
            poll_rate_minutes=poll_rate,
            notification_types=notifications,
        )

    # Add monitoring targets for each channel
    test_db.add_monitoring_target(12345, "location", "Seattle Pinball Museum", "1309")
    test_db.add_monitoring_target(12345, "latlong", "47.6062,-122.3321,5")

    test_db.add_monitoring_target(12346, "city", "Portland, OR", "45.5152,-122.6784,10")
    test_db.add_monitoring_target(12346, "location", "Ground Kontrol", "456")

    test_db.add_monitoring_target(12347, "latlong", "30.2672,-97.7431,8")

    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def integration_mock_bot():
    """Create mock bot for integration testing."""
    bot = AsyncMock()
    bot.wait_until_ready = AsyncMock()

    # Create mock channels for each test channel
    channels = {}
    for channel_id in [12345, 12346, 12347]:
        channel = AsyncMock()
        channel.id = channel_id
        channel.send = AsyncMock()
        channels[channel_id] = channel

    def get_channel(channel_id):
        return channels.get(channel_id)

    bot.get_channel = MagicMock(side_effect=get_channel)
    bot.channels = channels

    return bot


@pytest.fixture
def integration_notifier():
    """Create notifier for integration testing."""
    return Notifier()


@pytest.mark.asyncio
@pytest.mark.integration
class TestActualMonitoringLoopExecution:
    """Test actual monitoring loop execution in controlled environments."""

    async def test_real_monitoring_loop_execution(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test that real monitoring loops execute and process channels correctly."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track monitoring activity
        monitoring_activity = {
            "channels_processed": set(),
            "api_calls_made": [],
            "messages_sent": [],
            "errors_encountered": [],
        }

        # Mock API calls to track execution
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_location_fetch, patch(
            "src.cogs.monitor.fetch_submissions_for_coordinates", new_callable=AsyncMock
        ) as mock_coord_fetch:
            # Setup API mocks to return controlled data
            mock_location_fetch.return_value = [
                {
                    "id": "test_submission_1",
                    "type": "machine_added",
                    "machine_name": "Medieval Madness",
                    "location_name": "Seattle Pinball Museum",
                    "location_id": 1309,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "user_name": "TestUser",
                }
            ]

            mock_coord_fetch.return_value = [
                {
                    "id": "test_submission_2",
                    "type": "machine_removed",
                    "machine_name": "Attack From Mars",
                    "location_name": "Test Location",
                    "location_id": 999,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "user_name": "TestUser2",
                }
            ]

            # Wrap methods to track activity
            original_run_checks = monitor_cog.run_checks_for_channel

            async def tracking_run_checks(channel_id, config, is_manual_check=False):
                monitoring_activity["channels_processed"].add(channel_id)
                try:
                    result = await original_run_checks(
                        channel_id, config, is_manual_check
                    )
                    return result
                except Exception as e:
                    monitoring_activity["errors_encountered"].append(
                        {
                            "channel_id": channel_id,
                            "error": str(e),
                            "time": datetime.now(timezone.utc),
                        }
                    )
                    raise

            monitor_cog.run_checks_for_channel = tracking_run_checks

            # Track API calls
            def track_api_calls(func_name):
                def decorator(original_func):
                    async def wrapper(*args, **kwargs):
                        monitoring_activity["api_calls_made"].append(
                            {
                                "function": func_name,
                                "args": args,
                                "kwargs": kwargs,
                                "time": datetime.now(timezone.utc),
                            }
                        )
                        return await original_func(*args, **kwargs)

                    return wrapper

                return decorator

            mock_location_fetch.side_effect = track_api_calls(
                "fetch_submissions_for_location"
            )(
                mock_location_fetch.side_effect
                or mock_location_fetch.return_value.__class__
            )
            mock_coord_fetch.side_effect = track_api_calls(
                "fetch_submissions_for_coordinates"
            )(mock_coord_fetch.side_effect or mock_coord_fetch.return_value.__class__)

            # Start the actual monitoring loop
            monitor_cog.cog_load()

            try:
                # Wait for monitoring to process channels
                wait_time = 0
                max_wait = 10  # 10 seconds max

                while (
                    len(monitoring_activity["channels_processed"]) == 0
                    and wait_time < max_wait
                ):
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify real monitoring occurred
                assert (
                    len(monitoring_activity["channels_processed"]) > 0
                ), "No channels were processed by monitoring loop"

                # Should have processed all active channels
                active_channels = integration_test_database.get_active_channels()
                active_channel_ids = {ch["channel_id"] for ch in active_channels}
                processed_channel_ids = monitoring_activity["channels_processed"]

                assert processed_channel_ids.intersection(
                    active_channel_ids
                ), f"Active channels {active_channel_ids} not processed {processed_channel_ids}"

                # Should have made API calls
                assert (
                    len(monitoring_activity["api_calls_made"]) > 0
                ), "No API calls were made during monitoring"

                # Should not have errors (in this controlled test)
                assert (
                    len(monitoring_activity["errors_encountered"]) == 0
                ), f"Errors during monitoring: {monitoring_activity['errors_encountered']}"

                logger.info(
                    f"Integration test results: {len(monitoring_activity['channels_processed'])} channels processed, {len(monitoring_activity['api_calls_made'])} API calls made"
                )

            finally:
                monitor_cog.cog_unload()

    async def test_monitoring_loop_handles_channel_polling_intervals(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test that monitoring loop respects different channel polling intervals."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track polling decisions
        polling_decisions = []

        original_should_poll = monitor_cog._should_poll_channel

        async def tracking_should_poll(config):
            result = await original_should_poll(config)
            polling_decisions.append(
                {
                    "channel_id": config.get("channel_id"),
                    "should_poll": result,
                    "poll_rate": config.get("poll_rate_minutes"),
                    "last_poll_at": config.get("last_poll_at"),
                    "time": datetime.now(timezone.utc),
                }
            )
            return result

        monitor_cog._should_poll_channel = tracking_should_poll

        # Set different last poll times to test interval logic
        now = datetime.now(timezone.utc)

        # Channel 12345 (30 min) - last polled 35 minutes ago (should poll)
        integration_test_database.update_channel_last_poll_time(
            12345, now - timedelta(minutes=35)
        )

        # Channel 12346 (60 min) - last polled 45 minutes ago (should not poll)
        integration_test_database.update_channel_last_poll_time(
            12346, now - timedelta(minutes=45)
        )

        # Channel 12347 (45 min) - last polled 50 minutes ago (should poll)
        integration_test_database.update_channel_last_poll_time(
            12347, now - timedelta(minutes=50)
        )

        # Mock API to avoid real calls
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Start monitoring
            monitor_cog.cog_load()

            try:
                # Wait for polling decisions
                wait_time = 0
                max_wait = 5

                while len(polling_decisions) < 3 and wait_time < max_wait:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify polling decisions respect intervals
                decisions_by_channel = {d["channel_id"]: d for d in polling_decisions}

                # Channel 12345 (30 min interval, 35 min ago) should poll
                if 12345 in decisions_by_channel:
                    assert decisions_by_channel[12345][
                        "should_poll"
                    ], "Channel 12345 should poll (35 min > 30 min interval)"

                # Channel 12346 (60 min interval, 45 min ago) should not poll
                if 12346 in decisions_by_channel:
                    assert not decisions_by_channel[12346][
                        "should_poll"
                    ], "Channel 12346 should not poll (45 min < 60 min interval)"

                # Channel 12347 (45 min interval, 50 min ago) should poll
                if 12347 in decisions_by_channel:
                    assert decisions_by_channel[12347][
                        "should_poll"
                    ], "Channel 12347 should poll (50 min > 45 min interval)"

                logger.info(
                    f"Polling interval test: {len(polling_decisions)} decisions made"
                )

            finally:
                monitor_cog.cog_unload()

    async def test_monitoring_loop_error_resilience(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test that monitoring loop is resilient to various errors."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track error recovery
        error_recovery_log = []

        # Inject errors in different scenarios
        api_call_count = 0

        async def failing_api_fetch(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1

            if api_call_count <= 2:
                # First two calls fail
                error_recovery_log.append(f"API failure #{api_call_count}")
                raise Exception(f"Simulated API failure #{api_call_count}")
            else:
                # Subsequent calls succeed
                error_recovery_log.append(f"API success #{api_call_count}")
                return []

        with patch(
            "src.cogs.monitor.fetch_submissions_for_location",
            side_effect=failing_api_fetch,
        ), patch(
            "src.cogs.monitor.fetch_submissions_for_coordinates",
            side_effect=failing_api_fetch,
        ):
            # Start monitoring
            monitor_cog.cog_load()

            try:
                # Wait for multiple monitoring cycles to test recovery
                wait_time = 0
                max_wait = 10

                while api_call_count < 5 and wait_time < max_wait:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify error recovery occurred
                assert (
                    api_call_count >= 3
                ), f"Expected recovery after failures, got {api_call_count} attempts"

                # Should have both failures and successes
                failures = [log for log in error_recovery_log if "failure" in log]
                successes = [log for log in error_recovery_log if "success" in log]

                assert (
                    len(failures) >= 2
                ), f"Expected failures for testing, got {failures}"
                assert (
                    len(successes) >= 1
                ), f"Expected recovery after failures, got {successes}"

                # Monitoring loop should still be running
                assert (
                    monitor_cog.monitor_task_loop.is_running()
                ), "Monitoring loop stopped after errors"

                logger.info(
                    f"Error resilience test: {len(failures)} failures, {len(successes)} recoveries"
                )

            finally:
                monitor_cog.cog_unload()


@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEndMonitoringFunctionality:
    """Test end-to-end monitoring functionality with all components."""

    async def test_complete_monitoring_pipeline(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test complete monitoring pipeline from database to Discord notifications."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track the complete pipeline
        pipeline_log = {
            "database_queries": [],
            "api_calls": [],
            "notification_posts": [],
            "database_updates": [],
        }

        # Mock database methods to track queries
        original_get_active = integration_test_database.get_active_channels
        original_get_targets = integration_test_database.get_monitoring_targets
        original_filter_new = integration_test_database.filter_new_submissions
        original_mark_seen = integration_test_database.mark_submissions_seen
        original_update_poll_time = (
            integration_test_database.update_channel_last_poll_time
        )

        def tracking_get_active():
            result = original_get_active()
            pipeline_log["database_queries"].append(
                ("get_active_channels", len(result))
            )
            return result

        def tracking_get_targets(channel_id):
            result = original_get_targets(channel_id)
            pipeline_log["database_queries"].append(
                ("get_monitoring_targets", channel_id, len(result))
            )
            return result

        def tracking_filter_new(channel_id, submissions):
            result = original_filter_new(channel_id, submissions)
            pipeline_log["database_queries"].append(
                ("filter_new_submissions", channel_id, len(submissions), len(result))
            )
            return result

        def tracking_mark_seen(channel_id, submission_ids):
            result = original_mark_seen(channel_id, submission_ids)
            pipeline_log["database_updates"].append(
                ("mark_submissions_seen", channel_id, len(submission_ids))
            )
            return result

        def tracking_update_poll_time(channel_id, timestamp):
            result = original_update_poll_time(channel_id, timestamp)
            pipeline_log["database_updates"].append(
                ("update_poll_time", channel_id, timestamp)
            )
            return result

        # Apply tracking wrappers
        integration_test_database.get_active_channels = tracking_get_active
        integration_test_database.get_monitoring_targets = tracking_get_targets
        integration_test_database.filter_new_submissions = tracking_filter_new
        integration_test_database.mark_submissions_seen = tracking_mark_seen
        integration_test_database.update_channel_last_poll_time = (
            tracking_update_poll_time
        )

        # Mock notifier to track notifications
        original_post_submissions = integration_notifier.post_submissions

        async def tracking_post_submissions(channel, submissions, config):
            pipeline_log["notification_posts"].append(
                {
                    "channel_id": channel.id,
                    "submission_count": len(submissions),
                    "config": config,
                }
            )
            return await original_post_submissions(channel, submissions, config)

        integration_notifier.post_submissions = tracking_post_submissions

        # Mock API calls with realistic submissions
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_location_fetch, patch(
            "src.cogs.monitor.fetch_submissions_for_coordinates", new_callable=AsyncMock
        ) as mock_coord_fetch:
            # Setup realistic submission data
            test_submissions = [
                {
                    "id": f"submission_{i}",
                    "type": "machine_added",
                    "machine_name": f"Test Machine {i}",
                    "location_name": "Test Location",
                    "location_id": 1309,
                    "created_at": (
                        datetime.now(timezone.utc) - timedelta(minutes=i)
                    ).isoformat(),
                    "user_name": "TestUser",
                }
                for i in range(3)
            ]

            mock_location_fetch.return_value = test_submissions
            mock_coord_fetch.return_value = test_submissions

            # Track API calls
            def track_api_call(func_name):
                def wrapper(*args, **kwargs):
                    pipeline_log["api_calls"].append(
                        {"function": func_name, "args": args, "kwargs": kwargs}
                    )
                    return (
                        mock_location_fetch.return_value
                        if func_name == "location"
                        else mock_coord_fetch.return_value
                    )

                return AsyncMock(side_effect=wrapper)

            mock_location_fetch.side_effect = track_api_call("location")
            mock_coord_fetch.side_effect = track_api_call("coordinates")

            # Start monitoring
            monitor_cog.cog_load()

            try:
                # Wait for complete pipeline execution
                wait_time = 0
                max_wait = 10

                while (
                    len(pipeline_log["database_queries"]) == 0
                    or len(pipeline_log["api_calls"]) == 0
                ) and wait_time < max_wait:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify complete pipeline execution
                assert (
                    len(pipeline_log["database_queries"]) > 0
                ), "No database queries made"
                assert len(pipeline_log["api_calls"]) > 0, "No API calls made"

                # Should have queried active channels
                active_channel_queries = [
                    q
                    for q in pipeline_log["database_queries"]
                    if q[0] == "get_active_channels"
                ]
                assert len(active_channel_queries) > 0, "Did not query active channels"

                # Should have queried monitoring targets
                target_queries = [
                    q
                    for q in pipeline_log["database_queries"]
                    if q[0] == "get_monitoring_targets"
                ]
                assert len(target_queries) > 0, "Did not query monitoring targets"

                # Should have made API calls for submissions
                assert (
                    len(pipeline_log["api_calls"]) > 0
                ), "No submission API calls made"

                # Pipeline should update database with results
                if len(pipeline_log["notification_posts"]) > 0:
                    # If notifications were posted, should have marked submissions as seen
                    mark_seen_updates = [
                        u
                        for u in pipeline_log["database_updates"]
                        if u[0] == "mark_submissions_seen"
                    ]
                    assert (
                        len(mark_seen_updates) > 0
                    ), "Did not mark submissions as seen after posting"

                # Should update poll times
                poll_time_updates = [
                    u
                    for u in pipeline_log["database_updates"]
                    if u[0] == "update_poll_time"
                ]
                assert len(poll_time_updates) > 0, "Did not update poll times"

                logger.info(
                    f"Complete pipeline test: {len(pipeline_log['database_queries'])} DB queries, {len(pipeline_log['api_calls'])} API calls, {len(pipeline_log['notification_posts'])} notifications"
                )

            finally:
                monitor_cog.cog_unload()
                # Restore original methods
                integration_test_database.get_active_channels = original_get_active
                integration_test_database.get_monitoring_targets = original_get_targets
                integration_test_database.filter_new_submissions = original_filter_new
                integration_test_database.mark_submissions_seen = original_mark_seen
                integration_test_database.update_channel_last_poll_time = (
                    original_update_poll_time
                )
                integration_notifier.post_submissions = original_post_submissions

    async def test_multi_channel_monitoring_isolation(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test that multi-channel monitoring maintains proper isolation."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track per-channel activity
        channel_activity = {}

        original_run_checks = monitor_cog.run_checks_for_channel

        async def channel_tracking_run_checks(
            channel_id, config, is_manual_check=False
        ):
            if channel_id not in channel_activity:
                channel_activity[channel_id] = {
                    "checks_run": 0,
                    "config": config,
                    "last_check_time": None,
                }

            channel_activity[channel_id]["checks_run"] += 1
            channel_activity[channel_id]["last_check_time"] = datetime.now(timezone.utc)

            return await original_run_checks(channel_id, config, is_manual_check)

        monitor_cog.run_checks_for_channel = channel_tracking_run_checks

        # Mock API with different responses for different channels
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_location_fetch, patch(
            "src.cogs.monitor.fetch_submissions_for_coordinates", new_callable=AsyncMock
        ) as mock_coord_fetch:
            # Different submission data for different calls (simulating different locations)
            submission_responses = [
                [
                    {
                        "id": "sub_1",
                        "type": "machine_added",
                        "machine_name": "Machine A",
                        "location_name": "Location A",
                        "location_id": 1,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_name": "User1",
                    }
                ],
                [
                    {
                        "id": "sub_2",
                        "type": "machine_removed",
                        "machine_name": "Machine B",
                        "location_name": "Location B",
                        "location_id": 2,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_name": "User2",
                    }
                ],
                [
                    {
                        "id": "sub_3",
                        "type": "machine_comment",
                        "machine_name": "Machine C",
                        "location_name": "Location C",
                        "location_id": 3,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_name": "User3",
                    }
                ],
            ]

            call_count = 0

            def rotating_responses(*args, **kwargs):
                nonlocal call_count
                response = submission_responses[call_count % len(submission_responses)]
                call_count += 1
                return response

            mock_location_fetch.side_effect = rotating_responses
            mock_coord_fetch.side_effect = rotating_responses

            # Start monitoring
            monitor_cog.cog_load()

            try:
                # Wait for multi-channel monitoring
                wait_time = 0
                max_wait = 10

                while len(channel_activity) < 2 and wait_time < max_wait:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify multiple channels were processed
                assert (
                    len(channel_activity) >= 2
                ), f"Expected multiple channels, got {len(channel_activity)} channels processed"

                # Verify each channel maintains separate state
                channel_ids = list(channel_activity.keys())
                for channel_id in channel_ids:
                    activity = channel_activity[channel_id]
                    assert (
                        activity["checks_run"] > 0
                    ), f"Channel {channel_id} was not checked"
                    assert (
                        activity["config"] is not None
                    ), f"Channel {channel_id} missing config"
                    assert (
                        activity["last_check_time"] is not None
                    ), f"Channel {channel_id} missing check time"

                # Verify channels have different configurations (from test setup)
                configs = [activity["config"] for activity in channel_activity.values()]
                poll_rates = [config.get("poll_rate_minutes") for config in configs]

                # Should have different poll rates from test setup (30, 60, 45)
                unique_poll_rates = set(poll_rates)
                assert (
                    len(unique_poll_rates) > 1
                ), f"Expected different poll rates, got {poll_rates}"

                logger.info(
                    f"Multi-channel isolation test: {len(channel_activity)} channels processed with different configurations"
                )

            finally:
                monitor_cog.cog_unload()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceAndReliabilityTesting:
    """Performance and reliability testing for background tasks."""

    async def test_monitoring_performance_under_load(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test monitoring performance with many channels and targets."""
        # Add many channels and targets for load testing
        for i in range(20):  # 20 channels
            channel_id = 50000 + i
            guild_id = 60000 + i
            integration_test_database.update_channel_config(
                channel_id, guild_id, poll_rate_minutes=30, notification_types="all"
            )

            # Add multiple targets per channel
            for j in range(5):  # 5 targets per channel
                target_id = 1000 + (i * 5) + j
                integration_test_database.add_monitoring_target(
                    channel_id, "location", f"Location {i}-{j}", str(target_id)
                )

        # Setup mock bot for all channels
        channels = {}
        for i in range(20):
            channel_id = 50000 + i
            channel = AsyncMock()
            channel.id = channel_id
            channel.send = AsyncMock()
            channels[channel_id] = channel

        def get_channel(channel_id):
            return channels.get(channel_id)

        integration_mock_bot.get_channel = MagicMock(side_effect=get_channel)

        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track performance metrics
        performance_metrics = {
            "start_time": None,
            "end_time": None,
            "channels_processed": 0,
            "api_calls_made": 0,
            "errors_encountered": 0,
            "max_processing_time": 0,
            "min_processing_time": float("inf"),
        }

        original_run_checks = monitor_cog.run_checks_for_channel

        async def performance_tracking_run_checks(
            channel_id, config, is_manual_check=False
        ):
            check_start = datetime.now(timezone.utc)

            try:
                result = await original_run_checks(channel_id, config, is_manual_check)
                performance_metrics["channels_processed"] += 1

                check_time = (datetime.now(timezone.utc) - check_start).total_seconds()
                performance_metrics["max_processing_time"] = max(
                    performance_metrics["max_processing_time"], check_time
                )
                performance_metrics["min_processing_time"] = min(
                    performance_metrics["min_processing_time"], check_time
                )

                return result
            except Exception as e:
                performance_metrics["errors_encountered"] += 1
                raise

        monitor_cog.run_checks_for_channel = performance_tracking_run_checks

        # Mock API to return quickly
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []  # Empty responses for speed

            def track_api_call(*args, **kwargs):
                performance_metrics["api_calls_made"] += 1
                return []

            mock_fetch.side_effect = track_api_call

            # Start monitoring and measure performance
            performance_metrics["start_time"] = datetime.now(timezone.utc)
            monitor_cog.cog_load()

            try:
                # Wait for substantial processing
                wait_time = 0
                max_wait = 30  # 30 seconds for load test

                while (
                    performance_metrics["channels_processed"] < 10
                    and wait_time < max_wait
                ):
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                performance_metrics["end_time"] = datetime.now(timezone.utc)

                # Verify performance metrics
                assert (
                    performance_metrics["channels_processed"] >= 10
                ), f"Only processed {performance_metrics['channels_processed']} channels"

                total_time = (
                    performance_metrics["end_time"] - performance_metrics["start_time"]
                ).total_seconds()
                channels_per_second = (
                    performance_metrics["channels_processed"] / total_time
                )

                # Performance should be reasonable (at least 1 channel per second)
                assert (
                    channels_per_second >= 0.5
                ), f"Too slow: {channels_per_second} channels/second"

                # Should not have excessive errors
                error_rate = performance_metrics["errors_encountered"] / max(
                    performance_metrics["channels_processed"], 1
                )
                assert (
                    error_rate <= 0.1
                ), f"Too many errors: {error_rate * 100}% error rate"

                logger.info(
                    f"Performance test: {performance_metrics['channels_processed']} channels in {total_time:.2f}s ({channels_per_second:.2f} ch/s), {performance_metrics['api_calls_made']} API calls, {performance_metrics['errors_encountered']} errors"
                )

            finally:
                monitor_cog.cog_unload()

    async def test_monitoring_reliability_over_time(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test monitoring reliability over extended time periods."""
        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track reliability metrics over time
        reliability_metrics = {
            "monitoring_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "uptime_start": None,
            "last_successful_cycle": None,
            "consecutive_failures": 0,
            "max_consecutive_failures": 0,
            "cycle_times": [],
        }

        original_run_checks = monitor_cog.run_checks_for_channel

        async def reliability_tracking_run_checks(
            channel_id, config, is_manual_check=False
        ):
            cycle_start = datetime.now(timezone.utc)
            reliability_metrics["monitoring_cycles"] += 1

            try:
                result = await original_run_checks(channel_id, config, is_manual_check)

                # Track successful cycle
                reliability_metrics["successful_cycles"] += 1
                reliability_metrics["last_successful_cycle"] = cycle_start
                reliability_metrics["consecutive_failures"] = 0

                cycle_time = (datetime.now(timezone.utc) - cycle_start).total_seconds()
                reliability_metrics["cycle_times"].append(cycle_time)

                return result

            except Exception as e:
                # Track failed cycle
                reliability_metrics["failed_cycles"] += 1
                reliability_metrics["consecutive_failures"] += 1
                reliability_metrics["max_consecutive_failures"] = max(
                    reliability_metrics["max_consecutive_failures"],
                    reliability_metrics["consecutive_failures"],
                )
                raise

        monitor_cog.run_checks_for_channel = reliability_tracking_run_checks

        # Simulate various failure conditions
        failure_injection_count = 0

        async def reliability_test_api_call(*args, **kwargs):
            nonlocal failure_injection_count
            failure_injection_count += 1

            # Inject failures periodically to test reliability
            if failure_injection_count % 10 == 0:  # Every 10th call fails
                raise Exception(
                    f"Injected reliability test failure #{failure_injection_count}"
                )

            return []  # Successful response

        with patch(
            "src.cogs.monitor.fetch_submissions_for_location",
            side_effect=reliability_test_api_call,
        ):
            reliability_metrics["uptime_start"] = datetime.now(timezone.utc)
            monitor_cog.cog_load()

            try:
                # Run for extended period to test reliability
                test_duration = 15  # 15 seconds for reliability test
                start_time = datetime.now(timezone.utc)

                while (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() < test_duration:
                    await asyncio.sleep(0.1)

                # Calculate reliability metrics
                total_uptime = (
                    datetime.now(timezone.utc) - reliability_metrics["uptime_start"]
                ).total_seconds()
                success_rate = reliability_metrics["successful_cycles"] / max(
                    reliability_metrics["monitoring_cycles"], 1
                )

                # Verify reliability requirements
                assert (
                    success_rate >= 0.8
                ), f"Success rate too low: {success_rate * 100:.1f}%"
                assert (
                    reliability_metrics["max_consecutive_failures"] <= 3
                ), f"Too many consecutive failures: {reliability_metrics['max_consecutive_failures']}"
                assert (
                    reliability_metrics["monitoring_cycles"] >= 5
                ), f"Not enough monitoring cycles: {reliability_metrics['monitoring_cycles']}"

                # Calculate average cycle time
                if reliability_metrics["cycle_times"]:
                    avg_cycle_time = sum(reliability_metrics["cycle_times"]) / len(
                        reliability_metrics["cycle_times"]
                    )
                    assert (
                        avg_cycle_time <= 5.0
                    ), f"Cycle time too slow: {avg_cycle_time:.2f}s average"

                logger.info(
                    f"Reliability test: {success_rate * 100:.1f}% success rate over {total_uptime:.1f}s, {reliability_metrics['monitoring_cycles']} cycles, max {reliability_metrics['max_consecutive_failures']} consecutive failures"
                )

            finally:
                monitor_cog.cog_unload()

    async def test_memory_usage_during_extended_monitoring(
        self, integration_test_database, integration_mock_bot, integration_notifier
    ):
        """Test memory usage during extended monitoring periods."""
        import gc

        import psutil

        monitor_cog = MachineMonitor(
            integration_mock_bot, integration_test_database, integration_notifier
        )

        # Track memory usage
        memory_metrics = {
            "initial_memory": None,
            "peak_memory": 0,
            "final_memory": None,
            "memory_samples": [],
            "gc_collections": 0,
        }

        # Get initial memory usage
        process = psutil.Process()
        memory_metrics["initial_memory"] = process.memory_info().rss / 1024 / 1024  # MB
        memory_metrics["peak_memory"] = memory_metrics["initial_memory"]

        # Mock API with varying response sizes
        response_size_cycle = 0

        async def memory_test_api_call(*args, **kwargs):
            nonlocal response_size_cycle
            response_size_cycle += 1

            # Create responses of varying sizes to test memory handling
            response_size = (response_size_cycle % 10) + 1  # 1-10 submissions

            submissions = []
            for i in range(response_size):
                submissions.append(
                    {
                        "id": f"mem_test_{response_size_cycle}_{i}",
                        "type": "machine_added",
                        "machine_name": f"Memory Test Machine {i}"
                        * 10,  # Make names longer
                        "location_name": f"Memory Test Location {i}" * 5,
                        "location_id": 1000 + i,
                        "comment": f"This is a memory test comment {i}"
                        * 20,  # Large comments
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_name": f"MemoryTestUser{i}",
                    }
                )

            return submissions

        # Track memory during monitoring
        original_run_checks = monitor_cog.run_checks_for_channel

        async def memory_tracking_run_checks(channel_id, config, is_manual_check=False):
            # Sample memory before processing
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_metrics["memory_samples"].append(current_memory)
            memory_metrics["peak_memory"] = max(
                memory_metrics["peak_memory"], current_memory
            )

            # Force garbage collection periodically
            if len(memory_metrics["memory_samples"]) % 10 == 0:
                gc.collect()
                memory_metrics["gc_collections"] += 1

            return await original_run_checks(channel_id, config, is_manual_check)

        monitor_cog.run_checks_for_channel = memory_tracking_run_checks

        with patch(
            "src.cogs.monitor.fetch_submissions_for_location",
            side_effect=memory_test_api_call,
        ):
            monitor_cog.cog_load()

            try:
                # Run for extended period to observe memory patterns
                test_duration = 10  # 10 seconds
                start_time = datetime.now(timezone.utc)

                while (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() < test_duration:
                    await asyncio.sleep(0.1)

                # Final memory measurement
                memory_metrics["final_memory"] = process.memory_info().rss / 1024 / 1024

                # Analyze memory usage
                memory_growth = (
                    memory_metrics["final_memory"] - memory_metrics["initial_memory"]
                )
                memory_growth_percent = (
                    memory_growth / memory_metrics["initial_memory"]
                ) * 100

                # Memory growth should be reasonable
                assert (
                    memory_growth_percent <= 50
                ), f"Excessive memory growth: {memory_growth_percent:.1f}%"
                assert (
                    memory_metrics["peak_memory"]
                    <= memory_metrics["initial_memory"] * 2
                ), f"Peak memory too high: {memory_metrics['peak_memory']:.1f}MB"

                # Should have collected some memory samples
                assert (
                    len(memory_metrics["memory_samples"]) >= 5
                ), f"Not enough memory samples: {len(memory_metrics['memory_samples'])}"

                logger.info(
                    f"Memory test: {memory_metrics['initial_memory']:.1f}MB → {memory_metrics['final_memory']:.1f}MB (growth: {memory_growth_percent:.1f}%), peak: {memory_metrics['peak_memory']:.1f}MB, {memory_metrics['gc_collections']} GC cycles"
                )

            finally:
                monitor_cog.cog_unload()
