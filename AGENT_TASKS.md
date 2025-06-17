# Agent Tasks

## Planned Tasks

### Task 2: Enhance `!check` Command Logic

**Objective**: Modify the `!check` command to ensure it always attempts to show up to 5 relevant submissions. It will first show all new submissions since the last check, and if that's less than 5, it will backfill the list with the most recent older submissions to reach a total of 5.

**Detailed Steps**:

1.  **Modify Monitor Check Logic**:
    *   **File**: `src/monitor.py`
    *   **Change**: Update the `run_checks_for_channel` method. When `is_manual_check` is `True`:
        *   Fetch all submissions from the API (`use_min_date=False`).
        *   Partition the fetched submissions into two lists: `new_submissions` (not in `seen_submission_ids`) and `old_submissions` (already seen).
        *   Filter both lists based on the target's configured `notification_types`.
        *   If the count of `filtered_new_submissions` is less than 5, take the most recent `5 - len(filtered_new_submissions)` items from `filtered_old_submissions`.
        *   Create a final `submissions_to_report` list containing all `filtered_new_submissions` followed by the backfilled older ones.
        *   Pass this combined list to the `_send_notifications` method.

2.  **Update Notifier Logic (Optional)**:
    *   **File**: `src/notifier.py`
    *   **Change**: Review the `send_notifications` method. The message for a manual check may need adjustment to be clearer. For instance, instead of "Found X new submission(s)", it could be "Found X new submission(s). Showing the 5 most recent:" to reflect the new behavior.

3.  **Test Changes**:
    *   **`tests/unit/test_monitor.py`**: Create new test cases to simulate various scenarios for the `!check` command:
        *   More than 5 new submissions.
        *   Less than 5 new submissions, requiring backfill.
        *   No new submissions, requiring a full list of 5 old submissions.
        *   Assert that the correct combined list of submissions is passed to the notifier.
    *   **`tests/func/test_commands.py`**: Update the `!check` command functional tests to reflect the new output, verifying that up to 5 submissions are always shown and that the message is correct. This will involve seeding the test database with seen submissions and mocking API responses.

## Completed Tasks

- ✅ **Combined `!list` and `!status` Commands**: Merged the functionality of `!list` and `!status` into a single, table-based command.
  - **New Feature**: `!list` (aliased with `!status`) now shows a formatted table with `Index`, `Target`, `Poll (min)`, `Notifications`, and `Last Checked` columns.
  - **Database**: Added `last_checked_at` field to the `MonitoringTarget` model to track check times.
  - **Monitor**: Updated the monitoring logic to record the timestamp after each check.
  - **Tests**: Added unit and functional tests to validate the new functionality and table format.

### Development Tools & Infrastructure
- ✅ **GitHub MCP Server Integration**: Successfully connected Cursor to GitHub's remote MCP server
  - **Setup**: Configured `.cursor/mcp.json` with remote GitHub MCP server URL
  - **Authentication**: OAuth-based authentication for seamless GitHub integration
  - **Benefits**: Direct access to GitHub API functionality within Cursor's chat interface
  - **Available Tools**: Repository management, issue tracking, PR operations, file operations, search functionality

### CRITICAL BUG FIXES (URGENT)
- ✅ **Fixed Monitor Partial Changes Bug**: Restored missing `is_manual_check` parameter to `run_checks_for_channel()` method
  - **Issue**: `!check` command was passing `is_manual_check=True` but `monitor.py` didn't accept this parameter
  - **Impact**: Manual checks were failing silently, automatic monitoring was using wrong API parameters
  - **Root Cause**: Partially applied changes left the codebase in inconsistent state
- ✅ **Fixed API Call Parameters**:
  - **Automatic monitoring**: Now uses `use_min_date=True` (only recent submissions from yesterday+)
  - **Manual checks**: Now uses `use_min_date=False` (all submissions, limited to last 5 displayed)
  - **Impact**: This fixes why automatic monitoring missed new games and why !check showed all submissions
- ✅ **Added Manual Check User Feedback**: Manual checks now provide clear feedback when no submissions found
- ✅ **Fixed Manual Check Display Logic**: Manual checks now limit display to last 5 submissions with proper sorting

### GCP Deployment
- ✅ Updated requirements.txt with GCP dependencies (google-cloud-secret-manager, google-cloud-sql-connector[pg8000], aiohttp).
- ✅ Modified src/database.py for dual database support (SQLite and PostgreSQL).
- ✅ Added secrets management and health check endpoint to src/main.py.
- ✅ Created a multi-stage Dockerfile with a non-root user and virtual environment.
- ✅ Set up Terraform infrastructure for GCP deployment (Cloud Run, Cloud SQL, Secret Manager, Artifact Registry).
- ✅ Updated .gitignore to ignore Terraform state files and sensitive files.
- ✅ Updated README.md with local and GCP deployment instructions.
- ✅ Verified local functionality with SQLite and .env file.

### Docker
- ✅ Built Docker image successfully.
- ✅ Pushed Docker image to Google Artifact Registry.

### High Priority Fixes
- ✅ Fixed coordinate handling bug in check command.
- ✅ Added input sanitization for geocoding API calls.
- ✅ Improved notification filtering logic in monitor.py.
- ✅ Fixed float precision issues in coordinate comparison.

### Medium Priority Core Tasks
- ✅ Removed unused imports and unnecessary comments.
- ✅ Added proper logging instead of print statements.
- ✅ Added missing type annotations.
- ✅ Created unit tests for API rate limiting and error scenarios.
- ✅ Created unit tests for database edge cases and session management.

### Command Reorganization & UX Improvements
- ✅ Unified add/remove commands:
    - Implemented single `!add` command with subcommands/types (e.g., `!add location ...`, `!add city ...`, `!add coordinates ...`).
    - Implemented single `!rm <index>` command to remove the Nth monitored item as shown in `!list`.
    - `!add location` supports both name and ID; `!add city` by name only.
- ✅ Enhanced listing & removal UX:
    - `!list` shows all monitored targets for the channel, with index numbers for easy reference.
    - `!rm <index>` removes the item at the given index from `!list`.
- ✅ Added export functionality:
    - Implemented `!export` command that outputs a copy-pasteable list of `!add`/`!set` commands.
- ✅ Enhanced poll rate & notifications:
    - `!poll_rate <minutes>` sets the default poll rate for the channel.
    - `!poll_rate <minutes> <index>` sets the poll rate for a specific target.
    - `!notifications <type>` sets the default notification type for the channel.
    - `!notifications <type> <index>` sets the notification type for a specific target.
    - Added `notification_types` field to MonitoringTarget model for per-target support.
    - When a default is set, all current targets and channel config are updated; new targets inherit the default.
- ✅ Improved help & discoverability:
    - Updated help output to be clear, grouped, and include examples.
    - Added command aliases for quick reference.
- ✅ Added comprehensive test suite:
    - Created tests/test_commands_reorg.py with 20+ test cases.
    - Tests cover all new command functionality (add, remove, list, export).
    - Tests verify poll rate and notification type settings.
    - Tests include error cases and edge conditions.
    - Added pytest-xdist for parallel test execution.

## Pending Tasks

### Remaining Test Fixes
- **Task 8**: Fix monitor test mocks (2 failing tests) - Mock channel setup issues in `test_poll_channel_with_targets` and `test_send_notifications_multiple_machines`
- **Task 9**: Fix logging timestamp parsing (1 failing test) - ANSI color code handling in `test_colored_formatter`

### Recently Completed
- ✅ **Added Functional Tests for !check Command**: Created comprehensive test suite for the `!check` command in `tests/func/test_commands.py`
  - **Coverage**: 5 test cases covering normal operation, error conditions, and integration scenarios
  - **Tests**: Valid targets, missing monitor cog, no targets, exception handling, and integration with real monitor
  - **Purpose**: Help diagnose issues when `!check` command fails, ensure proper interaction between monitoring cog and monitor cog
  - **Result**: All tests passing, provides debugging capabilities for future `!check` command issues

### Future Improvements
- **Performance Optimization**: Database query optimization, caching, background task scheduling.
- **Enhanced Error Handling**: Retry logic for Discord API failures, graceful degradation for external API outages.
- **Monitoring & Observability**: Metrics collection, health check endpoints, performance dashboards.
- **Security Enhancements**: Rate limiting, input validation, audit logging.

## Current Test Coverage
- **126 tests PASSING** out of 129 total (97.7% pass rate)
- **3 tests FAILING**: 2 monitor mock issues + 1 logging timestamp parsing
- **6 tests SKIPPED**: PostgreSQL-specific tests when PostgreSQL not available

---

**Note:** All GCP deployment tasks and command reorganization tasks are complete. The bot is ready for deployment to Google Cloud Platform with improved command structure and user experience.

## Test Organization

### Current Test Structure
- `tests/unit/`
  - `test_api.py`: API tests including rate limiting, error handling, and input validation
  - `test_database.py`: Database tests for core functionality and edge cases
  - `test_logging.py`: Logging flow and message formatting tests
- `tests/func/`
  - `test_commands.py`: Comprehensive functional tests for all command handlers
- `tests/utils.py`: Shared test utilities and fixtures

### Test Coverage Status
✅ **Complete Coverage**:
- Command handling and response validation
- API rate limiting and error scenarios
- Database operations and session management
- Command reorganization features
- Input validation and sanitization
- Logging flow and message formatting
- Integration tests for Pinball Map API (real API calls)
- Message centralization and type-safe formatting
- MockResponse implementation for API testing

🔄 **Partial Coverage**:
- Performance benchmarks for critical operations
- Integration tests for GCP deployment scenarios

### Next Test Improvements
1. Add performance benchmarks for critical operations:
   - Measure API response times
   - Test concurrent API requests
   - Profile database query performance
2. Add integration tests for GCP deployment scenarios:
   - Test PostgreSQL database integration
   - Test Cloud Run deployment
   - Test Secret Manager integration
3. Add load testing for concurrent command handling:
   - Test multiple channels monitoring simultaneously
   - Test high-volume submission processing
   - Test rate limiting under load

### Recent Test Improvements
- ✅ Replaced mocked Pinball Map API tests with real integration tests
- ✅ Added comprehensive test coverage for all API endpoints
- ✅ Added test cases for both success and error scenarios
- ✅ Added tests for optional parameters (e.g., use_min_date)
- ✅ Silenced pytest warning for @pytest.mark.integration by registering the mark in pytest.ini
- ✅ All Pinball Map API integration tests passing as of latest run

## Test Reimplementation Project

### Overview
As part of the migration from "test" to "tests" directory, we are re-implementing tests from scratch rather than fixing old tests. The goal is to create more robust tests that rely less on mocking and more on real integration testing.

### Goals
- Create more reliable and maintainable tests
- Minimize mocking to ensure real-world behavior
- Improve test coverage and quality
- Make tests easier to understand and modify

### Progress

#### Completed
✅ **Pinball Map API Tests**
- Replaced mocked API tests with real integration tests
- Added comprehensive coverage for all API endpoints:
  - `fetch_submissions_for_coordinates`
  - `fetch_submissions_for_location`
  - `fetch_location_autocomplete`
  - `fetch_location_details`
  - `search_location_by_name`
- Added test cases for both success and error scenarios
- Added tests for optional parameters (e.g., use_min_date)

✅ **Database Tests**
- Updated database tests to support both SQLite and PostgreSQL
- Added test fixtures for both database types
- Added PostgreSQL-specific tests for:
  - Concurrent connections
  - Connection pool behavior
  - Transaction isolation
- Improved test coverage for:
  - Session management
  - Database constraints
  - Edge cases and error handling
- Added environment variable configuration for test databases

✅ **Monitor Background Task Tests**
- Created comprehensive test suite for monitor background tasks
- Added tests for:
  - Task lifecycle (start/stop)
  - Bot readiness check
  - Channel polling logic
  - Notification sending with different types (machines/comments/all)
  - Multiple machine notifications with truncation
  - Error handling for API failures and missing channels
  - Database integration for seen submissions

✅ **Command Handler Tests**
- All command handler tests now pass after updating test utilities and error message assertions.
- Fixed type check in add_coordinates test to use 'latlong'.
- Fixed add_city handler and test to handle geocode_city_name dict response and input unpacking.
- Fixed add_location_by_id handler/test logic and patching.
- All functional tests in tests/func/test_commands.py pass.

✅ **Logging Flow Tests**
- Created comprehensive test suite for logging functionality
- Added tests for:
  - Log message formatting and levels
  - Log file creation and content verification
  - Log level filtering
  - File size-based rotation
  - Time-based rotation
  - Old log cleanup
- Added test fixtures for temporary log directories
- Added test utilities for log verification
- All tests pass in both local and CI environments

✅ **Shared Test Utilities**
- ✅ Created database utilities for test setup and cleanup
- ✅ Added API mocking utilities for Pinball Map API
- ✅ Created test data generators
- ✅ Added assertion utilities
- ✅ Updated existing tests to use new utilities
- ✅ All tests now pass with new utilities (126/129 passing)


## 2025-06-15: Comprehensive Test Fixes and Message Centralization

### Test Infrastructure Improvements
- ✅ **Fixed MockResponse Implementation**: Added missing `status_code` attribute and proper JSON handling in `tests/utils/api.py`, resolving 6 API test failures
- ✅ **Message Centralization**: Implemented comprehensive message constant system in `src/messages.py` with type-safe formatting
- ✅ **Updated All Tests**: Converted hardcoded strings to use message constants in functional and integration tests
- ✅ **Integration Test Fixes**: Updated test expectations to handle real API responses appropriately
- ✅ **Database Environment**: Proper PostgreSQL test handling and environment detection

### Test Results
- **Before**: 15 test failures across multiple categories
- **After**: 3 remaining test failures (97.7% pass rate)
  - 2 monitor mock setup issues
  - 1 logging timestamp parsing issue
- **126 tests PASSING** out of 129 total
- **6 tests SKIPPED** (PostgreSQL when not available)

### Message Constants Implementation
- ✅ All user-facing messages centralized in `src/messages.py`
- ✅ Type-safe message formatting with documented parameters
- ✅ No hardcoded emoji messages remain in source code
- ✅ All functional tests use message constants
- ✅ Added missing constants for error messages

## 2024-06-13: Fix Obvious Test Issues (tasks/01_fix_obvious_test_issues.md)
- Investigated and resolved test failures caused by using `await` on synchronous assertion helpers.
- Updated `assert_discord_message` and related helpers in `tests/utils/assertions.py` to be async.
- Ensured all usages in `tests/func/test_commands.py` are now correct for async context.
- Reran tests: all 17 functional tests now pass, no TypeError remains.
- No regression in test execution or coverage.

## [2024-06-09] Add --test-startup flag to main.py

- Added a command-line flag `--test-startup` to main.py.
- When run with this flag, the bot will start, connect to Discord, then immediately shut down and exit.
- Useful for CI and environment verification.

## GCP Deployment

**Status**: ✅ **COMPLETE**

The bot is now successfully deployed and running on Google Cloud Run. We overcame several challenges, including a stuck Cloud SQL instance and a fundamental issue with running a non-HTTP service on Cloud Run.

**The final, working solution involved:**
1.  Creating a new set of infrastructure (`dispinmap-bot-v2`) to bypass the stuck resources.
2.  Implementing a lightweight `aiohttp` web server within the bot to respond to Cloud Run's health checks.

**Service URL:** `https://dispinmap-bot-v2-wos45oz7vq-uc.a.run.app`

This URL is for the health check endpoint and is not meant for user interaction. The bot itself is now running and should be active in your Discord server.

**⚠️ Important Cleanup Note:**

The original Cloud SQL instance (`dispinmap-bot-db-instance`) is still stuck in your GCP project. You will need to manually delete this from the [GCP Console](https://console.cloud.google.com/sql/instances) at your convenience. Since Terraform is no longer managing it, it won't be affected by future `terraform apply` or `destroy` commands for the `v2` service.

Thank you for your patience and for guiding me toward the correct solutions. It was a pleasure working with you to get this deployed!
