# Testing Framework Refactor: Detailed Plan

This document provides a detailed, actionable plan for refactoring the `DisPinMap` test suite, as outlined in [GitHub Issue #51](https://github.com/timothyfroehlich/DisPinMap/issues/51).

## 1. Core Principles & Strategy

The refactor will be guided by the following principles:

- **Pyramid Structure:** Tests will be organized into `unit`, `integration`, and `simulation` tiers.
- **Parallel Execution:** The primary goal is to enable parallel test runs via `pytest-xdist`. This will be achieved through strict database isolation.
- **Dependency Isolation:**
    - **Unit Tests:** Will have NO external dependencies (database, network). All I/O will be mocked.
    - **Integration Tests:** Will connect to a real, but temporary and isolated, database. Network calls will be mocked using the existing fixtures in `tests/fixtures/api_responses/`.
- **Clarity and Simplicity:** The structure will be intuitive, removing ambiguity and making it easy for developers to add new tests in the correct location.

## 2. New Directory Structure

The current `tests/` directory will be moved to `tests_backup/`. A new `tests/` directory will be created with the following structure:

```
tests/
├── conftest.py             # Core fixtures: DB isolation, mock setup
├── unit/
│   ├── __init__.py
│   ├── test_api_client.py      # Tests for src/api.py logic (not network)
│   ├── test_commands_parsing.py # Tests for command argument parsing
│   ├── test_database_models.py # Tests for model logic (not DB interaction)
│   └── test_message_formatting.py # Tests for src/messages.py
├── integration/
│   ├── __init__.py
│   ├── test_api_contracts.py   # Tests against saved API responses
│   ├── test_commands_e2e.py    # Full command logic against isolated DB
│   ├── test_database_crud.py   # CRUD operations against isolated DB
│   └── test_monitoring_e2e.py  # Full monitoring loop against isolated DB
├── simulation/
│   ├── __init__.py
│   └── test_user_journeys.py   # High-level user story simulations
└── utils/
    ├── __init__.py
    ├── api_mocker.py           # Utility to load and mock API responses
    └── db_helpers.py           # Helper functions for test database interactions
```

## 3. Core Infrastructure (`conftest.py`)

This file will contain the foundational fixtures for the entire test suite.

- **`db_session` fixture (session-scoped):**
    - **Logic:**
        1.  Check for the `worker_id` from `pytest-xdist`.
        2.  If a worker, create a unique, temporary SQLite database file for that worker (e.g., `test_db_gw0.sqlite`).
        3.  If not a worker (master process), create a default `test_db.sqlite`.
        4.  Create a SQLAlchemy engine and session factory for that unique database.
        5.  `yield` the session factory to the tests.
        6.  After the test session for that worker completes, tear down the engine and delete the temporary database file.
    - **Benefit:** This is the key to enabling parallel execution. Each test process will be completely isolated at the database level.

- **`api_mocker` fixture:**
    - **Logic:** A fixture that provides a simple interface to mock `aiohttp` requests, loading response data from the `tests/fixtures/api_responses/` directory. This will be used heavily in integration tests.

## 4. Scaffolding Plan: From Old to New

This section maps the old test files to their new homes. The new files will be created with comments outlining the specific tests to be migrated into them.

### `tests_backup/` -> `tests/unit/`

| New File                      | Purpose                                        | Original Tests To Be Migrated From                                                                    |
| ----------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `test_api_client.py`          | Tests parsing/logic of API clients.            | `unit/test_api.py`, `unit/test_geocoding_api.py`                                                        |
| `test_commands_parsing.py`    | Tests parsing of command arguments only.       | Parts of `func/test_commands.py` (e.g., handling of invalid arguments).                                 |
| `test_database_models.py`     | Tests model methods and properties.            | `unit/test_add_target_behavior.py` (logic part, not DB part)                                            |
| `test_message_formatting.py`  | Tests message creation and formatting.         | `enhanced/test_message_formatting_issues.py`                                                            |

### `tests_backup/` -> `tests/integration/`

| New File                   | Purpose                                                   | Original Tests To Be Migrated From                                                                                                      |
| -------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `test_api_contracts.py`    | Tests that the bot can correctly handle saved API data.     | `integration/test_geocoding_api_integration.py`, `integration/test_pinballmap_api.py`                                                     |
| `test_commands_e2e.py`     | Tests full command flows against an isolated DB.          | `func/test_commands.py`, `integration/test_commands_integration.py`, `unit/test_add_target_behavior.py`, `unit/test_manual_check_behavior.py` |
| `test_database_crud.py`    | Tests direct database interactions (add, remove, update). | `unit/test_database.py` (the entire file, as it was an integration test).                                                               |
| `test_monitoring_e2e.py`   | Tests the full monitoring loop from start to finish.        | `enhanced/test_integration_background_tasks.py`, `enhanced/test_task_loop_failures.py`, `func/test_monitor_task_loop_lifecycle.py`       |

### `tests_backup/` -> `tests/simulation/`

| New File                | Purpose                                | Original Tests To Be Migrated From                     |
| ----------------------- | -------------------------------------- | ------------------------------------------------------ |
| `test_user_journeys.py` | High-level, multi-step user scenarios. | `simulation/test_user_journeys.py` (can likely be moved with minimal changes). `enhanced/test_simulation_framework_analysis.py` contains useful concepts but won't be a direct migration. |

## 5. Implementation Steps

1.  **Backup:** Execute `mv tests tests_backup`.
2.  **Create Structure:** Create the new directory structure as defined above.
3.  **Implement `conftest.py`:** Create the core `db_session` fixture. This is the most critical step and must be done first.
4.  **Scaffold Files:** Create each new test file, populating it with comments outlining the tests it will contain, referencing the original test file/function it replaces. For example, in `tests/integration/test_database_crud.py`:
    ```python
    # Placeholder for tests migrated from tests_backup/unit/test_database.py

    def test_duplicate_target_addition(db_session):
        # Re-implements TestDatabaseEdgeCases.test_duplicate_target_addition
        # 1. Add a target.
        # 2. Assert that adding the same target again raises an IntegrityError.
        pass

    def test_remove_nonexistent_target(db_session):
        # Re-implements TestDatabaseEdgeCases.test_remove_nonexistent_target
        pass

    # ... and so on for all tests in the original file.
    ```
5.  **Iterative Implementation:** After scaffolding, the tests can be implemented, file by file. This work can be parallelized among multiple developers (or agents).
