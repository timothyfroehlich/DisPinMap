# Testing Framework Agent Instructions

## CRITICAL: Mock Requirements
**YOU MUST use spec-based mocks** - raw Mock() objects will break tests!

Required factories from `tests/utils/mock_factories.py`:
- `create_async_notifier_mock()` - For Notifier class mocks
- `create_database_mock()` - For Database operations
- `create_bot_mock()` - For Discord Bot mocks
- `create_discord_context_mock()` - For Discord Context
- `create_api_client_mock()` - For API clients

## Test Structure (Testing Pyramid)
- **Unit** (`tests/unit/`) - Fast, isolated, everything mocked
- **Integration** (`tests/integration/`) - Real database, mocked APIs
- **Simulation** (`tests/simulation/`) - End-to-end user journeys

## Key Fixtures
- **`db_session`** - Isolated database for each test (parallel execution safe)
- **`api_mocker`** - HTTP response mocking with JSON fixtures
- **Mock factories** - Spec-validated mocks preventing runtime failures

## Common Patterns
```python
# ✅ CORRECT - Use spec-based factory
mock_notifier = create_async_notifier_mock()
await mock_notifier.log_and_send("test")

# ❌ WRONG - Raw mock will fail
mock_notifier = AsyncMock()  # TypeError on await!

# ✅ CORRECT - Database test with isolation
def test_database_operation(db_session):
    session = db_session()
    # Safe to modify database

# ✅ CORRECT - API mocking with fixtures
def test_api_call(api_mocker):
    api_mocker.add_response(
        url_substring="search",
        json_fixture_path="search_results.json"
    )
```

## Running Tests
```bash
# All tests
pytest

# Parallel execution (faster)
pytest -n auto

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

## Common Issues & Solutions
**AsyncMock TypeError**: Use `create_async_notifier_mock()` not raw `AsyncMock()`

**AttributeError on mocks**: Mock spec enforces real interface - method doesn't exist

**Test interference**: Use `db_session` fixture for database isolation

**Slow tests**: Check if using unit vs integration patterns correctly

## Test Organization
- **Descriptive names**: `test_add_location_with_valid_search_result()`
- **AAA pattern**: Arrange, Act, Assert
- **One concept per test**: Focus on single behavior
- **Clear assertions**: Use specific assertions, not just `assert result`

Read `tests/README.md` for comprehensive testing guide.
