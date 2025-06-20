# Current Tasks and Status

## Pending Tasks

### Task 2: Enhance `!check` Command Logic

**Objective**: Modify the `!check` command to ensure it always attempts to show up to 5 relevant submissions. It will first show all new submissions since the last check, and if that's less than 5, it will backfill the list with the most recent older submissions to reach a total of 5.

**Detailed Steps**:

1. **Modify Monitor Check Logic**:
   * **File**: `src/monitor.py`
   * **Change**: Update the `run_checks_for_channel` method. When `is_manual_check` is `True`:
       * Fetch all submissions from the API (`use_min_date=False`).
       * Partition the fetched submissions into two lists: `new_submissions` (not in `seen_submission_ids`) and `old_submissions` (already seen).
       * Filter both lists based on the target's configured `notification_types`.
       * If the count of `filtered_new_submissions` is less than 5, take the most recent `5 - len(filtered_new_submissions)` items from `filtered_old_submissions`.
       * Create a final `submissions_to_report` list containing all `filtered_new_submissions` followed by the backfilled older ones.
       * Pass this combined list to the `_send_notifications` method.

2. **Update Notifier Logic (Optional)**:
   * **File**: `src/notifier.py`
   * **Change**: Review the `send_notifications` method. The message for a manual check may need adjustment to be clearer. For instance, instead of "Found X new submission(s)", it could be "Found X new submission(s). Showing the 5 most recent:" to reflect the new behavior.

3. **Test Changes**:
   * **`tests/unit/test_monitor.py`**: Create new test cases to simulate various scenarios for the `!check` command:
       * More than 5 new submissions.
       * Less than 5 new submissions, requiring backfill.
       * No new submissions, requiring a full list of 5 old submissions.
       * Assert that the correct combined list of submissions is passed to the notifier.
   * **`tests/func/test_commands.py`**: Update the `!check` command functional tests to reflect the new output, verifying that up to 5 submissions are always shown and that the message is correct. This will involve seeding the test database with seen submissions and mocking API responses.

### Remaining Test Fixes

- **Task 8**: Fix monitor test mocks (2 failing tests) - Mock channel setup issues in `test_poll_channel_with_targets` and `test_send_notifications_multiple_machines`
- **Task 9**: Fix logging timestamp parsing (1 failing test) - ANSI color code handling in `test_colored_formatter`

## Future Improvements

- **Performance Optimization**: Database query optimization, caching, background task scheduling.
- **Enhanced Error Handling**: Retry logic for Discord API failures, graceful degradation for external API outages.
- **Monitoring & Observability**: Metrics collection, health check endpoints, performance dashboards.
- **Security Enhancements**: Rate limiting, input validation, audit logging.