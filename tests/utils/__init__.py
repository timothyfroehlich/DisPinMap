"""
Shared test utilities package.

This package provides utilities for testing the DisPinMap application,
including database setup, API mocking, test data generation, and custom assertions.
"""

from .database import (
    setup_test_database,
    cleanup_test_database,
    verify_database_target,
    verify_channel_config,
    test_db
)

from .api import (
    MockResponse,
    create_rate_limit_response,
    create_success_response,
    create_error_response,
    create_location_response,
    create_submission_response,
    create_autocomplete_response,
    simulate_rate_limit
)

from .generators import (
    generate_coordinates,
    generate_location_data,
    generate_submission_data,
    generate_city_data,
    generate_error_data,
    generate_submission_sequence
)

from .assertions import (
    MockContext,
    assert_discord_message,
    assert_api_response,
    assert_error_response,
    assert_location_data,
    assert_submission_data,
    assert_timestamp_format,
    assert_coordinates
)

__all__ = [
    # Database utilities
    'setup_test_database',
    'cleanup_test_database',
    'verify_database_target',
    'verify_channel_config',
    'test_db',

    # API utilities
    'MockResponse',
    'create_rate_limit_response',
    'create_success_response',
    'create_error_response',
    'create_location_response',
    'create_submission_response',
    'create_autocomplete_response',
    'simulate_rate_limit',

    # Test data generators
    'generate_coordinates',
    'generate_location_data',
    'generate_submission_data',
    'generate_city_data',
    'generate_error_data',
    'generate_submission_sequence',

    # Assertion helpers
    'MockContext',
    'assert_discord_message',
    'assert_api_response',
    'assert_error_response',
    'assert_location_data',
    'assert_submission_data',
    'assert_timestamp_format',
    'assert_coordinates'
]
