"""
Shared test utilities package.

This package provides utilities for testing the DisPinMap application,
including database setup, API mocking, test data generation, and custom assertions.
"""

from .api import (
    MockResponse,
    create_autocomplete_response,
    create_error_response,
    create_location_response,
    create_rate_limit_response,
    create_submission_response,
    create_success_response,
    simulate_rate_limit,
)
from .assertions import (
    MockContext,
    assert_api_response,
    assert_coordinates,
    assert_discord_message,
    assert_error_response,
    assert_location_data,
    assert_submission_data,
    assert_timestamp_format,
)
from .db_utils import (
    cleanup_test_database,
    setup_test_database,
    test_db,
    verify_channel_config,
    verify_database_target,
)
from .generators import (
    generate_city_data,
    generate_coordinates,
    generate_error_data,
    generate_location_data,
    generate_submission_data,
    generate_submission_sequence,
)

__all__ = [
    # Database utilities
    "setup_test_database",
    "cleanup_test_database",
    "verify_database_target",
    "verify_channel_config",
    "test_db",
    # API utilities
    "MockResponse",
    "create_rate_limit_response",
    "create_success_response",
    "create_error_response",
    "create_location_response",
    "create_submission_response",
    "create_autocomplete_response",
    "simulate_rate_limit",
    # Test data generators
    "generate_coordinates",
    "generate_location_data",
    "generate_submission_data",
    "generate_city_data",
    "generate_error_data",
    "generate_submission_sequence",
    # Assertion helpers
    "MockContext",
    "assert_discord_message",
    "assert_api_response",
    "assert_error_response",
    "assert_location_data",
    "assert_submission_data",
    "assert_timestamp_format",
    "assert_coordinates",
]
