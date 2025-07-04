# Seen Submission Race Condition

**Priority**: 1
**Type**: bug
**Status**: open
**Created**: 2025-07-04
**Updated**: 2025-07-04

## Description
Race condition exists between filtering submissions and marking them as seen, potentially allowing duplicate notifications if the monitoring loop runs multiple times rapidly or if API responses change between calls.

## Reproduction Steps
1. Set up monitoring targets with very short poll intervals (difficult to reproduce consistently)
2. Force multiple rapid checks using `.trigger` command
3. Monitor for duplicate notifications of the same submission
4. Check database for timing issues in `seen_submissions` table

## Expected vs Actual Behavior
- **Expected**: Each submission should only be notified once, regardless of timing
- **Actual**: Rapid polling or API inconsistencies could cause duplicate notifications

## Technical Details

### Code Location
- **File**: `src/cogs/runner.py`
- **Functions**: `filter_new_submissions()` (line 386-398), `post_submissions()`, `mark_submissions_seen()`

### Race Condition Flow
```python
# Time T1: First check starts
submissions = await fetch_submissions_for_location(...)  # API call
new_submissions = self.db.filter_new_submissions(channel_id, submissions)  # Query DB

# Time T2: Second check starts (before first completes)
submissions_2 = await fetch_submissions_for_location(...)  # Same API response
new_submissions_2 = self.db.filter_new_submissions(channel_id, submissions_2)  # Same query result

# Time T3: Both post notifications
await self.post_submissions(new_submissions)  # Posts duplicates
await self.post_submissions(new_submissions_2)  # Posts duplicates

# Time T4: Both mark as seen
self.db.mark_submissions_seen(channel_id, submission_ids)  # Second call gets IntegrityError
```

### Database Protection
- `seen_submissions` table has unique constraint on `(channel_id, submission_id)`
- `mark_submissions_seen()` handles `IntegrityError` gracefully
- **Problem**: Notifications already sent before constraint violation

### Potential Triggers
- Multiple rapid manual checks (`.trigger` command)
- Cloud Run scaling events causing multiple instances
- API response timing variations
- Database connection delays

## Proposed Solutions

### Option 1: Atomic Transaction
```python
async def process_submissions_atomically(self, channel_id, submissions):
    async with self.db.transaction():
        new_submissions = self.db.filter_new_submissions(channel_id, submissions)
        if new_submissions:
            self.db.mark_submissions_seen(channel_id, [s["id"] for s in new_submissions])
            await self.post_submissions(new_submissions)
```

### Option 2: Channel-Level Locking
```python
class Runner:
    def __init__(self):
        self.channel_locks = {}
    
    async def run_checks_for_channel(self, channel_id, config, is_manual_check=False):
        if channel_id not in self.channel_locks:
            self.channel_locks[channel_id] = asyncio.Lock()
        
        async with self.channel_locks[channel_id]:
            # Existing check logic
```

### Option 3: Submission ID Tracking
```python
# Track recently processed submission IDs in memory
self.recently_processed = {}  # {channel_id: set(submission_ids)}

async def filter_new_submissions(self, channel_id, submissions):
    # Filter by database AND recent memory
    recent = self.recently_processed.get(channel_id, set())
    truly_new = [s for s in db_filtered if s["id"] not in recent]
    return truly_new
```

## Acceptance Criteria
- [ ] No duplicate notifications under rapid polling scenarios
- [ ] Multiple manual checks don't cause duplicates
- [ ] Database integrity maintained
- [ ] Performance impact minimal
- [ ] Cloud Run scaling doesn't trigger race conditions
- [ ] Test with concurrent `.trigger` commands

## Notes
- Difficult to reproduce consistently in testing
- May require load testing to verify fix
- Related to Cloud Run scaling and multiple instances
- Consider distributed locking for multi-instance deployments