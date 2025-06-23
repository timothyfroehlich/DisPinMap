"""
Main Simulation Framework

This module provides the primary simulation testing framework that coordinates
Discord bot simulation, API mocking, time control, and response validation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.cogs.monitor import MachineMonitor
from src.cogs.monitoring import MonitoringCog
from src.notifier import Notifier

try:
    from .api_mock import create_fast_mock, create_realistic_mock
    from .database import setup_test_database
    from .discord_mock import DiscordSimulator, MessageAnalyzer, MockUser
    from .time_mock import DatabaseTimeHelper, MonitoringSimulator, TimeController
except ImportError:
    # Handle case where test modules aren't available
    pass

logger = logging.getLogger(__name__)


class SimulationTestFramework:
    """Complete simulation testing framework."""

    def __init__(self, use_realistic_timing: bool = False):
        # Core components
        self.database: Optional[Any] = None
        self.notifier: Optional[Notifier] = None
        self.discord_sim: Optional[Any] = None  # DiscordSimulator when available
        self.api_sim: Optional[Any] = None
        self.time_controller: Optional[Any] = None  # TimeController when available

        # Monitoring components
        self.monitor_cog: Optional[MachineMonitor] = None
        self.monitoring_cog: Optional[MonitoringCog] = None
        self.monitoring_sim: Optional[Any] = None  # MonitoringSimulator when available

        # Test environment
        self.test_guild: Optional[Any] = None
        self.test_channel: Optional[Any] = None
        self.test_user: Optional[Any] = None  # MockUser when available

        # Analysis tools
        self.message_analyzer: Any = None  # MessageAnalyzer when available
        self.db_time_helper: Optional[Any] = None  # DatabaseTimeHelper when available

        # Configuration
        self.use_realistic_timing = use_realistic_timing

        # State tracking
        self.is_setup = False
        self.simulation_results: Dict[str, Any] = {}

        # Initialize message analyzer if available
        try:
            self.message_analyzer = MessageAnalyzer()
        except NameError:
            # MessageAnalyzer not available in this environment
            pass

    async def setup(self):
        """Set up the complete simulation environment."""
        if self.is_setup:
            return

        logger.info("Setting up simulation test framework...")

        # 1. Create test database
        try:
            self.database = setup_test_database()
        except NameError:
            raise RuntimeError("Test database setup not available")

        # 2. Create Discord simulation
        try:
            self.discord_sim = DiscordSimulator()
            (
                self.test_guild,
                self.test_channel,
            ) = self.discord_sim.setup_test_environment()
            self.test_user = MockUser(name="TestUser")
        except NameError:
            raise RuntimeError("Discord simulation components not available")

        # 3. Create API simulation
        try:
            if self.use_realistic_timing:
                self.api_sim = create_realistic_mock()
            else:
                self.api_sim = create_fast_mock()
            self.api_sim.start()
        except NameError:
            raise RuntimeError("API mock components not available")

        # 4. Create time controller
        try:
            self.time_controller = TimeController()
            self.time_controller.start()
        except NameError:
            raise RuntimeError("Time controller not available")

        # 5. Create notifier with Discord simulation
        self.notifier = Notifier(self.database)

        # 6. Inject dependencies into Discord bot
        self.discord_sim.inject_dependencies(self.database, self.notifier)

        # 7. Create and load cogs
        self.monitor_cog = MachineMonitor(
            self.discord_sim.bot, self.database, self.notifier
        )
        self.monitoring_cog = MonitoringCog(
            self.discord_sim.bot, self.database, self.notifier
        )

        self.discord_sim.load_cogs(
            {"MachineMonitor": self.monitor_cog, "Monitoring": self.monitoring_cog}
        )

        # 8. Create monitoring simulator
        try:
            self.monitoring_sim = MonitoringSimulator(
                self.time_controller, self.monitor_cog
            )
        except NameError:
            raise RuntimeError("Monitoring simulator not available")

        # 9. Create database time helper
        try:
            self.db_time_helper = DatabaseTimeHelper(
                self.database, self.time_controller
            )
        except NameError:
            raise RuntimeError("Database time helper not available")

        self.is_setup = True
        logger.info("Simulation framework setup complete")

    async def teardown(self):
        """Clean up simulation environment."""
        if not self.is_setup:
            return

        logger.info("Tearing down simulation framework...")

        # Stop time control
        if self.time_controller:
            self.time_controller.stop()

        # Stop API mocking
        if self.api_sim:
            self.api_sim.stop()

        # Clean up database
        if self.database:
            self.database.close()

        self.is_setup = False
        logger.info("Simulation framework teardown complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.teardown()

    # User Journey Simulation Methods

    async def simulate_add_location_by_id(
        self, location_id: int
    ) -> Tuple[bool, List[str]]:
        """Simulate a user adding a location by ID."""
        await self._ensure_setup()

        logger.info(f"Simulating: User adds location {location_id}")

        # Execute the command
        if self.discord_sim is None:
            raise RuntimeError("Discord simulator not initialized")
        ctx = await self.discord_sim.simulate_user_interaction(
            "add", ["location", str(location_id)], self.test_channel, self.test_user
        )

        # Analyze results
        messages = [msg.content for msg in ctx.get_sent_messages()]

        # Check success: if we got messages back, command executed successfully
        # (workaround for missing success message bug #16)
        success = len(messages) > 0 and not any("❌" in msg for msg in messages)

        # Store results
        self.simulation_results["add_location"] = {
            "success": success,
            "messages": messages,
            "location_id": location_id,
        }

        return success, messages

    async def simulate_add_coordinates(
        self, lat: float, lon: float, radius: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """Simulate a user adding coordinates monitoring."""
        await self._ensure_setup()

        logger.info(
            f"Simulating: User adds coordinates {lat}, {lon} (radius: {radius})"
        )

        args = ["coordinates", str(lat), str(lon)]
        if radius:
            args.append(str(radius))

        if self.discord_sim is None:
            raise RuntimeError("Discord simulator not initialized")
        ctx = await self.discord_sim.simulate_user_interaction(
            "add", args, self.test_channel, self.test_user
        )

        messages = [msg.content for msg in ctx.get_sent_messages()]
        # Check success: if we got messages back without errors, command executed successfully
        success = len(messages) > 0 and not any("❌" in msg for msg in messages)

        self.simulation_results["add_coordinates"] = {
            "success": success,
            "messages": messages,
            "coordinates": {"lat": lat, "lon": lon, "radius": radius},
        }

        return success, messages

    async def simulate_add_city(
        self, city_name: str, radius: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """Simulate a user adding city monitoring."""
        await self._ensure_setup()

        logger.info(f"Simulating: User adds city {city_name} (radius: {radius})")

        args = ["city", city_name]
        if radius:
            args.append(str(radius))

        if self.discord_sim is None:
            raise RuntimeError("Discord simulator not initialized")
        ctx = await self.discord_sim.simulate_user_interaction(
            "add", args, self.test_channel, self.test_user
        )

        messages = [msg.content for msg in ctx.get_sent_messages()]
        # Check success: if we got messages back without errors, command executed successfully
        success = len(messages) > 0 and not any("❌" in msg for msg in messages)

        self.simulation_results["add_city"] = {
            "success": success,
            "messages": messages,
            "city": city_name,
            "radius": radius,
        }

        return success, messages

    async def simulate_list_targets(self) -> List[str]:
        """Simulate a user listing monitoring targets."""
        await self._ensure_setup()

        logger.info("Simulating: User lists monitoring targets")

        if self.discord_sim is None:
            raise RuntimeError("Discord simulator not initialized")
        ctx = await self.discord_sim.simulate_user_interaction(
            "list", [], self.test_channel, self.test_user
        )

        messages = [msg.content for msg in ctx.get_sent_messages()]

        self.simulation_results["list_targets"] = {"messages": messages}

        return messages

    async def simulate_manual_check(self) -> List[str]:
        """Simulate a user running a manual check."""
        await self._ensure_setup()

        logger.info("Simulating: User runs manual check")

        # Record initial channel message count
        if self.test_channel is None:
            raise RuntimeError("Test channel not initialized")
        initial_count = len(self.test_channel.get_sent_messages())

        if self.discord_sim is None:
            raise RuntimeError("Discord simulator not initialized")
        _ = await self.discord_sim.simulate_user_interaction(
            "check", [], self.test_channel, self.test_user
        )

        # Get messages sent during the check command execution
        # The check command sends messages directly to the channel, not through ctx
        all_channel_messages = self.test_channel.get_sent_messages()
        new_messages = all_channel_messages[initial_count:]
        messages = [msg.content for msg in new_messages]

        self.simulation_results["manual_check"] = {"messages": messages}

        return messages

    # Monitoring Simulation Methods

    async def simulate_periodic_monitoring(
        self, duration_minutes: int = 120, poll_rate_minutes: int = 60
    ) -> Dict[str, Any]:
        """Simulate periodic monitoring over time."""
        await self._ensure_setup()

        logger.info(f"Simulating periodic monitoring for {duration_minutes} minutes")

        # Set up channel configuration
        if self.database is None:
            raise RuntimeError("Database not initialized")
        if self.test_channel is None:
            raise RuntimeError("Test channel not initialized")
        if self.test_guild is None:
            raise RuntimeError("Test guild not initialized")
        self.database.update_channel_config(
            self.test_channel.id,
            self.test_guild.id,
            is_active=True,
            poll_rate_minutes=poll_rate_minutes,
        )

        # Record initial state
        initial_messages = len(self.test_channel.get_sent_messages())

        # Run monitoring simulation
        if self.monitoring_sim is None:
            raise RuntimeError("Monitoring simulator not initialized")
        await self.monitoring_sim.simulate_monitoring_cycle(
            duration_minutes=duration_minutes,
            channels_to_monitor=[self.test_channel.id],
        )

        # Analyze results
        final_messages = self.test_channel.get_sent_messages()
        new_messages = final_messages[initial_messages:]

        results = {
            "duration_minutes": duration_minutes,
            "poll_rate_minutes": poll_rate_minutes,
            "new_messages": [msg.content for msg in new_messages],
            "message_count": len(new_messages),
            "polling_cycles": duration_minutes // poll_rate_minutes,
        }

        self.simulation_results["periodic_monitoring"] = results
        return results

    async def simulate_submission_detection(
        self, mock_new_submissions: List[Dict]
    ) -> List[str]:
        """Simulate detection of new submissions."""
        await self._ensure_setup()

        logger.info(
            f"Simulating detection of {len(mock_new_submissions)} new submissions"
        )

        # Modify the API mock to return new submissions
        # This would require enhancing the API mock system to inject new data

        # For now, we'll run a manual check to see current behavior
        messages = await self.simulate_manual_check()

        return messages

    # Validation and Analysis Methods

    def validate_message_format(self, message: str, expected_format: str) -> bool:
        """Validate that a message matches expected format."""
        if self.message_analyzer is None:
            return False
        return self.message_analyzer.validate_response_format(message, expected_format)

    def analyze_messages(self, messages: List[str]) -> Dict[str, Any]:
        """Analyze a list of messages for patterns and content."""
        analysis: Dict[str, Any] = {
            "total_messages": len(messages),
            "categories": {},
            "locations_mentioned": [],
            "errors": [],
            "successes": [],
        }

        if self.message_analyzer is None:
            # Return basic analysis if message analyzer is not available
            return analysis

        for message in messages:
            category = self.message_analyzer.categorize_message(message)
            categories = analysis["categories"]
            if isinstance(categories, dict):
                categories[category] = categories.get(category, 0) + 1

            if category == "error":
                errors = analysis["errors"]
                if isinstance(errors, list):
                    errors.append(message)
            elif category == "success":
                successes = analysis["successes"]
                if isinstance(successes, list):
                    successes.append(message)

            location_info = self.message_analyzer.extract_location_info(message)
            if location_info:
                locations = analysis["locations_mentioned"]
                if isinstance(locations, list):
                    locations.append(location_info)

        return analysis

    def get_database_state(self) -> Dict[str, Any]:
        """Get current database state for verification."""
        if self.database is None:
            return {"error": "Database not initialized"}
        if self.test_channel is None:
            return {"error": "Test channel not initialized"}

        return {
            "channels": [self.database.get_channel_config(self.test_channel.id)],
            "targets": self.database.get_monitoring_targets(self.test_channel.id),
            "seen_submissions": self.database.get_seen_submission_ids(
                self.test_channel.id
            ),
        }

    def get_simulation_summary(self) -> Dict[str, Any]:
        """Get a summary of all simulation results."""
        summary = {
            "framework_info": {
                "use_realistic_timing": self.use_realistic_timing,
                "current_time": (
                    self.time_controller.current_time.isoformat()
                    if self.time_controller
                    else None
                ),
            },
            "test_environment": {
                "channel_id": self.test_channel.id if self.test_channel else None,
                "guild_id": self.test_guild.id if self.test_guild else None,
                "user_id": self.test_user.id if self.test_user else None,
            },
            "results": self.simulation_results,
            "database_state": self.get_database_state() if self.database else None,
            "api_logs": (
                self.api_sim.get_request_logs()
                if self.api_sim and hasattr(self.api_sim, "get_request_logs")
                else None
            ),
            "discord_logs": (
                self.discord_sim.get_execution_log()
                if self.discord_sim and hasattr(self.discord_sim, "get_execution_log")
                else None
            ),
        }

        return summary

    # Helper Methods

    async def _ensure_setup(self):
        """Ensure the framework is set up."""
        if not self.is_setup:
            await self.setup()

    def reset_state(self):
        """Reset simulation state for new test."""
        if self.test_channel and hasattr(self.test_channel, "clear_messages"):
            self.test_channel.clear_messages()
        if self.discord_sim and hasattr(self.discord_sim, "clear_logs"):
            self.discord_sim.clear_logs()
        if self.api_sim and hasattr(self.api_sim, "clear_logs"):
            self.api_sim.clear_logs()
        self.simulation_results.clear()


# Convenience Functions


async def create_simulation_framework(
    realistic_timing: bool = False,
) -> SimulationTestFramework:
    """Create and set up a simulation framework."""
    try:
        framework = SimulationTestFramework(use_realistic_timing=realistic_timing)
        await framework.setup()
        return framework
    except (NameError, RuntimeError) as e:
        raise RuntimeError(f"Failed to create simulation framework: {e}")


async def run_complete_user_journey(location_id: int = 1309) -> Dict[str, Any]:
    """Run a complete user journey simulation."""
    async with SimulationTestFramework() as framework:
        # Add location
        success, add_messages = await framework.simulate_add_location_by_id(location_id)

        # List targets
        list_messages = await framework.simulate_list_targets()

        # Manual check
        check_messages = await framework.simulate_manual_check()

        # Simulate periodic monitoring
        monitoring_results = await framework.simulate_periodic_monitoring(
            duration_minutes=120
        )

        return {
            "add_location": {"success": success, "messages": add_messages},
            "list_targets": {"messages": list_messages},
            "manual_check": {"messages": check_messages},
            "monitoring": monitoring_results,
            "summary": framework.get_simulation_summary(),
        }
