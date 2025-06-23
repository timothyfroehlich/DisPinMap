"""
Time Manipulation Framework for Simulation Testing

This module provides utilities for controlling time during tests, allowing
rapid simulation of periodic monitoring tasks and time-based behavior.

Note: This simplified version doesn't patch datetime.datetime.now() due to
immutability in Python 3.13. Instead, it provides manual time control for
the simulation framework.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TimeController:
    """Controls time flow during testing."""

    def __init__(self):
        self.current_time = datetime.now(timezone.utc)
        self.is_active = False

    def set_time(self, target_time: datetime):
        """Set the current simulated time."""
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        self.current_time = target_time
        logger.debug(f"Time set to: {self.current_time}")

    def advance_time(self, delta: timedelta):
        """Advance time by the specified delta."""
        self.current_time += delta
        logger.debug(f"Time advanced to: {self.current_time}")

    def advance_minutes(self, minutes: int):
        """Advance time by the specified number of minutes."""
        self.advance_time(timedelta(minutes=minutes))

    def advance_hours(self, hours: int):
        """Advance time by the specified number of hours."""
        self.advance_time(timedelta(hours=hours))

    def advance_days(self, days: int):
        """Advance time by the specified number of days."""
        self.advance_time(timedelta(days=days))

    def now(self, tz=None) -> datetime:
        """Return the current simulated time."""
        if tz is None:
            return self.current_time
        return self.current_time.astimezone(tz)

    def utcnow(self) -> datetime:
        """Return current UTC time (for datetime.utcnow() replacement)."""
        return self.current_time.replace(tzinfo=None)  # datetime.utcnow() returns naive

    def __enter__(self):
        """Context manager entry - start time control."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop time control."""
        self.stop()

    def start(self):
        """Start time control."""
        if self.is_active:
            return

        self.is_active = True
        logger.info(f"Time control started at: {self.current_time}")

    def stop(self):
        """Stop time control."""
        self.is_active = False
        logger.info("Time control stopped")


class PollingSimulator:
    """Simulates periodic polling tasks with accelerated time."""

    def __init__(self, time_controller: TimeController):
        self.time_controller = time_controller
        self.polling_tasks: List[Dict[str, Any]] = []
        self.simulation_running = False

    def add_polling_task(
        self, task_func: Callable, interval_minutes: int, name: Optional[str] = None
    ):
        """Add a polling task to simulate."""
        self.polling_tasks.append(
            {
                "function": task_func,
                "interval": timedelta(minutes=interval_minutes),
                "last_run": None,
                "name": name or f"task_{len(self.polling_tasks)}",
            }
        )

    async def simulate_polling_cycle(
        self, duration_minutes: int = 60, time_step_minutes: int = 1
    ):
        """Simulate polling for a specified duration with time acceleration."""
        self.simulation_running = True
        start_time = self.time_controller.current_time
        end_time = start_time + timedelta(minutes=duration_minutes)

        logger.info(f"Starting polling simulation from {start_time} to {end_time}")

        polling_cycles = 0

        while self.time_controller.current_time < end_time and self.simulation_running:
            # Check if any tasks should run
            for task in self.polling_tasks:
                should_run = False

                if task["last_run"] is None:
                    # First run
                    should_run = True
                else:
                    # Check if interval has passed
                    time_since_last = (
                        self.time_controller.current_time - task["last_run"]
                    )
                    if time_since_last >= task["interval"]:
                        should_run = True

                if should_run:
                    polling_cycles += 1
                    logger.debug(
                        f"Running polling task: {task['name']} (cycle {polling_cycles})"
                    )
                    try:
                        if asyncio.iscoroutinefunction(task["function"]):
                            await task["function"]()
                        else:
                            task["function"]()
                        task["last_run"] = self.time_controller.current_time
                    except Exception as e:
                        logger.error(f"Error in polling task {task['name']}: {e}")

            # Advance time
            self.time_controller.advance_minutes(time_step_minutes)

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.001)

        logger.info(
            f"Polling simulation completed at {self.time_controller.current_time} with {polling_cycles} cycles"
        )

        return {
            "polling_cycles": polling_cycles,
            "start_time": start_time,
            "end_time": self.time_controller.current_time,
        }

    def stop_simulation(self):
        """Stop the current simulation."""
        self.simulation_running = False

    def reset_tasks(self):
        """Reset all task timers."""
        for task in self.polling_tasks:
            task["last_run"] = None


class MonitoringSimulator:
    """Specialized simulator for Discord bot monitoring tasks."""

    def __init__(self, time_controller: TimeController, monitor_cog=None):
        self.time_controller = time_controller
        self.monitor_cog = monitor_cog
        self.polling_simulator = PollingSimulator(time_controller)

    async def simulate_monitoring_cycle(
        self,
        duration_minutes: int = 120,
        channels_to_monitor: Optional[List[Any]] = None,
    ):
        """Simulate the monitoring loop for specified channels."""

        # Add the monitor task to polling simulator
        async def monitor_task():
            """Wrapper for the monitor task loop body."""
            if self.monitor_cog and hasattr(self.monitor_cog, "monitor_task_loop"):
                # Get active channels (similar to the real monitor logic)
                active_channels = self.monitor_cog.db.get_active_channels()

                for config in active_channels:
                    # Filter to only specified channels if provided
                    if (
                        channels_to_monitor
                        and config["channel_id"] not in channels_to_monitor
                    ):
                        continue

                    # Check if channel should be polled
                    should_poll = await self.monitor_cog._should_poll_channel(config)
                    if should_poll:
                        await self.monitor_cog.run_checks_for_channel(
                            config["channel_id"], config, is_manual_check=False
                        )

        # If we have a monitor cog, use it; otherwise just simulate timing
        if self.monitor_cog:
            self.polling_simulator.add_polling_task(monitor_task, 1, "monitor_loop")
        else:
            # Simple placeholder task for timing simulation
            async def placeholder_task():
                logger.debug("Placeholder monitoring task executed")

            self.polling_simulator.add_polling_task(
                placeholder_task, 30, "placeholder_monitor"
            )

        # Run the simulation
        result = await self.polling_simulator.simulate_polling_cycle(
            duration_minutes=duration_minutes, time_step_minutes=1
        )

        return result


class DatabaseTimeHelper:
    """Helper for managing time-related database operations during testing."""

    def __init__(self, database, time_controller: TimeController):
        self.database = database
        self.time_controller = time_controller

    def set_channel_last_poll_time(self, channel_id: int, minutes_ago: int):
        """Set the last poll time for a channel to a specific time in the past."""
        past_time = self.time_controller.current_time - timedelta(minutes=minutes_ago)
        if hasattr(self.database, "update_channel_last_poll_time"):
            self.database.update_channel_last_poll_time(channel_id, past_time)

    def set_target_last_checked_time(self, target_id: int, minutes_ago: int):
        """Set the last checked time for a target."""
        past_time = self.time_controller.current_time - timedelta(minutes=minutes_ago)
        if hasattr(self.database, "update_target_last_checked_time"):
            self.database.update_target_last_checked_time(target_id, past_time)

    def simulate_submission_aging(self, submission_data: list, days_spread: int = 7):
        """Modify submission timestamps to spread them over time."""
        for i, submission in enumerate(submission_data):
            # Spread submissions over the specified number of days
            days_back = (i % days_spread) + 1
            submission_time = self.time_controller.current_time - timedelta(
                days=days_back
            )
            submission["created_at"] = submission_time.isoformat()

        return submission_data


# Convenience functions


def create_time_controller(start_time: Optional[datetime] = None) -> TimeController:
    """Create a time controller with optional start time."""
    controller = TimeController()
    if start_time:
        controller.set_time(start_time)
    return controller


def create_monitoring_simulation(
    monitor_cog: Optional[Any] = None, start_time: Optional[datetime] = None
) -> tuple[TimeController, MonitoringSimulator]:
    """Create a complete monitoring simulation setup."""
    time_controller = create_time_controller(start_time)
    monitoring_sim = MonitoringSimulator(time_controller, monitor_cog)
    return time_controller, monitoring_sim
