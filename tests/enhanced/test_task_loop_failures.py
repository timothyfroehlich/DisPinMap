"""
Enhanced Testing for @tasks.loop Failures

This test suite is designed to catch background task failures that were missed
by the existing simulation framework. It focuses on verifying that Discord.py
@tasks.loop decorators actually execute and can detect long-running failures.

Key improvements over existing tests:
1. Tests actual @tasks.loop execution, not just method calls
2. Verifies loop health monitoring and failure detection
3. Uses accelerated time to test scheduling without waiting
4. Validates database polling occurs in real monitoring scenarios
5. Detects loop cancellation and restart scenarios
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cogs.monitor import MachineMonitor
from tests.utils.db_utils import cleanup_test_database, setup_test_database
from tests.utils.time_mock import MonitoringSimulator, TimeController

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_bot():
    """Create a mock bot for task loop testing"""
    bot = AsyncMock()
    bot.wait_until_ready = AsyncMock()
    channel = AsyncMock()
    channel.id = 12345
    bot.get_channel = MagicMock(return_value=channel)
    return bot


@pytest.fixture
def db():
    """Create test database"""
    test_db = setup_test_database()
    yield test_db
    cleanup_test_database(test_db)


@pytest.fixture
def mock_notifier():
    """Create mock notifier"""
    return AsyncMock()


@pytest.fixture
def monitor_cog(mock_bot, db, mock_notifier):
    """Create monitor cog with real task loop"""
    return MachineMonitor(mock_bot, db, mock_notifier)


@pytest.mark.asyncio
class TestTaskLoopExecution:
    """Test that @tasks.loop actually executes and can be monitored."""

    async def test_monitor_task_loop_starts_on_cog_load(self, monitor_cog):
        """Verify that the monitor task loop starts when cog is loaded."""
        # Initially, task should not be running
        assert not monitor_cog.monitor_task_loop.is_running()

        # Load the cog (starts the task)
        monitor_cog.cog_load()

        # Task should now be running
        assert monitor_cog.monitor_task_loop.is_running()

        # Cleanup
        monitor_cog.cog_unload()

    async def test_monitor_task_loop_stops_on_cog_unload(self, monitor_cog):
        """Verify that the monitor task loop stops when cog is unloaded."""
        # Start the task
        monitor_cog.cog_load()
        assert monitor_cog.monitor_task_loop.is_running()

        # Unload the cog (stops the task)
        monitor_cog.cog_unload()

        # Task should be cancelled
        assert not monitor_cog.monitor_task_loop.is_running()

    async def test_task_loop_actual_execution_detection(self, monitor_cog, db):
        """Test that we can detect when the task loop actually executes."""
        # Setup monitoring target to ensure loop has work to do
        channel_id = 12345
        guild_id = 67890
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(
            channel_id, guild_id, poll_rate_minutes=1
        )  # 1 minute polling

        # Track task execution
        execution_count = 0
        original_run_checks = monitor_cog.run_checks_for_channel

        async def counting_run_checks(*args, **kwargs):
            nonlocal execution_count
            execution_count += 1
            # Call original but with mocked API to avoid real calls
            with patch(
                "src.cogs.monitor.fetch_submissions_for_location",
                new_callable=AsyncMock,
            ) as mock_fetch:
                mock_fetch.return_value = []
                return await original_run_checks(*args, **kwargs)

        # Replace the method to track calls
        monitor_cog.run_checks_for_channel = counting_run_checks

        # Start the task loop
        monitor_cog.cog_load()

        try:
            # Wait for at least one execution (with timeout for safety)
            wait_time = 0
            max_wait = 5  # 5 seconds max wait
            while execution_count == 0 and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1

            # Verify the task loop actually executed
            assert (
                execution_count > 0
            ), f"Task loop did not execute after {max_wait} seconds"

        finally:
            monitor_cog.cog_unload()

    async def test_task_loop_respects_before_loop_wait(self, monitor_cog):
        """Test that the task loop waits for bot ready before starting."""
        # Mock bot that's not ready yet
        monitor_cog.bot.wait_until_ready = AsyncMock()

        # Track if before_loop executed
        before_loop_called = False

        async def mock_before_loop():
            nonlocal before_loop_called
            before_loop_called = True
            await monitor_cog.bot.wait_until_ready()

        # Replace the before_loop method
        monitor_cog.before_monitor_task_loop = mock_before_loop

        # Start the task (this will call before_loop)
        monitor_cog.cog_load()

        # Give it a moment to execute before_loop
        await asyncio.sleep(0.1)

        # Verify before_loop was called
        assert before_loop_called, "before_monitor_task_loop was not called"
        monitor_cog.bot.wait_until_ready.assert_called_once()

        # Cleanup
        monitor_cog.cog_unload()


@pytest.mark.asyncio
class TestTaskLoopHealthMonitoring:
    """Test monitoring of task loop health and failure detection."""

    async def test_task_loop_failure_detection(self, monitor_cog, db):
        """Test detection when task loop fails internally."""
        # Setup monitoring target
        channel_id = 12345
        guild_id = 67890
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(channel_id, guild_id)

        # Track task failures
        task_failures = []

        # Make run_checks_for_channel raise an exception
        async def failing_run_checks(*args, **kwargs):
            task_failures.append(datetime.now(timezone.utc))
            raise Exception("Simulated task failure")

        monitor_cog.run_checks_for_channel = failing_run_checks

        # Start the task loop
        monitor_cog.cog_load()

        try:
            # Wait for at least one failure
            wait_time = 0
            max_wait = 3
            while len(task_failures) == 0 and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1

            # Verify failure was detected
            assert len(task_failures) > 0, "Task loop failure was not detected"

            # The task loop should still be running (Discord.py tasks are resilient)
            assert (
                monitor_cog.monitor_task_loop.is_running()
            ), "Task loop stopped after failure"

        finally:
            monitor_cog.cog_unload()

    async def test_task_loop_recovery_after_exception(self, monitor_cog, db):
        """Test that task loop recovers and continues after exceptions."""
        # Setup monitoring target
        channel_id = 12345
        guild_id = 67890
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(channel_id, guild_id)

        # Track successful and failed executions
        execution_results = []
        failure_count = 0

        async def alternating_run_checks(*args, **kwargs):
            nonlocal failure_count
            if failure_count < 2:  # Fail first 2 times
                failure_count += 1
                execution_results.append("failure")
                raise Exception(f"Simulated failure #{failure_count}")
            else:
                execution_results.append("success")
                # Mock successful execution
                with patch(
                    "src.cogs.monitor.fetch_submissions_for_location",
                    new_callable=AsyncMock,
                ) as mock_fetch:
                    mock_fetch.return_value = []
                    return await monitor_cog.__class__.run_checks_for_channel(
                        monitor_cog, *args, **kwargs
                    )

        monitor_cog.run_checks_for_channel = alternating_run_checks

        # Start the task loop
        monitor_cog.cog_load()

        try:
            # Wait for recovery (should have failures then success)
            wait_time = 0
            max_wait = 5
            while len(execution_results) < 3 and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1

            # Verify we had failures followed by recovery
            assert (
                len(execution_results) >= 3
            ), f"Not enough executions: {execution_results}"
            assert "failure" in execution_results, "No failures detected"
            assert "success" in execution_results, "No recovery detected"

            # Task should still be running
            assert (
                monitor_cog.monitor_task_loop.is_running()
            ), "Task loop stopped after recovery"

        finally:
            monitor_cog.cog_unload()


@pytest.mark.asyncio
class TestLongRunningTaskScenarios:
    """Test long-running scenarios that can detect background task failures."""

    async def test_accelerated_long_running_monitoring(self, monitor_cog, db):
        """Test long-running monitoring scenario with time acceleration."""
        # Setup monitoring environment
        channel_id = 12345
        guild_id = 67890
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(
            channel_id, guild_id, poll_rate_minutes=30
        )  # 30 min intervals

        # Use time controller for acceleration
        time_controller = TimeController()
        time_controller.start()

        # Track monitoring executions with timestamps
        execution_log = []

        async def logging_run_checks(*args, **kwargs):
            execution_log.append(
                {"time": time_controller.current_time, "args": args, "kwargs": kwargs}
            )
            # Mock successful execution
            with patch(
                "src.cogs.monitor.fetch_submissions_for_location",
                new_callable=AsyncMock,
            ) as mock_fetch:
                mock_fetch.return_value = []
                return await monitor_cog.__class__.run_checks_for_channel(
                    monitor_cog, *args, **kwargs
                )

        monitor_cog.run_checks_for_channel = logging_run_checks

        # Use monitoring simulator for accelerated testing
        monitoring_sim = MonitoringSimulator(time_controller, monitor_cog)

        try:
            # Simulate 6 hours of monitoring (should trigger multiple polls)
            result = await monitoring_sim.simulate_monitoring_cycle(
                duration_minutes=360
            )

            # Verify monitoring occurred multiple times
            assert (
                result["polling_cycles"] >= 12
            ), f"Expected 12+ cycles, got {result['polling_cycles']}"
            assert (
                len(execution_log) >= 12
            ), f"Expected 12+ executions, got {len(execution_log)}"

            # Verify timing intervals are respected
            if len(execution_log) >= 2:
                time_diff = execution_log[1]["time"] - execution_log[0]["time"]
                # Should be close to 30 minutes (allowing for simulation timing)
                assert time_diff >= timedelta(
                    minutes=25
                ), f"Timing interval too short: {time_diff}"

        finally:
            time_controller.stop()

    async def test_database_polling_verification(self, monitor_cog, db):
        """Test that actual database polling occurs during monitoring."""
        # Setup multiple channels and targets
        channels_data = [
            (12345, 67890, "location", "Test Location 1", "123"),
            (12346, 67891, "location", "Test Location 2", "456"),
        ]

        for (
            channel_id,
            guild_id,
            target_type,
            target_name,
            target_data,
        ) in channels_data:
            db.add_monitoring_target(channel_id, target_type, target_name, target_data)
            db.update_channel_config(channel_id, guild_id, poll_rate_minutes=1)

        # Track database method calls
        db_call_log = []
        original_get_active_channels = db.get_active_channels
        original_get_monitoring_targets = db.get_monitoring_targets

        def logging_get_active_channels():
            result = original_get_active_channels()
            db_call_log.append(("get_active_channels", len(result)))
            return result

        def logging_get_monitoring_targets(channel_id):
            result = original_get_monitoring_targets(channel_id)
            db_call_log.append(("get_monitoring_targets", channel_id, len(result)))
            return result

        db.get_active_channels = logging_get_active_channels
        db.get_monitoring_targets = logging_get_monitoring_targets

        # Mock API calls to avoid real network
        with patch(
            "src.cogs.monitor.fetch_submissions_for_location", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Start task loop
            monitor_cog.cog_load()

            try:
                # Wait for database polling to occur
                wait_time = 0
                max_wait = 3
                while len(db_call_log) == 0 and wait_time < max_wait:
                    await asyncio.sleep(0.1)
                    wait_time += 0.1

                # Verify database was actually polled
                assert len(db_call_log) > 0, "No database polling detected"

                # Should have called get_active_channels
                active_channel_calls = [
                    call for call in db_call_log if call[0] == "get_active_channels"
                ]
                assert (
                    len(active_channel_calls) > 0
                ), "get_active_channels was not called"

                # Should have found the active channels
                assert (
                    active_channel_calls[0][1] == 2
                ), f"Expected 2 active channels, got {active_channel_calls[0][1]}"

            finally:
                monitor_cog.cog_unload()
                # Restore original methods
                db.get_active_channels = original_get_active_channels
                db.get_monitoring_targets = original_get_monitoring_targets


@pytest.mark.asyncio
class TestTaskLoopSchedulingAccuracy:
    """Test that @tasks.loop scheduling works accurately without waiting."""

    async def test_one_minute_loop_timing_with_acceleration(self, monitor_cog, db):
        """Test that 1-minute loop timing is accurate using time acceleration."""
        # Setup monitoring target
        channel_id = 12345
        guild_id = 67890
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(channel_id, guild_id)

        # Track execution times (relative to start)
        start_time = datetime.now(timezone.utc)
        execution_times = []

        async def timing_run_checks(*args, **kwargs):
            execution_times.append(datetime.now(timezone.utc) - start_time)
            # Mock to avoid real API calls
            return False

        monitor_cog.run_checks_for_channel = timing_run_checks

        # The task loop is set to 1 minute intervals
        # We'll run for ~3 minutes to get multiple executions
        monitor_cog.cog_load()

        try:
            # Wait for at least 3 executions (allowing 4 minutes max)
            wait_time = 0
            max_wait = 240  # 4 minutes in seconds
            while len(execution_times) < 3 and wait_time < max_wait:
                await asyncio.sleep(1)  # Check every second
                wait_time += 1

            # Verify we got multiple executions
            assert (
                len(execution_times) >= 3
            ), f"Expected 3+ executions, got {len(execution_times)}"

            # Verify timing intervals are approximately 1 minute
            for i in range(1, len(execution_times)):
                interval = execution_times[i] - execution_times[i - 1]
                # Allow some variance but should be close to 60 seconds
                assert (
                    50 <= interval.total_seconds() <= 70
                ), f"Interval {i} was {interval.total_seconds()}s, expected ~60s"

        finally:
            monitor_cog.cog_unload()

    async def test_custom_poll_rate_timing_accuracy(self, monitor_cog, db):
        """Test that custom poll rates are respected accurately."""
        # Setup with 5-minute poll rate
        channel_id = 12345
        guild_id = 67890
        poll_rate_minutes = 5

        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(
            channel_id, guild_id, poll_rate_minutes=poll_rate_minutes
        )

        # Track when should_poll_channel is called and returns True
        should_poll_calls = []
        original_should_poll = monitor_cog._should_poll_channel

        async def tracking_should_poll(config):
            result = await original_should_poll(config)
            should_poll_calls.append(
                {
                    "time": datetime.now(timezone.utc),
                    "result": result,
                    "channel_id": config.get("channel_id"),
                }
            )
            return result

        monitor_cog._should_poll_channel = tracking_should_poll

        # Set initial poll time to ensure we know the baseline
        past_time = datetime.now(timezone.utc) - timedelta(
            minutes=poll_rate_minutes + 1
        )
        db.update_channel_last_poll_time(channel_id, past_time)

        # Start monitoring
        monitor_cog.cog_load()

        try:
            # Wait for polling decision
            wait_time = 0
            max_wait = 10
            while len(should_poll_calls) == 0 and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1

            # Should have made polling decisions
            assert len(should_poll_calls) > 0, "No polling decisions made"

            # Should return True for first check (past time is old enough)
            true_results = [call for call in should_poll_calls if call["result"]]
            assert len(true_results) > 0, "No True polling decisions found"

        finally:
            monitor_cog.cog_unload()
            monitor_cog._should_poll_channel = original_should_poll


# Integration test that combines all aspects
@pytest.mark.asyncio
@pytest.mark.integration
class TestIntegratedTaskLoopMonitoring:
    """Integration tests combining task loop execution, health monitoring, and database polling."""

    async def test_complete_task_loop_monitoring_cycle(self, monitor_cog, db):
        """Test complete monitoring cycle including task loop health."""
        # Setup comprehensive monitoring environment
        channel_id = 12345
        guild_id = 67890

        # Add multiple types of targets
        db.add_monitoring_target(channel_id, "location", "Test Location", "123")
        db.update_channel_config(channel_id, guild_id, poll_rate_minutes=1)

        # Track all aspects of monitoring
        monitoring_log = {
            "task_executions": 0,
            "database_polls": 0,
            "api_calls": 0,
            "errors": [],
        }

        # Wrap methods to track execution
        original_run_checks = monitor_cog.run_checks_for_channel
        original_get_active = db.get_active_channels

        async def comprehensive_run_checks(*args, **kwargs):
            monitoring_log["task_executions"] += 1
            try:
                with patch(
                    "src.cogs.monitor.fetch_submissions_for_location",
                    new_callable=AsyncMock,
                ) as mock_fetch:
                    monitoring_log["api_calls"] += 1
                    mock_fetch.return_value = []
                    return await original_run_checks(*args, **kwargs)
            except Exception as e:
                monitoring_log["errors"].append(str(e))
                raise

        def comprehensive_get_active():
            monitoring_log["database_polls"] += 1
            return original_get_active()

        monitor_cog.run_checks_for_channel = comprehensive_run_checks
        db.get_active_channels = comprehensive_get_active

        # Run comprehensive test
        monitor_cog.cog_load()

        try:
            # Wait for comprehensive monitoring activity
            wait_time = 0
            max_wait = 5
            while (
                monitoring_log["task_executions"] < 2
                or monitoring_log["database_polls"] < 2
            ) and wait_time < max_wait:
                await asyncio.sleep(0.1)
                wait_time += 0.1

            # Verify all components worked
            assert (
                monitoring_log["task_executions"] >= 2
            ), f"Insufficient task executions: {monitoring_log['task_executions']}"
            assert (
                monitoring_log["database_polls"] >= 2
            ), f"Insufficient database polls: {monitoring_log['database_polls']}"
            assert (
                monitoring_log["api_calls"] >= 2
            ), f"Insufficient API calls: {monitoring_log['api_calls']}"
            assert (
                len(monitoring_log["errors"]) == 0
            ), f"Errors occurred: {monitoring_log['errors']}"

            # Verify task loop health
            assert (
                monitor_cog.monitor_task_loop.is_running()
            ), "Task loop stopped running"

        finally:
            monitor_cog.cog_unload()
            # Restore methods
            monitor_cog.run_checks_for_channel = original_run_checks
            db.get_active_channels = original_get_active
