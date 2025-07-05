# Startup Duplicate Notifications

**Priority**: 1 **Type**: bug **Status**: open **Created**: 2025-07-04
**Updated**: 2025-07-04

## Description

When the bot starts up, it sends notifications for old submissions that have
already been shown previously. The startup check bypasses normal polling logic
and treats all submissions as "new" even though they were previously processed.

## Reproduction Steps

1. Start the bot with existing monitoring targets
2. Observe that one or more channels receive notifications
3. Check log timestamps - notifications are for submissions that occurred before
   the current session
4. Compare with previous bot runs - same submissions are re-notified

## Expected vs Actual Behavior

- **Expected**: Startup should only initialize monitoring, not send duplicate
  notifications
- **Actual**: Startup sends notifications for previously seen submissions

## Technical Details

### Code Location

- **File**: `src/cogs/runner.py`
- **Function**: `_run_startup_checks()` (lines 457-508)
- **Issue**: Calls `run_checks_for_channel(is_manual_check=False)` during
  startup

### Root Cause

1. `_run_startup_checks()` runs immediately when bot becomes ready
2. Calls `run_checks_for_channel()` with `is_manual_check=False`
3. Since `last_poll_at` is None, API fetches all recent submissions without date
   filtering
4. `filter_new_submissions()` has no seen submissions in database yet (fresh
   start)
5. All submissions get posted as notifications
6. Submissions are then marked as seen, preventing future duplicates

### Database State

- `seen_submissions` table is empty on startup
- `last_poll_at` is None for channels that haven't been polled
- API returns submissions from past 24 hours without filtering

## Proposed Solution

### Option 1: Change Startup to Manual Check

```python
# In _run_startup_checks()
result = await self.run_checks_for_channel(channel_id, config, is_manual_check=True)
```

This would show "Last 5 submissions" format instead of posting as notifications.

### Option 2: Mark as Seen Without Posting

```python
# In _run_startup_checks()
submissions = await self._fetch_submissions_for_channel(channel_id, config)
if submissions:
    self.db.mark_submissions_seen(channel_id, [s["id"] for s in submissions])
# Don't call post_submissions()
```

### Option 3: Skip Startup Checks Entirely

Remove `_run_startup_checks()` and let normal 1-minute polling handle first
check.

## Acceptance Criteria

- [ ] Bot startup does not trigger duplicate notifications
- [ ] Normal polling behavior unchanged
- [ ] Manual check commands still show recent submissions
- [ ] No regression in monitoring functionality
- [ ] Test with multiple channels and monitoring targets

## Notes

- This issue is particularly noticeable with active monitoring targets
- Users report confusion when old submissions appear as "new"
- May be related to timezone handling in date filtering logic
