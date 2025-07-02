# Database Schema Redesign Plan

**Issues**: #78, #81 **Branch**: `feature/schema-redesign-issues-78-81`
**Approach**: Complete schema redesign with fresh database start (no data
migration)

## Overview

This plan implements a comprehensive database schema redesign to resolve
architectural issues with data overloading in the `target_name` field and
inconsistent data access patterns. We will create a new, properly normalized
schema and start with a fresh database (no data migration required).

## Current Problems Being Solved

1. **Data Overloading**: `target_name` stores different data types (names vs
   coordinates)
2. **Type Confusion**: 'city' targets cause crashes, should be 'geographic'
3. **No Coordinate Validation**: String-based coordinates prevent proper
   validation
4. **Inconsistent Access**: Different fields used for different target types
5. **Constraint Issues**: Duplicate geographic targets possible

## New Schema Design

### MonitoringTarget Table (Redesigned)

```sql
CREATE TABLE monitoring_targets (
    id INTEGER PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    target_type TEXT CHECK (target_type IN ('location', 'geographic')) NOT NULL,
    display_name TEXT NOT NULL,  -- Always human-readable name for users

    -- Location-specific fields (for PinballMap locations)
    location_id INTEGER,  -- PinballMap location ID

    -- Geographic fields (for coordinate-based monitoring)
    latitude REAL,
    longitude REAL,
    radius_miles INTEGER DEFAULT 25,

    -- Settings (unchanged)
    poll_rate_minutes INTEGER DEFAULT 60,
    notification_types TEXT DEFAULT 'machines',
    last_checked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Data integrity constraints
    CONSTRAINT target_data_check CHECK (
        (target_type = 'location' AND location_id IS NOT NULL AND latitude IS NULL)
        OR
        (target_type = 'geographic' AND location_id IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL AND radius_miles IS NOT NULL)
    ),
    CONSTRAINT valid_coordinates CHECK (
        latitude IS NULL OR (latitude BETWEEN -90 AND 90)
    ),
    CONSTRAINT valid_longitude CHECK (
        longitude IS NULL OR (longitude BETWEEN -180 AND 180)
    ),
    CONSTRAINT valid_radius CHECK (
        radius_miles IS NULL OR (radius_miles BETWEEN 1 AND 100)
    ),

    -- Uniqueness constraints
    CONSTRAINT unique_location UNIQUE (channel_id, location_id),
    CONSTRAINT unique_geographic UNIQUE (channel_id, latitude, longitude, radius_miles),

    FOREIGN KEY(channel_id) REFERENCES channel_configs (channel_id)
);
```

### Key Design Principles

1. **Single Responsibility**: Each field has one clear purpose
2. **Type Safety**: Proper data types with validation constraints
3. **Clear Semantics**: `display_name` always human-readable, coordinates always
   numeric
4. **Extensibility**: Easy to add new target types or geographic features
5. **Data Integrity**: Comprehensive constraints prevent invalid data

## Implementation Status

### ✅ COMPLETED PHASES

#### ✅ Phase 1: Schema Models & Validation

- **File**: `src/models.py` (updated directly, not temporary)
- ✅ New SQLAlchemy models with comprehensive constraints
- ✅ Validation methods and helper functions
- ✅ Data integrity constraints and proper types

#### ✅ Phase 2: Code Refactoring

- **File**: `src/database.py` - ✅ Updated for new schema
- **File**: `src/models.py` - ✅ Replaced with new schema models
- **File**: `src/cogs/command_handler.py` - ✅ Refactored for new schema
- **File**: `src/cogs/runner.py` - ✅ Updated coordinate handling
- **File**: `src/notifier.py` - ✅ Updated API integration

### 🟡 CURRENT PHASE: Testing & Alembic

#### 🟡 Phase 3.1: Unit Test Updates (In Progress)

- 🟡 Update all `tests/unit/*.py` files for new schema (15 files)
- 🟡 Fix field name changes (`target_name` → `display_name`)
- 🟡 Update mock data structures and test fixtures
- 🟡 Update database operation tests for new method signatures

#### ❌ Phase 3.2: Integration Test Updates (Pending)

- Update all `tests/integration/*.py` files for new schema
- Fix end-to-end workflows with new coordinate handling
- Update API integration tests for geographic vs location targets
- Test runner functionality with new data patterns
- Integration test `tests/integration/test_commands_e2e.py` needs further changes:
  - Update all command invocations to use the correct subcommand methods or simulate Discord command invocation as appropriate for the test framework.
  - Replace all references to the old schema field `target_name` with `display_name` and update any other schema field usages to match the new schema.
  - Ensure all test code that instantiates `MonitoringTarget` or calls `add_monitoring_target` uses the new schema fields.
  - Review and update any other test logic that assumes the old schema or command structure.

#### ❌ Phase 3.3: Migration Test Updates (Pending)

- Update `tests/migration/*.py` files for new approach
- Remove data transformation tests (not needed)
- Focus on fresh schema validation tests

### ❌ REMAINING PHASES

#### ❌ Phase 4: Alembic Baseline Creation

- **Fresh Start Approach**: Remove all existing migration files
- Generate new baseline migration from current `models.py`
- Create comprehensive initial migration with all constraints
- Test baseline migration on empty database

#### ❌ Phase 5: Documentation & Cleanup

- **File**: `docs/DATABASE.md` - Update schema documentation
- **File**: `USER_DOCUMENTATION.md` - Verify examples still work
- **File**: `docs/DEVELOPER_HANDBOOK.md` - Update architecture docs
- Clean up temporary files (`models_new.py`, etc.)
- Update directory-specific `CLAUDE.md` files

## Fresh Database Deployment Strategy

### Production Deployment Process

1. **Pre-Deployment**:
   - Ensure all tests pass with new schema
   - Generate fresh Alembic baseline migration
   - Create deployment checklist

2. **Deployment Execution**:
   - Stop bot temporarily (maintenance mode)
   - **Wipe existing database completely**
   - Create fresh database with new schema using Alembic
   - Start bot with empty database (fresh start)
   - Verify all functionality works

3. **Post-Deployment**:
   - Monitor for errors or issues
   - Verify all commands work correctly
   - Users can re-add their monitoring targets as needed

### Fresh Start Benefits

- **No Data Migration Complexity**: Eliminates transformation pipeline risks
- **Clean Slate**: No legacy data inconsistencies
- **Simplified Deployment**: Single step database creation
- **User Re-engagement**: Users re-add targets using improved commands

## Risk Mitigation

### Technical Risks

1. **Data Loss**: Comprehensive testing with production copies
2. **Downtime**: Minimize by pre-testing entire pipeline
3. **Performance**: Benchmark new schema against old
4. **Rollback**: Maintain complete rollback capability

### Operational Risks

1. **User Impact**: Ensure no user-visible changes
2. **Command Changes**: Maintain backward compatibility
3. **API Compatibility**: Ensure all API integrations work
4. **Monitoring**: Add validation monitoring post-migration

## Success Criteria

### Technical Success

- [ ] All existing functionality preserved with new schema
- [ ] New schema constraints working correctly
- [ ] No performance degradation
- [ ] All tests passing (unit, integration, migration)
- [ ] Fresh Alembic baseline migration created

### User Experience Success

- [ ] All commands work as documented
- [ ] No user-visible changes in command behavior
- [ ] Export/import functionality works with new schema
- [ ] Users can seamlessly re-add monitoring targets

### Code Quality Success

- [ ] Cleaner, more maintainable code
- [ ] Proper separation of concerns
- [ ] Type safety and validation
- [ ] Comprehensive test coverage
- [ ] Updated documentation

## Revised Timeline Summary

| Phase                      | Status     | Duration     | Agent Assignment     |
| -------------------------- | ---------- | ------------ | -------------------- |
| 1-2. Schema & Code         | ✅ DONE    | 5 days       | Completed            |
| 3.1. Unit Test Updates     | 🟡 ACTIVE  | 2-3 days     | Agent 1: Unit Tests  |
| 3.2. Integration Tests     | ❌ PENDING | 2-3 days     | Agent 2: Integration |
| 3.3. Migration Tests       | ❌ PENDING | 1 day        | Agent 2: Integration |
| 4. Alembic Baseline        | ❌ PENDING | 1 day        | Agent 3: Alembic     |
| 5. Documentation & Cleanup | ❌ PENDING | 1-2 days     | Agent 4: Docs        |
| **Remaining**              | **ACTIVE** | **5-7 days** | **Multi-agent**      |

## Multi-Agent Work Division

### Agent 1: Unit Test Specialist (CURRENT)

**Duration:** 2-3 days
**Files:** All `tests/unit/*.py` files (15 files need updates) **Tasks:**

- ✅ `tests/unit/test_database_models.py` - Updated for new schema
- 🟡 `tests/unit/test_command_handler.py` - Fix field name changes
- ❌ Remaining 13 unit test files - systematic schema updates
- Update mock data structures and test fixtures
- Ensure 100% unit test coverage passes

### Agent 2: Integration Test Specialist

**Duration:** 2-3 days (starts after Agent 1 ~80% complete) **Files:** All
`tests/integration/*.py` and `tests/migration/*.py` **Tasks:**

- Update integration tests for new schema fields and constraints
- Fix end-to-end workflows with new coordinate handling
- Update API integration tests for geographic vs location targets
- Update/simplify migration tests for fresh database approach
- Test runner functionality with new data patterns
- Integration test `tests/integration/test_commands_e2e.py` needs further changes:
  - Update all command invocations to use the correct subcommand methods or simulate Discord command invocation as appropriate for the test framework.
  - Replace all references to the old schema field `target_name` with `display_name` and update any other schema field usages to match the new schema.
  - Ensure all test code that instantiates `MonitoringTarget` or calls `add_monitoring_target` uses the new schema fields.
  - Review and update any other test logic that assumes the old schema or command structure.

### Agent 3: Alembic Baseline Specialist

**Duration:** 1 day (can work in parallel) **Files:** `alembic/` directory
**Tasks:**

- **Reset Alembic completely**: Remove all existing migration files
- Generate fresh baseline migration from current `models.py`
- Create comprehensive initial migration with all constraints
- Test baseline migration creation and application on empty database
- Document fresh-start database approach

### Agent 4: Documentation & Cleanup Specialist

**Duration:** 1-2 days (can work in parallel) **Files:** Documentation, cleanup
**Tasks:**

- Update `docs/DATABASE.md` with new schema documentation
- Update any affected user documentation
- Clean up temporary files (`models_new.py`, etc.)
- Update directory-specific `CLAUDE.md` files with new patterns
- Create deployment notes for fresh database setup

## Coordination Strategy

- Agent 1 provides foundation for Agent 2 (unit tests validate integration)
- Agents 3 & 4 work independently in parallel
- Final verification requires all agents coordinating on full test suite
- Ready for fresh database deployment once all agents complete

## Commit Strategy

Following conventional commits and small, atomic changes:

- ✅ `feat: add new schema models with validation constraints`
- ✅ `refactor: update database layer for new schema`
- ✅ `refactor: update command handlers for new schema`
- ✅ `refactor: update runner logic for new schema`
- 🟡 `test: update unit tests for new schema`
- ❌ `test: update integration tests for new schema`
- ❌ `feat: create fresh Alembic baseline migration`
- ❌ `docs: update documentation for new schema`
- ❌ `feat: complete schema redesign with fresh database`

Each commit will be small, focused, and independently testable following the
project's TDD principles.
