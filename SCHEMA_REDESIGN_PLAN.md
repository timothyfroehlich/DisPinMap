# Database Schema Redesign Plan
**Issues**: #78, #81
**Branch**: `feature/schema-redesign-issues-78-81`
**Approach**: Complete schema redesign with fresh database start

## Overview

This plan implements a comprehensive database schema redesign to resolve architectural issues with data overloading in the `target_name` field and inconsistent data access patterns. We will create a new, properly normalized schema and migrate existing production data.

## Current Problems Being Solved

1. **Data Overloading**: `target_name` stores different data types (names vs coordinates)
2. **Type Confusion**: 'city' targets cause crashes, should be 'geographic'
3. **No Coordinate Validation**: String-based coordinates prevent proper validation
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
3. **Clear Semantics**: `display_name` always human-readable, coordinates always numeric
4. **Extensibility**: Easy to add new target types or geographic features
5. **Data Integrity**: Comprehensive constraints prevent invalid data

## Implementation Phases

### Phase 1: Test Development & Schema Validation (3 days)

#### 1.1 Create New Model Classes
- **File**: `src/models_new.py` (temporary)
- Create new SQLAlchemy models with proper constraints
- Include validation methods and helper functions

#### 1.2 Data Transformation Pipeline Tests
- **File**: `tests/migration/test_data_transformation.py`
- Test export from current schema
- Test transformation logic for each target type
- Test import to new schema with validation

#### 1.3 Schema Validation Tests
- **File**: `tests/migration/test_new_schema.py`
- Test all constraints work correctly
- Test data integrity rules
- Test edge cases and invalid data rejection

#### 1.4 Production Data Copy Testing
- Download latest production database backup
- Run transformation pipeline on real data
- Validate all targets can be converted successfully
- Document any data quality issues found

### Phase 2: Data Migration Pipeline (3 days)

#### 2.1 Export Pipeline
- **File**: `scripts/export_current_data.py`
- Export all monitoring targets to JSON format
- Include metadata for validation
- Create data integrity checksums

#### 2.2 Transformation Pipeline
- **File**: `scripts/transform_schema_data.py`
- **Location Targets**:
  - `location_id` → `location_id` (unchanged)
  - `target_name` → `display_name` (unchanged)
  - `target_type` → `location` (unchanged)
- **Geographic Targets** (city/latlong):
  - Parse coordinates from `target_name`: "30.26715,-97.74306,5"
  - Extract: `latitude=30.26715`, `longitude=-97.74306`, `radius_miles=5`
  - Generate `display_name` from reverse geocoding or format coordinates
  - Set `target_type='geographic'`
- **Data Validation**: Verify all coordinates are valid
- **Conflict Resolution**: Handle any duplicate geographic targets

#### 2.3 Import Pipeline
- **File**: `scripts/import_new_schema.py`
- Create new database with new schema
- Import transformed data with validation
- Run integrity checks and constraint validation
- Generate import report with statistics

#### 2.4 Rollback Procedures
- **File**: `scripts/rollback_schema.py`
- Export data from new schema back to old format
- Create emergency rollback database
- Document rollback procedures

### Phase 3: Code Refactoring (5 days)

#### 3.1 Database Layer Updates
- **File**: `src/database.py`
- Update all CRUD operations for new schema
- Add helper methods for coordinate handling
- Update target retrieval to use appropriate fields
- Add validation for coordinate inputs

#### 3.2 Model Updates
- **File**: `src/models.py`
- Replace with new schema models
- Add validation methods
- Add helper methods for coordinate formatting

#### 3.3 Command Handler Refactoring
- **File**: `src/cogs/command_handler.py`
- **Add Commands**:
  - Location: Use `location_id` and `display_name`
  - City: Geocode and create geographic target (not city!)
  - Coordinates: Use numeric `latitude`, `longitude`, `radius_miles`
- **List Command**: Format display using `display_name` for all targets
- **Remove Command**: Update to work with new schema
- **Export Command**: Generate commands using new field structure

#### 3.4 Runner Logic Updates
- **File**: `src/cogs/runner.py`
- Remove all 'city' target type handling (should not exist)
- Update coordinate parsing to use numeric fields
- Simplify target processing with consistent data access
- Update API calls to use appropriate fields

#### 3.5 API Integration Updates
- **File**: `src/api.py`
- Update coordinate-based API calls to use numeric fields
- Update location-based API calls to use `location_id`
- Remove coordinate string parsing logic

### Phase 4: Testing & Integration (4 days)

#### 4.1 Unit Test Updates
- Update all existing tests for new schema
- Add tests for new constraint validations
- Test coordinate validation and edge cases
- Test data access patterns

#### 4.2 Integration Testing
- **File**: `tests/integration/test_schema_e2e.py`
- End-to-end testing with transformed production data
- Test all command flows with new schema
- Test runner functionality with real data
- Verify API integrations work correctly

#### 4.3 User Journey Testing
- **File**: `tests/simulation/test_new_schema_journeys.py`
- Test complete user workflows with new schema
- Verify all commands work as documented in USER_DOCUMENTATION.md
- Test edge cases and error handling

#### 4.4 Performance Testing
- Compare query performance between old and new schema
- Test geographic coordinate queries
- Validate that all operations are at least as fast as before

### Phase 5: Documentation & Deployment (2 days)

#### 5.1 Documentation Updates
- **File**: `docs/DATABASE.md`
  - Update schema documentation
  - Add new constraint explanations
  - Update example queries
- **File**: `USER_DOCUMENTATION.md`
  - Verify all examples still work
  - Update any changes in command behavior
- **File**: `docs/DEVELOPER_HANDBOOK.md`
  - Update architecture documentation
  - Add new data access patterns

#### 5.2 Migration Documentation
- **File**: `docs/SCHEMA_MIGRATION.md`
  - Document the migration process
  - Include rollback procedures
  - Add troubleshooting guide

#### 5.3 Deployment Preparation
- Create deployment checklist
- Prepare monitoring for migration
- Create validation scripts for production deployment
- Document post-deployment verification steps

## Data Migration Strategy

### Production Migration Process

1. **Pre-Migration**:
   - Download latest production backup
   - Run full transformation pipeline on copy
   - Validate all data transforms correctly
   - Create rollback database

2. **Migration Execution**:
   - Stop bot temporarily (maintenance mode)
   - Export current production data
   - Transform data using validated pipeline
   - Create new database with new schema
   - Import transformed data
   - Validate data integrity

3. **Post-Migration**:
   - Start bot with new schema
   - Monitor for errors or issues
   - Verify all functionality works
   - Keep rollback database available for 48 hours

### Validation Criteria

- **Data Completeness**: All targets successfully migrated
- **Functionality**: All commands work as before
- **Performance**: No performance degradation
- **Data Integrity**: All constraints and validations work
- **User Experience**: No changes visible to users

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
- [ ] All production data successfully migrated
- [ ] All existing functionality preserved
- [ ] New schema constraints working correctly
- [ ] No performance degradation
- [ ] All tests passing

### User Experience Success
- [ ] All commands work as documented
- [ ] No user-visible changes in behavior
- [ ] All existing monitoring targets continue working
- [ ] Export/import functionality works with new schema

### Code Quality Success
- [ ] Cleaner, more maintainable code
- [ ] Proper separation of concerns
- [ ] Type safety and validation
- [ ] Comprehensive test coverage
- [ ] Updated documentation

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Test Development | 3 days | None |
| 2. Migration Pipeline | 3 days | Phase 1 complete |
| 3. Code Refactoring | 5 days | Phase 2 complete |
| 4. Testing & Integration | 4 days | Phase 3 complete |
| 5. Documentation & Deployment | 2 days | Phase 4 complete |
| **Total** | **17 days** | Sequential execution |

## Commit Strategy

Following conventional commits and small, atomic changes:

- `feat: add new schema models with validation constraints`
- `test: add data transformation pipeline tests`
- `feat: implement data export/transform/import pipeline`
- `refactor: update database layer for new schema`
- `refactor: update command handlers for new schema`
- `refactor: update runner logic for new schema`
- `test: add comprehensive integration tests for new schema`
- `docs: update documentation for new schema`
- `feat: complete schema redesign migration`

Each commit will be small, focused, and independently testable following the project's TDD principles.
