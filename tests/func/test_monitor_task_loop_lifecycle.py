"""
Functional test for monitor task loop lifecycle and timing issues.

This test is designed to catch the current production issues with monitor loop startup:
1. Task loop starting before bot is ready (RuntimeError)
2. Task loop not executing iterations after startup
3. Database queries not happening during monitoring cycles

This test will FAIL initially, demonstrating our current timing problems.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cogs.monitor import MachineMonitor
from src.notifier import Notifier
from tests.utils.db_utils import cleanup_test_database, setup_test_database

logger = logging.getLogger(__name__)


class MonitorTimingTracker:
    """Tracks timing and method calls for monitor loop lifecycle testing"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.task_loop_states: List[Dict[str, Any]] = []
        self.method_calls: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """Log a timing event"""
        timestamp = datetime.now(timezone.utc)
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details or {},
        }
        self.events.append(event)
        logger.info(f"TIMING EVENT: {event_type} at {timestamp}")

    def log_task_loop_state(self, cog: MachineMonitor):
        """Log current task loop state"""
        timestamp = datetime.now(timezone.utc)
        state = {
            "timestamp": timestamp,
            "is_running": cog.monitor_task_loop.is_running(),
            "is_being_cancelled": cog.monitor_task_loop.is_being_cancelled(),
            "iteration_count": cog.loop_iteration_count,
            "current_loop": cog.monitor_task_loop.current_loop,
        }
        self.task_loop_states.append(state)
        logger.info(f"TASK LOOP STATE: {state}")

    def log_method_call(
        self,
        method_name: str,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ):
        """Log a method call"""
        timestamp = datetime.now(timezone.utc)
        call = {
            "timestamp": timestamp,
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
        }
        self.method_calls.append(call)
        logger.info(f"METHOD CALL: {method_name} at {timestamp}")


@pytest.fixture
def test_database():
    """Create test database with realistic monitoring targets"""
    db = setup_test_database()

    # Add channel with targets (same as production issue)
    channel_id = 1387268568424513587  # testb channel from production logs
    guild_id = 67890

    db.update_channel_config(
        channel_id,
        guild_id,
        poll_rate_minutes=60,
        notification_types="machines",
        is_active=True,
    )
    db.add_monitoring_target(
        channel_id, "city", "Dallas, Texas, US", "32.7767,-96.7970,10"
    )
    db.add_monitoring_target(
        channel_id, "city", "Philadelphia, Pennsylvania, US", "39.9526,-75.1652,10"
    )
    db.add_monitoring_target(
        channel_id, "city", "Detroit, Michigan, US", "42.3314,-83.0458,10"
    )

    yield db
    cleanup_test_database(db)


@pytest.fixture
def timing_tracker():
    """Create timing tracker for monitoring lifecycle events"""
    return MonitorTimingTracker()


@pytest.fixture
def mock_discord_bot(timing_tracker):
    """Create mock Discord bot that simulates realistic lifecycle"""
    bot = AsyncMock()
    bot.user = MagicMock()
    bot.user.name = "TestBot"
    bot.user.id = 12345
    bot.guilds = []

    # Track bot readiness state
    bot._ready = False

    async def mock_wait_until_ready():
        timing_tracker.log_event("wait_until_ready_called", {"bot_ready": bot._ready})
        if not bot._ready:
            # This should cause the RuntimeError we're seeing in production
            raise RuntimeError(
                "Client has not been properly initialised. Please use the login method or asynchronous context manager before calling this method"
            )
        timing_tracker.log_event("wait_until_ready_completed")

    bot.wait_until_ready = mock_wait_until_ready

    # Method to simulate bot becoming ready
    def make_bot_ready():
        timing_tracker.log_event("bot_becomes_ready")
        bot._ready = True

    bot.make_ready = make_bot_ready

    return bot


@pytest.mark.asyncio
async def test_monitor_loop_startup_timing_issues(
    mock_discord_bot, test_database, timing_tracker
):
    """
    Test that catches the current monitor loop timing issues.

    This test will FAIL initially, demonstrating:
    1. Task loop starts before bot is ready
    2. RuntimeError from wait_until_ready()
    3. Task loop doesn't execute iterations
    4. Database queries don't happen
    """
    timing_tracker.log_event("test_start")

    # Create real notifier and monitor cog (not mocked)
    notifier = Notifier(test_database)
    monitor_cog = MachineMonitor(mock_discord_bot, test_database, notifier)

    timing_tracker.log_event("monitor_cog_created")
    timing_tracker.log_task_loop_state(monitor_cog)

    # Track database calls
    original_get_active_channels = test_database.get_active_channels
    db_call_count = 0

    def tracking_get_active_channels():
        nonlocal db_call_count
        db_call_count += 1
        timing_tracker.log_method_call(
            "database.get_active_channels", args=(db_call_count,)
        )
        return original_get_active_channels()

    test_database.get_active_channels = tracking_get_active_channels

    # Track monitor loop method calls
    original_run_checks = monitor_cog.run_checks_for_channel
    monitor_call_count = 0

    async def tracking_run_checks(*args, **kwargs):
        nonlocal monitor_call_count
        monitor_call_count += 1
        timing_tracker.log_method_call(
            "run_checks_for_channel", args=args, kwargs=kwargs
        )
        return await original_run_checks(*args, **kwargs)

    monitor_cog.run_checks_for_channel = tracking_run_checks

    # Test 1: Load cog (this starts the task loop too early)
    timing_tracker.log_event("calling_cog_load")

    # This should demonstrate the timing issue
    try:
        await monitor_cog.cog_load()
        timing_tracker.log_event("cog_load_completed")
    except Exception as e:
        timing_tracker.log_event("cog_load_failed", {"error": str(e)})
        # Don't fail the test here - we expect this timing issue

    timing_tracker.log_task_loop_state(monitor_cog)

    # Test 2: Check if task loop is running (it shouldn't be yet)
    assert (
        not monitor_cog.monitor_task_loop.is_running()
    ), "Task loop should not be running before bot is ready"

    # Test 3: Make bot ready (simulating successful login)
    timing_tracker.log_event("making_bot_ready")
    mock_discord_bot.make_ready()

    # Test 4: Now try to start the task loop properly
    timing_tracker.log_event("starting_task_loop_after_ready")
    try:
        if not monitor_cog.monitor_task_loop.is_running():
            monitor_cog.monitor_task_loop.start()
            timing_tracker.log_event("task_loop_started_successfully")
    except Exception as e:
        timing_tracker.log_event("task_loop_start_failed", {"error": str(e)})
        pytest.fail(f"Task loop should start successfully after bot is ready: {e}")

    timing_tracker.log_task_loop_state(monitor_cog)

    # Test 5: Wait for task loop iterations (should happen every minute in @tasks.loop(minutes=1))
    # For testing, we'll wait a shorter time and check for iterations
    timing_tracker.log_event("waiting_for_iterations")

    initial_iteration_count = monitor_cog.loop_iteration_count
    max_wait = 5  # seconds
    wait_time = 0

    while (
        wait_time < max_wait
        and monitor_cog.loop_iteration_count == initial_iteration_count
    ):
        await asyncio.sleep(0.1)
        wait_time += 0.1
        timing_tracker.log_task_loop_state(monitor_cog)

    timing_tracker.log_event(
        "iteration_wait_completed",
        {
            "initial_count": initial_iteration_count,
            "final_count": monitor_cog.loop_iteration_count,
            "wait_time": wait_time,
        },
    )

    # Test 6: Assert that iterations actually happened
    assert (
        monitor_cog.loop_iteration_count > initial_iteration_count
    ), f"Monitor loop should have executed iterations. Initial: {initial_iteration_count}, Final: {monitor_cog.loop_iteration_count}"

    # Test 7: Assert that database was queried during iterations
    assert (
        db_call_count > 0
    ), f"Database get_active_channels should have been called during monitoring, but call count is {db_call_count}"

    # Test 8: Assert that monitoring methods were called
    assert (
        monitor_call_count > 0
    ), f"run_checks_for_channel should have been called during monitoring, but call count is {monitor_call_count}"

    # Cleanup
    timing_tracker.log_event("cleanup_start")
    if monitor_cog.monitor_task_loop.is_running():
        monitor_cog.monitor_task_loop.cancel()
        timing_tracker.log_event("task_loop_cancelled")

    timing_tracker.log_event("test_completed")

    # Print timing analysis for debugging
    logger.info("=== TIMING ANALYSIS ===")
    for event in timing_tracker.events:
        logger.info(f"{event['timestamp']}: {event['event_type']} - {event['details']}")

    logger.info("=== TASK LOOP STATES ===")
    for state in timing_tracker.task_loop_states:
        logger.info(
            f"{state['timestamp']}: running={state['is_running']}, iterations={state['iteration_count']}"
        )


@pytest.mark.asyncio
async def test_monitor_cog_loading_with_realistic_bot_lifecycle(
    mock_discord_bot, test_database, timing_tracker
):
    """
    Test the monitor cog loading process with realistic Discord bot lifecycle.

    This simulates the actual sequence that happens in main.py:
    1. Load cogs
    2. Bot logs in
    3. Bot becomes ready
    4. Monitor loop should start
    """
    timing_tracker.log_event("realistic_lifecycle_test_start")

    # Step 1: Create cog but don't load it yet (simulating main.py)
    notifier = Notifier(test_database)

    # Step 2: Simulate the bot.add_cog process
    timing_tracker.log_event("simulating_add_cog")
    monitor_cog = MachineMonitor(mock_discord_bot, test_database, notifier)

    # This simulates what happens in Discord.py when add_cog is called
    await monitor_cog.cog_load()
    timing_tracker.log_task_loop_state(monitor_cog)

    # Step 3: Bot is not ready yet - task loop should not be running
    assert (
        not monitor_cog.monitor_task_loop.is_running()
    ), "Task loop should not be running before bot is ready"

    # Step 4: Simulate bot login and ready event
    timing_tracker.log_event("simulating_bot_ready")
    mock_discord_bot.make_ready()

    # Step 5: Simulate the on_ready event triggering monitor start
    # (This is what we need to implement in main.py)
    timing_tracker.log_event("simulating_on_ready_monitor_start")
    if not monitor_cog.monitor_task_loop.is_running():
        try:
            monitor_cog.monitor_task_loop.start()
            timing_tracker.log_event("monitor_started_in_on_ready")
        except Exception as e:
            timing_tracker.log_event(
                "monitor_start_failed_in_on_ready", {"error": str(e)}
            )
            pytest.fail(f"Monitor should start successfully in on_ready: {e}")

    timing_tracker.log_task_loop_state(monitor_cog)

    # Step 6: Verify the monitor is now properly running
    assert (
        monitor_cog.monitor_task_loop.is_running()
    ), "Task loop should be running after proper startup sequence"

    # Cleanup
    if monitor_cog.monitor_task_loop.is_running():
        monitor_cog.monitor_task_loop.cancel()
