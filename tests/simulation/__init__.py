"""
Simulation Testing Framework

This package contains the complete end-to-end simulation testing framework for
the DisPinMap Discord bot, including API mocking, Discord simulation, time
manipulation, and comprehensive user journey testing.
"""

from tests.utils.api_mock import (
    APISimulator,
    create_error_prone_mock,
    create_fast_mock,
    create_realistic_mock,
)
from tests.utils.discord_mock import (
    DiscordSimulator,
    MessageAnalyzer,
    MockChannel,
    MockUser,
    create_basic_simulation,
)
from tests.utils.simulation import (
    SimulationTestFramework,
    create_simulation_framework,
    run_complete_user_journey,
)
from tests.utils.time_mock import (
    MonitoringSimulator,
    TimeController,
    create_time_controller,
)

# Import main framework components for easy access
from .test_user_journeys import (
    TestCityMonitoringJourney,
    TestCompleteUserJourney,
    TestCoordinateMonitoringJourney,
    TestErrorHandlingJourney,
    TestLocationMonitoringJourney,
    TestPeriodicMonitoringBehavior,
    run_journey_test,
)

__all__ = [
    # Test classes
    "TestLocationMonitoringJourney",
    "TestCoordinateMonitoringJourney",
    "TestCityMonitoringJourney",
    "TestCompleteUserJourney",
    "TestErrorHandlingJourney",
    "TestPeriodicMonitoringBehavior",
    # Main framework
    "SimulationTestFramework",
    "run_complete_user_journey",
    "create_simulation_framework",
    "run_journey_test",
    # API mocking
    "APISimulator",
    "create_fast_mock",
    "create_realistic_mock",
    "create_error_prone_mock",
    # Discord simulation
    "DiscordSimulator",
    "MockChannel",
    "MockUser",
    "MessageAnalyzer",
    "create_basic_simulation",
    # Time manipulation
    "TimeController",
    "MonitoringSimulator",
    "create_time_controller",
]
