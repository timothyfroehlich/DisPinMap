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

## Current Status Analysis (as of 2025-07-02)

The schema redesign is well underway. The core application logic in `src/` has
been successfully updated to reflect the new, normalized schema as per the plan.

**The project is currently blocked in the testing phase.** Unit and integration
tests have not been fully updated to work with the new schema, which prevents
the final phases (Alembic baseline creation and documentation updates) from
starting.

- **Core Logic (`src/`)**: ✅ **Complete**. `models.py`, `database.py`, and
  `cogs/command_handler.py` align with the new schema.
- **Unit Tests (`tests/unit/`)**: 🟡 **In Progress but Blocked**. Files need
  systematic updates. Mocks and assertions are outdated.
- **Integration Tests (`tests/integration/`)**: ❌ **Pending/Blocked**. These
  tests are not aligned with the new schema or command structure and require
  significant updates. `test_commands_e2e.py` is the primary blocker.
- **Alembic Migrations (`alembic/`)**: ❌ **Pending**. Blocked by failing tests.
  The old migration files are still in place.
- **Documentation (`docs/`)**: ❌ **Pending**. Blocked by the incomplete
  implementation. `DATABASE.md` still describes the old schema.

The immediate priority is to update the test suite to unblock the rest of the
project.

## Implementation Status

### ✅ COMPLETED PHASES

#### ✅ Phase 1: Schema Models & Validation

- **File**: `src/models.py` - ✅ **Verified**. New SQLAlchemy models with
  comprehensive constraints are correctly implemented.

#### ✅ Phase 2: Code Refactoring

- **File**: `src/database.py` - ✅ **Verified**. Database layer is updated for
  the new schema.
- **File**: `src/cogs/command_handler.py` - ✅ **Verified**. Commands are
  refactored for the new schema.
- **Files**: `src/cogs/runner.py`, `src/notifier.py` - ✅ Assumed complete as
  per plan.

### 🔴 BLOCKED PHASE: Testing

The testing phase is the primary bottleneck. The existing tests are failing and
must be updated before proceeding.

#### 🟡 Phase 3.1: Unit Test Updates (In Progress)

- **Status**: Partially complete, but requires systematic review.
- **Task**: Update all `tests/unit/*.py` files to align with the new schema.
  This includes fixing field name changes (`target_name` → `display_name`),
  updating mock data structures, and aligning database operation tests with new
  method signatures.

#### ❌ Phase 3.2: Integration Test Updates (Pending)

- **Status**: Not started. This is a critical blocker.
- **Task**: Update all `tests/integration/*.py` files. `test_commands_e2e.py`
  requires a major rewrite to use the new `!add <subcommand>` structure and
  validate against the new schema.

#### ❌ Phase 3.3: Migration Test Updates (Pending)

- **Status**: Not started.
- **Task**: Update `tests/migration/*.py` to focus on fresh schema validation
  rather than data transformation.

### ❌ REMAINING PHASES (Blocked by Testing)

#### ❌ Phase 4: Alembic Baseline Creation

- **Status**: Pending.
- **Task**: Remove all existing migration files and generate a new baseline from
  the completed `src/models.py`.

#### ❌ Phase 5: Documentation & Cleanup

- **Status**: Pending.
- **Task**: Update `docs/DATABASE.md`, `USER_DOCUMENTATION.md`, and other
  relevant documentation.

## Parallel Work-streams for Independent Contributors

To accelerate the completion of the schema redesign, the remaining work has been
broken down into the following independent work-streams. Contributors can claim
a task and work on it in a separate feature branch.

---

#### **Task 1: Update Unit Tests (`tests/unit/`)**

- **Objective**: Ensure all unit tests pass by aligning them with the new schema
  and application logic.
- **Files to Modify**: All files within `tests/unit/`.
- **Key Activities**:
  1.  Create a new branch: `feature/fix-unit-tests`
  2.  Systematically update each test file in `tests/unit/`.
  3.  Modify mock objects to return data in the new schema format (e.g.,
      `display_name`, `location_id`, `latitude`, `longitude`).
  4.  Update assertions to check for the new fields.
  5.  Ensure that tests for `database.py` and `command_handler.py` correctly
      reflect the new method signatures and command structures.
- **Risk of Conflict**: **Low**. This task is self-contained within the
  `tests/unit/` directory.

---

#### **Task 2: Update Integration & Migration Tests (`tests/integration/` & `tests/migration/`)**

- **Objective**: Rewrite integration tests to validate the end-to-end
  functionality of the new schema and commands.
- **Files to Modify**: All files within `tests/integration/` and
  `tests/migration/`.
- **Key Activities**:
  1.  Create a new branch: `feature/fix-integration-tests`
  2.  Rewrite `tests/integration/test_commands_e2e.py` to use the new
      `!add <subcommand>` format.
  3.  Update database assertions to validate the new `MonitoringTarget` schema.
  4.  Ensure the `api_mocker` is used correctly to test interactions with
      external APIs.
  5.  Update `tests/migration/` to test the creation of a fresh database schema,
      removing any old data migration logic.
- **Risk of Conflict**: **Low**. This task is self-contained within the
  `tests/integration/` and `tests/migration/` directories.

---

#### **Task 3: Create Alembic Baseline (`alembic/`)**

- **Objective**: Reset the database migration history and create a single, clean
  baseline migration that reflects the new schema.
- **Files to Modify**: All files within `alembic/versions/`.
- **Key Activities**:
  1.  Create a new branch: `feature/create-alembic-baseline`
  2.  Delete all existing migration files in `alembic/versions/`.
  3.  Run
      `alembic revision --autogenerate -m "Create initial baseline from new schema"`
      to generate a new baseline migration.
  4.  Verify that the generated migration script correctly creates all tables
      and constraints as defined in `src/models.py`.
- **Risk of Conflict**: **Low**. This task is isolated to the `alembic/`
  directory. It can be done in parallel with the testing tasks but should only
  be merged after the tests are passing.

---

#### **Task 4: Update Documentation (`docs/`)**

- **Objective**: Update all project documentation to reflect the new database
  schema and any changes to user-facing commands.
- **Files to Modify**: `docs/DATABASE.md`, `USER_DOCUMENTATION.md`, and any
  other relevant files in `docs/`.
- **Key Activities**:
  1.  Create a new branch: `feature/update-documentation`
  2.  Update the schema diagram and descriptions in `docs/DATABASE.md`.
  3.  Review and update command examples in `USER_DOCUMENTATION.md` to ensure
      they are correct.
  4.  Update any architectural diagrams or descriptions in the developer
      handbook.
- **Risk of Conflict**: **Low**. This task is isolated to the `docs/` directory.

---

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

**Duration:** 2-3 days **Files:** All `tests/unit/*.py` files (15 files need
updates) **Tasks:**

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
- Integration test `tests/integration/test_commands_e2e.py` needs further
  changes:
  - Update all command invocations to use the correct subcommand methods or
    simulate Discord command invocation as appropriate for the test framework.
  - Replace all references to the old schema field `target_name` with
    `display_name` and update any other schema field usages to match the new
    schema.
  - Ensure all test code that instantiates `MonitoringTarget` or calls
    `add_monitoring_target` uses the new schema fields.
  - Review and update any other test logic that assumes the old schema or
    command structure.

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
