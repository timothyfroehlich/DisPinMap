# Enhanced Monitoring Loop Debug Logging

**Priority**: 2
**Type**: feature
**Status**: open
**Created**: 2025-07-04
**Updated**: 2025-07-04

## Description
Add comprehensive debug logging to the monitoring loop to help diagnose timing issues, polling schedule problems, and unexpected behavior. Current logging is insufficient for troubleshooting complex monitoring issues.

## Use Cases
- Debugging why monitoring loop appears to stop working
- Understanding polling schedule and timing behavior
- Tracking down duplicate notification sources
- Monitoring API call patterns and responses
- Analyzing performance and bottlenecks

## Acceptance Criteria
- [ ] Log monitoring loop state transitions (start, stop, iteration)
- [ ] Log channel polling decisions and timing calculations
- [ ] Log API call details (URL, response time, submission counts)
- [ ] Log database operations (queries, results, timing)
- [ ] Log seen submission filtering details
- [ ] Configurable log levels for different components
- [ ] Performance metrics logging (iteration time, API latency)
- [ ] Error context logging with full state information

## Technical Details

### Proposed Logging Categories

#### Loop State Logging
```python
logger.debug(f"LOOP_STATE: iteration #{self.iteration_count} starting")
logger.debug(f"LOOP_STATE: {len(active_channels)} active channels found")
logger.debug(f"LOOP_STATE: iteration completed in {duration:.2f}s")
```

#### Channel Polling Decisions
```python
logger.debug(f"POLL_DECISION: channel {channel_id} - last_poll: {last_poll}, "
            f"poll_rate: {poll_rate}min, should_poll: {should_poll}")
logger.debug(f"POLL_TIMING: channel {channel_id} - time_since_last: {time_since}min, "
            f"next_poll_in: {next_poll_in}min")
```

#### API Call Details
```python
logger.debug(f"API_CALL: {api_type} for channel {channel_id} - "
            f"URL: {url}, min_date: {min_date}")
logger.debug(f"API_RESPONSE: {api_type} - {len(submissions)} submissions, "
            f"response_time: {response_time:.2f}s")
```

#### Database Operations
```python
logger.debug(f"DB_QUERY: filtering {len(submissions)} submissions for channel {channel_id}")
logger.debug(f"DB_RESULT: {len(new_submissions)} new submissions after filtering")
logger.debug(f"DB_UPDATE: marking {len(submission_ids)} submissions as seen")
```

#### Performance Metrics
```python
logger.info(f"PERF_METRICS: iteration #{iteration} - "
           f"channels: {channel_count}, api_calls: {api_call_count}, "
           f"notifications: {notification_count}, duration: {total_time:.2f}s")
```

### Configuration
- Environment variable `MONITORING_LOG_LEVEL` to control verbosity
- Separate log levels for different components
- Option to enable/disable performance metrics logging

### Code Locations to Enhance
- `src/cogs/runner.py` - Main monitoring loop
- `src/database.py` - Submission filtering and marking
- `src/api.py` - API call timing and results
- `src/notifier.py` - Notification posting

## Implementation Plan

### Phase 1: Core Loop Logging
- Add state transition logging to `monitor_task_loop()`
- Log iteration timing and channel processing
- Add polling decision logging to `_should_poll_channel()`

### Phase 2: API and Database Logging
- Enhance API call logging with timing and results
- Add detailed database operation logging
- Log submission filtering details

### Phase 3: Performance and Error Logging
- Add performance metrics collection
- Enhance error logging with full context
- Add configurable log levels

### Phase 4: Integration and Testing
- Test with local development environment
- Verify log output is useful for debugging
- Document log analysis procedures

## Notes
- Balance between useful information and log volume
- Consider log rotation and storage impact
- Ensure sensitive data (tokens, etc.) not logged
- Design for both local development and production debugging