# Product Specifications

## Bot Commands
The bot uses slash commands prefixed with `!`.

**Target Monitoring:**
- `!add location <name_or_id>` - Monitor specific locations by ID or name
- `!add city <name> [radius]` - Monitor city areas with optional radius
- `!add coordinates <lat> <lon> [radius]` - Monitor coordinate areas with optional radius
- `!rm <index>` - Remove target by index (use `!list` to see indices)

**General Commands:**
- `!list` or `!ls` - Show all monitored targets with their indices
- `!export` - Export channel configuration as copy-pasteable commands
- `!poll_rate <minutes> [target_index]` - Set polling rate for channel or specific target
- `!notifications <type> [target_index]` - Set notification types (machines, comments, all)
- `!check` - Immediately check for new submissions across all targets

## Product Decisions

### Notification Filtering
- Initial submissions when adding a new target are filtered according to the channel's notification settings
- Default notification type is 'machines' (additions/removals only)
- Available notification types:
  - `machines`: Only machine additions and removals
  - `comments`: Only condition updates and comments
  - `all`: All submission types

### Check/Monitoring Behavior

There are three types of checks. All successful checks update the channel's `last_poll_at` timestamp, which is reflected in the `!list` command's "Last Checked" column. All checks filter their results based on the channel's configured notification type (`machines`, `comments`, or `all`).

1. **Automatic Poll (Scheduled)**
   * **Trigger**: Background timer based on the channel's configured poll rate.
   * **Reporting**: Reports all new submissions since the last successful check.
   * **Error Handling**: Errors are logged internally. No message is sent to the Discord channel to avoid spam. The `last_poll_at` timestamp is NOT updated on failure, causing a retry on the next cycle.

2. **Add Target Check**
   * **Trigger**: Immediately after a user successfully adds a new monitoring target (`!add ...`).
   * **Reporting**: Reports the 5 most recent submissions relevant to the new target, fetching historical data as far back as needed. This confirms the target is working as expected.
   * **Error Handling**: If the check fails, an explicit error message is posted to the Discord channel. The `last_poll_at` timestamp is NOT updated on failure.

3. **Manual Check (`!check`)**
   * **Trigger**: On-demand execution by a user.
   * **Reporting (Hybrid Model)**:
       1. Reports all new submissions since the last successful check.
       2. If the number of new submissions is fewer than 5, it fetches older submissions (going back as far as necessary, beyond the 24-hour limit if needed) until a total of 5 are reported.
   * **Error Handling**: If the check fails, an explicit error message is posted to the Discord channel. The `last_poll_at` timestamp is NOT updated on failure.

### Concurrency
- A locking mechanism to prevent overlapping checks (e.g., a check taking longer than the poll interval) was considered but determined to be overkill for the current usage patterns. This is noted in the source code.

### Submission History
- When adding a new target, the bot displays the 5 most recent submissions
- Submissions are sorted by creation date (newest first)
- The history display respects the channel's notification type settings
- For initial target display: submissions older than 24 hours are not included (unlike manual checks, which will go back as far as needed to find 5 submissions)

## Timestamp Update Behavior and Testing

### Check Types and Timestamp Rules

The `last_poll_at` timestamp in channel configurations follows specific update rules based on check type:

1. **Automatic Polls (Scheduled)**
   - **Updates timestamp**: On successful API calls, regardless of whether new submissions were found
   - **Does NOT update**: When API calls fail or exceptions occur
   - **Rationale**: Failed polls should retry on next cycle; successful polls (even with no new data) indicate the system is working

2. **Manual Checks (!check command)**
   - **Updates timestamp**: On successful API calls, regardless of whether new submissions were found
   - **Does NOT update**: When API calls fail or exceptions occur
   - **Rationale**: Successful manual checks indicate the targets are being monitored properly

3. **Add Target Checks**
   - **Updates timestamp**: On successful API calls when adding new targets
   - **Does NOT update**: When API calls fail during target addition
   - **Rationale**: Successful target addition indicates the system is working and targets are being monitored

### Testing Guidelines for Timestamps

When writing tests involving timestamp comparisons:

1. **Use Consistent Timezone Format**
   ```python
   # Correct - timezone-aware
   initial_time = datetime.now(timezone.utc)

   # Incorrect - naive datetime will cause comparison errors
   initial_time = datetime.now()
   ```

2. **Database vs Test Consistency**
   - Database stores timezone-aware datetime objects
   - Tests must use timezone-aware objects for comparisons
   - Use `datetime.now(timezone.utc)` in tests, not `datetime.now()`

3. **Common Test Failure Patterns**
   ```python
   # This will fail with "can't subtract offset-naive and offset-aware datetimes"
   initial_time = datetime.now()  # naive
   db_time = config['last_poll_at']  # timezone-aware from database
   assert db_time == initial_time  # ERROR

   # Correct approach
   initial_time = datetime.now(timezone.utc)  # timezone-aware
   db_time = config['last_poll_at']  # timezone-aware from database
   assert db_time == initial_time  # OK
   ```

4. **Test Verification Patterns**
   - For successful automatic polls: Assert timestamp WAS updated
   - For failed automatic polls: Assert timestamp was NOT updated
   - For successful manual checks: Assert timestamp WAS updated
   - For failed manual checks: Assert timestamp was NOT updated
   - For successful add target operations: Assert timestamp WAS updated
   - For failed add target operations: Assert timestamp was NOT updated

### Implementation Notes

- All successful checks (automatic, manual, and add target) should update the `last_poll_at` timestamp
- Timestamp updates should occur after successful API operations, regardless of check type
- Only failed API calls should prevent timestamp updates
- Error handling should distinguish between automatic polls (silent logging) and manual/add target checks (Discord error messages)
