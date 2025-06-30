# Testing Framework Agent Instructions

## Overview

The DisPinMap test suite follows a **pyramid structure** with three distinct tiers supporting **parallel execution** via strict database isolation:

- **Unit Tests** (`tests/unit/`): Fast, isolated tests with no external dependencies
- **Integration Tests** (`tests/integration/`): Tests with database and API interactions
- **Simulation Tests** (`tests/simulation/`): High-level user journey testing

### Key Features

✅ **Parallel Execution Support** - Each worker gets isolated SQLite database
✅ **Spec-Based Mock Framework** - Interface compliance and early error detection
✅ **Comprehensive API Mocking** - Easy HTTP response mocking with JSON fixtures

## CRITICAL: Mock Specifications Required

**ALL mocks MUST use proper `spec` parameters to enforce interface compliance:**

### Why Use Spec-Based Mocks?

1. **Interface Enforcement**: Prevents access to non-existent attributes/methods
2. **Early Error Detection**: Catches typos and wrong method names during test execution
3. **AsyncMock Compatibility**: Prevents "TypeError: object MagicMock can't be used in 'await' expression"
4. **Type Safety**: Better IDE support and static analysis
5. **Refactoring Safety**: Tests break when real interfaces change

### Mock Requirements

1. **ALWAYS use spec-based factories** from `tests/utils/mock_factories.py`
2. **NEVER use raw `Mock()` or `MagicMock()` without specs**
3. **Use `autospec=True`** for all `@patch` decorators
4. **Validate mock specs** to catch interface violations early

### Factory Functions (REQUIRED)

```python
from tests.utils.mock_factories import (
    create_async_notifier_mock,
    create_discord_context_mock,
    create_database_mock,
    create_bot_mock,
    create_api_client_mock,
)

# Create properly spec'd mocks
mock_notifier = create_async_notifier_mock()
mock_ctx = create_discord_context_mock(user_id=12345, channel_id=67890)
mock_db = create_database_mock()
```

### Examples

```python
# ❌ WRONG - No spec validation
mock_notifier = Mock()
mock_notifier = AsyncMock()  # TypeError on await!

# ✅ CORRECT - Spec-based factory with interface validation
mock_notifier = create_async_notifier_mock()
await mock_notifier.log_and_send("test")

# ❌ WRONG - Basic patching
@patch("requests.get")

# ✅ CORRECT - Autospec patching
@patch("requests.get", autospec=True)
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

**Rationale**: Spec-based mocks catch interface changes at test time, preventing runtime failures and ensuring tests accurately reflect production behavior.

## Test Structure & Patterns

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
from tests.utils.mock_factories import validate_async_mock

mock_notifier = create_async_notifier_mock()
validate_async_mock(mock_notifier, 'log_and_send')
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

```bash
# All tests
pytest

# Parallel execution (faster)
pytest -n auto  # Uses all CPU cores
pytest -n 4     # Uses 4 workers

# Specific tier
pytest tests/unit/           # Unit only
pytest tests/integration/    # Integration only
pytest tests/simulation/     # Simulation only

# With coverage
pytest --cov=src --cov-report=html
```

## Fixture Management

- **API responses** stored in `tests/fixtures/api_responses/`
- **Organized by service**: `pinballmap_search/`, `geocoding/`
- **Use real API data** for accuracy
- **Validate fixtures** with `scripts/run_all_validations.py`

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

## Test Organization

- **Descriptive names**: `test_add_location_with_valid_search_result()`
- **AAA pattern**: Arrange, Act, Assert
- **One concept per test**: Focus on single behavior
- **Clear assertions**: Use specific assertions, not just `assert result`

## Contributing

When adding new tests:

1. **Choose the Right Tier**: Unit for isolated logic, Integration for component interaction, Simulation for user journeys
2. **Use Spec-Based Mocks**: Always use mock factory functions
3. **Follow Naming Conventions**: Descriptive test names with clear intent
4. **Add Documentation**: Document complex test setups and patterns
5. **Validate Coverage**: Ensure new functionality is adequately tested
