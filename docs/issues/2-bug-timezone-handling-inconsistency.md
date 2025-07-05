# Timezone Handling Inconsistency

**Priority**: 2 **Type**: bug **Status**: open **Created**: 2025-07-04
**Updated**: 2025-07-04

## Description

Inconsistent timezone handling across the application may cause polling schedule
issues, incorrect date filtering in API calls, and database timestamp problems.

## Reproduction Steps

1. Review datetime handling in different parts of the codebase
2. Check for naive vs timezone-aware datetime objects
3. Monitor for polling schedule irregularities
4. Verify API date filtering works correctly across time zones

## Expected vs Actual Behavior

- **Expected**: All datetime operations should be timezone-aware and consistent
- **Actual**: Mix of naive and timezone-aware datetime objects causing potential
  issues

## Technical Details

### Code Locations

- **File**: `src/database.py` - `get_channel_config()` (lines 113-131)
- **File**: `src/cogs/runner.py` - Various datetime operations
- **File**: `src/api.py` - Date filtering in API calls

### Specific Issues

#### Database Operations

```python
# In get_channel_config() - timezone conversion happens here
if config.last_poll_at and config.last_poll_at.tzinfo is None:
    config.last_poll_at = config.last_poll_at.replace(tzinfo=timezone.utc)
```

#### Polling Schedule Logic

```python
# In _should_poll_channel() - may use naive datetime
current_time = datetime.now()  # Potentially naive
time_since_last_poll = current_time - config.last_poll_at  # Mixed types
```

#### API Date Filtering

```python
# Date calculations for min_date_of_submission parameter
yesterday = datetime.now() - timedelta(days=1)  # Potentially naive
date_str = yesterday.strftime("%Y-%m-%d")  # May not account for timezone
```

### Potential Impact

- **Polling Schedule**: Channels may poll too frequently or not frequently
  enough
- **API Filtering**: Submissions might be missed or duplicated due to date range
  issues
- **Database Consistency**: Timestamps may not align properly
- **Multi-timezone Users**: Different behavior based on server vs user timezones

## Proposed Solution

### Centralized Timezone Handling

```python
# Create utility functions for consistent datetime handling
from datetime import datetime, timezone
import pytz

def now_utc() -> datetime:
    """Get current UTC time, always timezone-aware"""
    return datetime.now(timezone.utc)

def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and in UTC"""
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def format_api_date(dt: datetime) -> str:
    """Format datetime for API calls consistently"""
    return ensure_utc(dt).strftime("%Y-%m-%d")
```

### Update All Datetime Operations

1. Replace `datetime.now()` with `now_utc()`
2. Ensure all database datetime fields are timezone-aware
3. Standardize API date formatting
4. Add timezone validation in tests

## Acceptance Criteria

- [ ] All datetime objects are timezone-aware
- [ ] Polling schedules work correctly regardless of server timezone
- [ ] API date filtering is consistent and accurate
- [ ] Database timestamps are properly handled
- [ ] No regression in existing functionality
- [ ] Add timezone-specific tests

## Notes

- May require database migration if existing timestamps are naive
- Consider impact on existing data
- Test with different server timezone configurations
- Document timezone assumptions for deployment
