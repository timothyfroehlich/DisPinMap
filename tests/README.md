# DisPinMap Test Framework

This document describes the testing framework architecture and best practices for the DisPinMap project.

## Overview

The DisPinMap test suite follows a **pyramid structure** with three distinct tiers:

- **Unit Tests** (`tests/unit/`): Fast, isolated tests with no external dependencies
- **Integration Tests** (`tests/integration/`): Tests with database and API interactions
- **Simulation Tests** (`tests/simulation/`): High-level user journey testing

## Key Features

### ✅ Parallel Execution Support
The framework supports parallel test execution via `pytest-xdist` through strict database isolation. Each worker gets its own temporary SQLite database.

### ✅ Spec-Based Mock Framework
All mocks use `unittest.mock` `spec` parameters for interface compliance and early error detection.

### ✅ Comprehensive API Mocking
The `api_mocker` fixture provides easy HTTP response mocking using saved JSON fixtures.

## Spec-Based Mock Framework

### Why Use `spec` Parameters?

The `spec` parameter in `unittest.mock` provides several critical benefits:

1. **Interface Enforcement**: Prevents access to non-existent attributes/methods
2. **Early Error Detection**: Catches typos and wrong method names during test execution
3. **AsyncMock Compatibility**: Prevents "TypeError: object MagicMock can't be used in 'await' expression"
4. **Type Safety**: Better IDE support and static analysis
5. **Refactoring Safety**: Tests break when real interfaces change

### Mock Factory Functions

All mocks should be created using the factory functions in `tests/utils/mock_factories.py`:

#### Core Mock Factories

```python
from tests.utils.mock_factories import (
    create_async_notifier_mock,
    create_discord_context_mock,
    create_database_mock,
    create_bot_mock,
    create_api_client_mock,
)

# Create a properly spec'd notifier mock
mock_notifier = create_async_notifier_mock()

# Create a Discord context mock with proper specs
mock_ctx = create_discord_context_mock(user_id=12345, channel_id=67890)

# Create a database mock
mock_db = create_database_mock()
```

#### Validation Utilities

```python
from tests.utils.mock_factories import validate_async_mock, validate_mock_spec

# Validate that an async mock is properly awaitable
validate_async_mock(mock_notifier, 'log_and_send')

# Validate that a mock has the expected spec
validate_mock_spec(mock_notifier, Notifier)
```

### Migration from Legacy Mocks

**❌ Old Pattern (Deprecated):**
```python
from unittest.mock import AsyncMock, MagicMock

# Raw mock without spec - dangerous!
mock_notifier = AsyncMock()
mock_ctx = MagicMock()
```

**✅ New Pattern (Recommended):**
```python
from tests.utils.mock_factories import create_async_notifier_mock, create_discord_context_mock

# Spec-validated mocks with interface enforcement
mock_notifier = create_async_notifier_mock()
mock_ctx = create_discord_context_mock()
```

## Test Structure and Patterns

### Unit Tests (`tests/unit/`)

- **Purpose**: Test individual functions/classes in isolation
- **Dependencies**: None (all external dependencies mocked)
- **Speed**: Very fast (< 1s per test)
- **Patterns**: Use spec-based mocks for all external dependencies

```python
def test_notifier_log_and_send(mock_database):
    """Test notifier functionality with mocked database."""
    notifier = Notifier(mock_database)
    # Test the logic without real database
```

### Integration Tests (`tests/integration/`)

- **Purpose**: Test component interactions with real database
- **Dependencies**: Isolated test database, mocked external APIs
- **Speed**: Moderate (1-5s per test)
- **Patterns**: Use `db_session` fixture and `api_mocker`

```python
@pytest.mark.asyncio
async def test_add_command_end_to_end(db_session, api_mocker):
    """Test full command flow with database and mocked APIs."""
    # Configure API responses
    api_mocker.add_response(
        url_substring="search_endpoint",
        json_fixture_path="search_results.json"
    )

    # Test with real database but mocked APIs
    result = await execute_command(db_session)
```

### Simulation Tests (`tests/simulation/`)

- **Purpose**: Test complete user journeys and workflows
- **Dependencies**: Full test environment with all components
- **Speed**: Slower (5-30s per test)
- **Patterns**: Multi-step scenarios, end-to-end validation

## Core Fixtures

### Database Isolation (`db_session`)

The `db_session` fixture provides isolated database sessions for parallel testing:

```python
def test_database_operations(db_session):
    """Test with isolated database session."""
    session = db_session()
    target = MonitoringTarget(name="test")
    session.add(target)
    session.commit()
    # Each test gets its own database
```

### API Mocking (`api_mocker`)

The `api_mocker` fixture enables easy HTTP response mocking:

```python
def test_api_integration(api_mocker):
    """Test with mocked API responses."""
    api_mocker.add_response(
        url_substring="api.example.com/search",
        json_fixture_path="search_response.json",
        status=200
    )
    # API calls will return the fixture data
```

## Best Practices

### ✅ DO: Use Spec-Based Mocks
```python
# Always use factory functions
mock_notifier = create_async_notifier_mock()
```

### ❌ DON'T: Use Raw Mocks
```python
# Avoid raw mocks without specs
mock_notifier = AsyncMock()  # No interface enforcement!
```

### ✅ DO: Validate Async Mocks
```python
mock_notifier = create_async_notifier_mock()
validate_async_mock(mock_notifier, 'log_and_send')
```

### ✅ DO: Use Descriptive Test Names
```python
def test_add_location_command_with_valid_search_result():
    """Test the add location command when API returns valid results."""
```

### ✅ DO: Follow AAA Pattern
```python
def test_example():
    # 1. ARRANGE: Set up test data and mocks
    mock_notifier = create_async_notifier_mock()

    # 2. ACT: Execute the code under test
    result = await function_under_test(mock_notifier)

    # 3. ASSERT: Verify the expected behavior
    assert result.success is True
    mock_notifier.log_and_send.assert_called_once()
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Tests in Parallel
```bash
pytest -n auto  # Uses all CPU cores
pytest -n 4     # Uses 4 workers
```

### Run Specific Test Tiers
```bash
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest tests/simulation/     # Simulation tests only
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html
```

## Troubleshooting

### AsyncMock Issues

**Problem**: `TypeError: object MagicMock can't be used in 'await' expression`

**Solution**: Use spec-based mock factories:
```python
# ❌ Problem
mock = MagicMock()
await mock.some_method()  # TypeError!

# ✅ Solution
mock = create_async_notifier_mock()
await mock.log_and_send()  # Works!
```

### Mock Attribute Errors

**Problem**: `AttributeError: Mock object has no attribute 'method_name'`

**Solution**: Check the spec and ensure method exists on real class:
```python
# The mock spec enforces real interface
mock = create_async_notifier_mock()
mock.nonexistent_method()  # AttributeError - good!
mock.log_and_send()        # Works - method exists
```

### Database Isolation Issues

**Problem**: Tests interfere with each other

**Solution**: Ensure using `db_session` fixture:
```python
def test_database_operation(db_session):
    """Each test gets isolated database."""
    session = db_session()
    # Safe to modify database
```

## Contributing

When adding new tests:

1. **Choose the Right Tier**: Unit for isolated logic, Integration for component interaction, Simulation for user journeys
2. **Use Spec-Based Mocks**: Always use mock factory functions
3. **Follow Naming Conventions**: Descriptive test names with clear intent
4. **Add Documentation**: Document complex test setups and patterns
5. **Validate Coverage**: Ensure new functionality is adequately tested

## Future Improvements

- [ ] Add property-based testing with Hypothesis
- [ ] Implement mutation testing for test quality validation
- [ ] Add performance benchmarking for critical paths
- [ ] Enhance API fixture management and versioning
