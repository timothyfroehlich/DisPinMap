# DisPinMap Simulation Testing Framework

## Overview

The DisPinMap Simulation Testing Framework is a comprehensive end-to-end testing system that validates the entire Discord bot pipeline from command handling through API interactions to periodic monitoring notifications. This framework allows developers to test complete user journeys without requiring actual Discord servers, live APIs, or waiting for real-time polling intervals.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [API Response Capture System](#api-response-capture-system)
4. [Mock API Framework](#mock-api-framework)
5. [Discord Simulation](#discord-simulation)
6. [Time Manipulation](#time-manipulation)
7. [User Journey Testing](#user-journey-testing)
8. [Response Validation](#response-validation)
9. [Usage Examples](#usage-examples)
10. [Running Tests](#running-tests)
11. [Development Guide](#development-guide)
12. [Troubleshooting](#troubleshooting)

## Architecture Overview

The simulation framework consists of several interconnected layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Simulation Test Layer                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   User Journey  │  │   Integration   │  │    Pytest   │ │
│  │     Tests       │  │     Tests       │  │ Integration  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  Core Framework Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │    Discord      │  │       Time      │  │   Response   │ │
│  │   Simulation    │  │  Manipulation   │  │  Validation  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Mock Services Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   API Mocking   │  │    Database     │  │   Message    │ │
│  │   (PinballMap,  │  │   Isolation     │  │   Analysis   │ │
│  │   Geocoding)    │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Foundation Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Captured API   │  │   Test Data     │  │    Logging   │ │
│  │   Responses     │  │   Generation    │  │  & Tracking  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. SimulationTestFramework

The main orchestrator that coordinates all simulation components.

**Key Features:**
- Unified setup and teardown of all mock services
- Dependency injection for bot components
- State management and result tracking
- Context manager support for clean resource management

**Location:** `tests/utils/simulation.py`

### 2. API Mock System

Provides realistic API responses based on captured real data.

**Components:**
- `APIResponseLoader`: Loads captured API responses
- `PinballMapAPIMock`: Mocks PinballMap API functions
- `GeocodingAPIMock`: Mocks geocoding API functions
- `APISimulator`: Coordinates all API mocking

**Location:** `tests/utils/api_mock.py`

### 3. Discord Simulation

Creates a complete fake Discord environment for testing.

**Components:**
- `MockBot`: Simulated Discord bot
- `MockChannel`: Fake Discord channel with message tracking
- `MockUser`: Simulated Discord user
- `CommandSimulator`: Executes bot commands in simulation
- `MessageAnalyzer`: Validates bot responses

**Location:** `tests/utils/discord_mock.py`

### 4. Time Manipulation

Controls time flow for testing time-dependent behavior.

**Components:**
- `TimeController`: Core time manipulation
- `PollingSimulator`: Simulates periodic tasks
- `MonitoringSimulator`: Specialized for bot monitoring
- `DatabaseTimeHelper`: Manages time-related database operations

**Location:** `tests/utils/time_mock.py`

## API Response Capture System

The framework uses real API responses captured from live services to ensure realistic testing behavior.

### Capture Process

1. **Data Collection Script**
   - Location: `scripts/capture_api_responses.py`
   - Captures responses from PinballMap and geocoding APIs
   - Stores responses in structured JSON format
   - Includes metadata for filtering and selection

2. **Response Categories**
   - **PinballMap Locations**: Location details, search results
   - **PinballMap Submissions**: Recent and historical submissions
   - **Geocoding**: City name resolution with coordinates
   - **Error Cases**: Invalid inputs and API failures

3. **Storage Structure**
   ```
   tests/fixtures/api_responses/
   ├── index.json                 # Master index of all responses
   ├── pinballmap_locations/      # Location-specific responses
   ├── pinballmap_search/         # Search result responses
   ├── pinballmap_submissions/    # Submission data
   └── geocoding/                 # Geocoding responses
   ```

### Captured Data Examples

**Seattle Pinball Museum (ID: 1309)**
- Full location details with 46+ machines
- Recent submissions and activity
- Machine change history

**Coordinate Searches**
- Seattle Center area (47.6062, -122.3321)
- Various radius configurations
- New York Times Square area

**City Geocoding**
- Major US cities with state specifications
- Ambiguous city names (Portland)
- Invalid city names for error testing

## Mock API Framework

### Configuration Options

The API mock system supports multiple operation modes:

```python
# Fast mode for unit tests (no delays)
mock = create_fast_mock()

# Realistic timing with delays and occasional errors
mock = create_realistic_mock()

# High error rate for robustness testing
mock = create_error_prone_mock()

# Custom configuration
config = MockAPIConfig()
config.with_delays(0.1, 0.5)
config.with_errors(error_rate=0.1, timeout_rate=0.05)
mock = APISimulator(config)
```

### Response Matching

The mock system intelligently matches requests to appropriate responses:

1. **Exact Matches**: Location IDs, coordinates, city names
2. **Fuzzy Matching**: Similar search terms, nearby coordinates
3. **Error Injection**: Random failures based on configuration
4. **Default Responses**: Fallbacks for unmatched requests

### Request Logging

All API calls are logged for verification:

```python
# Get detailed logs of all API interactions
api_logs = framework.api_sim.get_request_logs()

# Verify specific API calls were made
pinballmap_calls = api_logs["pinballmap"]
geocoding_calls = api_logs["geocoding"]
```

## Discord Simulation

### Mock Discord Objects

The framework creates realistic Discord object simulations:

**MockChannel**
- Tracks all sent messages
- Provides message history
- Supports Discord API methods

**MockUser**
- Realistic user properties
- Configurable for testing different scenarios

**MockBot**
- Command execution pipeline
- Cog loading and management
- Event simulation

### Command Execution

Commands are executed through a realistic pipeline:

1. **Command Parsing**: Parse user input into command and arguments
2. **Context Creation**: Create mock command context
3. **Cog Dispatch**: Route to appropriate cog method
4. **Response Capture**: Track all bot responses
5. **Result Analysis**: Validate responses and behavior

### Message Tracking

All bot messages are captured and categorized:

```python
# Get messages sent to a channel
messages = channel.get_sent_messages()

# Analyze message content
analyzer = MessageAnalyzer()
for message in messages:
    category = analyzer.categorize_message(message.content)
    location_info = analyzer.extract_location_info(message.content)
```

## Time Manipulation

### Core Concepts

The time manipulation system allows complete control over time flow:

**Time Control**
- Set specific times for testing
- Advance time by arbitrary amounts
- Control polling intervals and scheduling

**Monitoring Simulation**
- Accelerate periodic tasks
- Test long-running scenarios quickly
- Validate timing-dependent behavior

### Usage Patterns

```python
# Basic time control
with TimeController() as time_ctrl:
    time_ctrl.set_time(datetime(2025, 1, 1, 12, 0, 0))
    time_ctrl.advance_hours(2)
    # Bot thinks it's 2:00 PM on Jan 1, 2025

# Monitoring simulation
monitoring_sim = MonitoringSimulator(time_ctrl, monitor_cog)
await monitoring_sim.simulate_monitoring_cycle(duration_minutes=120)
```

### Database Time Helpers

Special utilities manage time-related database operations:

```python
db_helper = DatabaseTimeHelper(database, time_controller)

# Set last poll time to 30 minutes ago
db_helper.set_channel_last_poll_time(channel_id, minutes_ago=30)

# Spread submission timestamps over time
db_helper.simulate_submission_aging(submissions, days_spread=7)
```

## User Journey Testing

### Complete Journey Framework

The framework supports testing entire user workflows:

**Journey Components**
1. **Setup**: Initialize test environment
2. **User Actions**: Simulate Discord commands
3. **Bot Processing**: Execute command logic
4. **API Interactions**: Mock external service calls
5. **Database Updates**: Track state changes
6. **Monitoring**: Simulate periodic background tasks
7. **Validation**: Verify expected outcomes

### Example Journeys

**Location Monitoring Journey**
```python
async def test_location_monitoring_journey():
    async with SimulationTestFramework() as framework:
        # 1. User adds location
        success, messages = await framework.simulate_add_location_by_id(1309)
        assert success

        # 2. Bot shows initial submissions
        assert any("Found" in msg for msg in messages)

        # 3. User lists targets
        list_messages = await framework.simulate_list_targets()
        assert "Seattle Pinball Museum" in " ".join(list_messages)

        # 4. Periodic monitoring detects changes
        monitoring_results = await framework.simulate_periodic_monitoring(
            duration_minutes=120
        )

        # 5. Validate database state
        db_state = framework.get_database_state()
        assert len(db_state["targets"]) == 1
        assert db_state["channels"][0]["is_active"]
```

**Multi-Target Monitoring**
```python
async def test_multi_target_monitoring():
    async with SimulationTestFramework() as framework:
        # Add location, coordinates, and city
        await framework.simulate_add_location_by_id(1309)
        await framework.simulate_add_coordinates(47.6062, -122.3321, 5)
        await framework.simulate_add_city("Seattle, WA", radius=10)

        # Verify all targets are monitored correctly
        monitoring_results = await framework.simulate_periodic_monitoring(
            duration_minutes=90
        )

        # Should handle multiple targets without conflicts
        assert "error" not in " ".join(monitoring_results["new_messages"])
```

### Error Handling Testing

The framework thoroughly tests error scenarios:

**Invalid Input Handling**
- Non-existent location IDs
- Invalid coordinates
- Malformed city names
- Missing command parameters

**API Failure Simulation**
- Network timeouts
- Service unavailability
- Rate limiting
- Malformed responses

**Database Constraint Testing**
- Duplicate target prevention
- Constraint violations
- Transaction rollbacks

## Response Validation

### Message Analysis

The framework provides sophisticated message analysis:

**Content Categorization**
```python
analyzer = MessageAnalyzer()

# Categorize messages by type
category = analyzer.categorize_message(message)
# Returns: "success", "error", "info", "notification", "unknown"

# Extract structured information
location_info = analyzer.extract_location_info(message)
# Returns: {"type": "location", "id": "1309"} or {"type": "coordinates", ...}
```

**Format Validation**
```python
# Validate message follows expected patterns
is_valid = analyzer.validate_response_format(message, "success_with_name")
# Checks for pattern: "✅.*Added.*:**.*:**"
```

### Behavioral Verification

The framework validates bot behavior across multiple dimensions:

**Database Consistency**
- Target creation and configuration
- Submission tracking and deduplication
- Channel state management

**API Usage Patterns**
- Correct API endpoints called
- Appropriate parameters passed
- Rate limiting respected

**Timing Behavior**
- Polling intervals honored
- Response timing within bounds
- Background task scheduling

## Usage Examples

### Basic Setup

```python
from tests.utils.simulation import SimulationTestFramework

async def test_basic_functionality():
    async with SimulationTestFramework() as framework:
        # Framework automatically sets up:
        # - Test database
        # - API mocks
        # - Discord simulation
        # - Time control

        # Perform tests
        success, messages = await framework.simulate_add_location_by_id(1309)
        assert success
```

### Custom Configuration

```python
from tests.utils.simulation import SimulationTestFramework
from tests.utils.api_mock import MockAPIConfig

# Configure for realistic timing
framework = SimulationTestFramework(use_realistic_timing=True)

async with framework:
    # Test with realistic delays and occasional errors
    pass
```

### Standalone Component Testing

```python
from tests.utils.api_mock import create_fast_mock
from tests.utils.discord_mock import create_basic_simulation

# Test just API mocking
with create_fast_mock() as api_sim:
    # API calls are mocked
    pass

# Test just Discord simulation
discord_sim, channel = create_basic_simulation()
```

### Production-Like Testing

```python
async def test_production_scenario():
    # Use realistic timing and larger datasets
    framework = SimulationTestFramework(use_realistic_timing=True)

    async with framework:
        # Add multiple targets like a real user
        await framework.simulate_add_location_by_id(1309)
        await framework.simulate_add_coordinates(47.6062, -122.3321, 5)
        await framework.simulate_add_city("Seattle, WA")

        # Set production-like poll rate
        framework.database.update_channel_config(
            framework.test_channel.id,
            framework.test_guild.id,
            poll_rate_minutes=60  # 1 hour like production
        )

        # Simulate extended monitoring period
        monitoring_results = await framework.simulate_periodic_monitoring(
            duration_minutes=180  # 3 hours
        )

        # Validate production-like behavior
        assert monitoring_results["polling_cycles"] >= 3
```

## Running Tests

### Pytest Integration

The framework integrates seamlessly with pytest:

```bash
# Run all simulation tests
pytest tests/simulation/

# Run specific test categories
pytest -m simulation
pytest -m "simulation and not slow"

# Run with verbose output
pytest tests/simulation/ -v -s

# Run single test file
pytest tests/simulation/test_user_journeys.py

# Run specific test
pytest tests/simulation/test_user_journeys.py::TestLocationMonitoringJourney::test_add_location_by_id_success
```

### Test Markers

Tests use pytest markers for organization:

- `@pytest.mark.simulation`: Simulation tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Long-running tests

### Demo Script

A comprehensive demo shows all framework capabilities:

```bash
# Run the complete demonstration
python tests/simulation/demo_simulation.py

# Run specific demo sections
python tests/simulation/demo_simulation.py basic_journey
```

### API Response Refresh

Periodically refresh captured API responses:

```bash
# Capture fresh API responses
python scripts/capture_api_responses.py

# This updates tests/fixtures/api_responses/ with new data
```

## Development Guide

### Adding New Test Scenarios

1. **Create Test Case**
   ```python
   async def test_new_scenario():
       async with SimulationTestFramework() as framework:
           # Your test logic here
           pass
   ```

2. **Add to Test Class**
   ```python
   class TestNewFeature:
       async def test_feature_functionality(self):
           # Test implementation
           pass
   ```

3. **Use Appropriate Markers**
   ```python
   @pytest.mark.simulation
   @pytest.mark.slow
   async def test_long_running_scenario():
       # Test implementation
       pass
   ```

### Extending Mock Responses

1. **Capture New Data**
   - Modify `scripts/capture_api_responses.py`
   - Add new API endpoints or scenarios
   - Run capture script to update fixtures

2. **Enhance Mock Logic**
   - Update `tests/utils/api_mock.py`
   - Add new response matching patterns
   - Implement custom mock behaviors

3. **Update Test Cases**
   - Add tests for new scenarios
   - Verify mock responses are used correctly

### Custom Validation

1. **Message Analysis**
   ```python
   # Add new message patterns
   analyzer = MessageAnalyzer()
   analyzer.patterns["new_category"] = ["indicator1", "indicator2"]
   ```

2. **Format Validation**
   ```python
   # Add new format patterns
   format_patterns = {
       "custom_format": r"pattern_regex_here"
   }
   ```

3. **Behavioral Checks**
   ```python
   # Add custom validation logic
   def validate_custom_behavior(framework):
       db_state = framework.get_database_state()
       # Custom validation logic
       return validation_result
   ```

### Debugging Tests

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Inspect Framework State**
   ```python
   # Get comprehensive state information
   summary = framework.get_simulation_summary()

   # Check API call logs
   api_logs = framework.api_sim.get_request_logs()

   # Examine database state
   db_state = framework.get_database_state()
   ```

3. **Save Debug Information**
   ```python
   import json
   with open("debug_output.json", "w") as f:
       json.dump(framework.get_simulation_summary(), f, indent=2, default=str)
   ```

## Troubleshooting

### Common Issues

**1. API Mock Not Working**
- Verify `tests/fixtures/api_responses/` exists with data
- Check if `scripts/capture_api_responses.py` was run successfully
- Ensure API mock is started before bot operations

**2. Time Control Issues**
- Verify time controller is started before time-dependent operations
- Check that datetime imports are being patched correctly
- Ensure time advancement happens before polling checks

**3. Database Isolation Problems**
- Confirm test database is separate from production
- Verify cleanup between tests
- Check database transaction handling

**4. Discord Simulation Failures**
- Ensure cogs are loaded correctly into mock bot
- Verify command routing is working
- Check message capture and analysis logic

### Performance Considerations

**Test Speed Optimization**
- Use `create_fast_mock()` for unit tests
- Minimize time advancement steps
- Use smaller datasets when possible

**Memory Usage**
- Clear message histories between tests
- Reset framework state for independent tests
- Manage captured response data size

### Integration with CI/CD

**GitHub Actions Configuration**
```yaml
- name: Run Simulation Tests
  run: |
    pytest tests/simulation/ -m "simulation and not slow" --tb=short
```

**Test Data Management**
- Include captured responses in version control
- Refresh responses periodically (monthly/quarterly)
- Monitor response data size and relevance

## Framework Benefits

### Comprehensive Coverage

The simulation framework provides unprecedented test coverage:

- **End-to-End Validation**: Complete user journeys from command to notification
- **Realistic Data**: Uses actual API responses for authentic testing
- **Temporal Testing**: Validates time-dependent behavior without waiting
- **Error Scenarios**: Comprehensive error handling validation
- **Integration Verification**: Tests component interaction patterns

### Development Efficiency

- **Fast Iteration**: No waiting for real-time polling or API delays
- **Isolated Testing**: No dependencies on external services
- **Deterministic Results**: Consistent, reproducible test outcomes
- **Debugging Support**: Comprehensive logging and state inspection
- **Parallel Execution**: Tests can run concurrently without interference

### Quality Assurance

- **Regression Prevention**: Catches breaking changes early
- **Behavioral Validation**: Ensures bot responds appropriately
- **Performance Monitoring**: Tracks response times and resource usage
- **API Contract Verification**: Validates external service integration
- **User Experience Testing**: Simulates real user interactions

The DisPinMap Simulation Testing Framework represents a sophisticated approach to testing complex, time-dependent, multi-service applications. By providing realistic simulation of all external dependencies while maintaining fast execution and deterministic results, it enables comprehensive quality assurance for the Discord bot's functionality.

Ready to commence testing operations, sir! Like a well-calibrated chronometer, this simulation framework ensures your bot's temporal accuracy across all dimensions of operation!
