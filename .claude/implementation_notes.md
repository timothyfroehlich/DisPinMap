# Implementation Notes & Discoveries

## Session 1: 2025-06-20

### Codebase Analysis Findings

#### Bot Architecture
- **Main Entry**: `src/main.py` - Discord bot setup with cog loading
- **Command Structure**: Uses Discord.py cogs in `src/cogs/`
  - `monitoring.py` - User commands (add, rm, list, check, export)
  - `monitor.py` - Background polling task (`@tasks.loop(minutes=1)`)
  - `config.py` - Configuration commands (poll_rate, notifications)

#### API Integration
- **PinballMap API**: `src/api.py` - Handles location search, submissions
- **Geocoding**: Also in `src/api.py` - City name to coordinates
- **Rate Limiting**: `rate_limited_request()` function (async but uses blocking requests.get - Issue #15)

#### Database Schema
- **SQLAlchemy Models**: `src/models.py`
  - `ChannelConfig` - Channel settings and last poll times
  - `MonitoringTarget` - What each channel monitors
  - `SeenSubmission` - Deduplication tracking
- **Database Class**: `src/database.py` - Supports SQLite and PostgreSQL

#### Monitoring Flow
1. Background task runs every minute (`monitor_task_loop`)
2. Checks if channels should be polled based on `poll_rate_minutes`
3. Fetches submissions for each target (location, coordinates, city)
4. Filters new submissions using `SeenSubmission` table
5. Posts notifications via `Notifier` class
6. Updates timestamps and marks submissions as seen

#### Message System
- **Centralized Messages**: `src/messages.py` - All user-facing strings
- **Notifier**: `src/notifier.py` - Formats and sends Discord messages
- **Rate Limiting**: 1-second delays between messages in production

#### Testing Infrastructure
- **Pytest Setup**: `conftest.py`, `pytest.ini`
- **Test Utils**: `tests/utils/` with database, API, and assertion helpers
- **Coverage**: Unit, integration, and functional test categories
- **Database Testing**: In-memory SQLite with cleanup fixtures

### Potential Issues Identified
1. **Async/Blocking Mix**: `rate_limited_request()` declared async but uses blocking `requests.get()`
2. **Time Zone Handling**: Some datetime operations may not be timezone-aware
3. **Monitoring Reliability**: Need to verify background task actually triggers correctly
4. **Error Handling**: May need better API failure handling during monitoring

### Simulation Framework Requirements
1. **API Mocking**: Need to capture real responses and provide controlled test data
2. **Discord Mocking**: Must simulate channels, users, message contexts
3. **Time Control**: Background tasks need accelerated time simulation
4. **Database Isolation**: Each test needs clean database state
5. **Message Validation**: Need semantic analysis beyond string matching

### Implementation Strategy
- Build on existing test utilities rather than replacing them
- Use captured real API responses for realistic testing
- Create separate simulation test directory structure
- Implement time manipulation carefully to avoid test interference
- Focus on complete user journeys rather than just unit testing
