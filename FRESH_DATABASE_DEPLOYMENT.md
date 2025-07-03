# Fresh Database Deployment Guide

**Schema Redesign Project - Issues #78, #81**

This document outlines the fresh-start database deployment approach for the schema redesign project.

## Overview

The schema redesign project has adopted a **fresh baseline approach** instead of traditional data migration. This means:

- **Complete database reset**: The existing database is wiped clean
- **New baseline migration**: A single migration creates the complete new schema
- **No data preservation**: Users will need to re-add their monitoring targets
- **Clean slate**: No legacy data inconsistencies or migration complexities

## Fresh-Start Benefits

### Technical Benefits
- **No Migration Complexity**: Eliminates complex data transformation pipelines
- **Clean Architecture**: New schema is free from legacy constraints
- **Simplified Deployment**: Single-step database creation process
- **Consistent Data**: No mixed old/new data patterns
- **Validation Enforcement**: All new data follows strict validation rules

### Operational Benefits
- **Faster Deployment**: No time-consuming data migration process
- **Lower Risk**: Eliminates data transformation errors
- **Easier Rollback**: Simple revert to previous version
- **Clear Testing**: Test against known clean state

## New Schema Overview

The redesigned schema includes three main tables:

### 1. ChannelConfig
- Channel-specific configuration and settings
- Polling rates and notification preferences
- Activity tracking and timestamps

### 2. MonitoringTarget (Redesigned)
- **Normalized design**: Separate fields for different target types
- **Type safety**: `target_type` field with enum validation
- **Clear semantics**: `display_name` always human-readable
- **Coordinate validation**: Proper numeric lat/lon with range checks
- **Data integrity**: Comprehensive constraints prevent invalid data

### 3. SeenSubmission
- Tracks processed submissions to prevent duplicates
- Channel-specific submission tracking

## Deployment Process

### Pre-Deployment Checklist
- [ ] All tests pass with new schema
- [ ] Fresh baseline migration generated
- [ ] Backup procedures documented
- [ ] Rollback plan prepared
- [ ] User communication plan ready

### Deployment Steps

1. **Preparation**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Verify migration status
   alembic current
   alembic history
   ```

2. **Database Reset**
   ```bash
   # Stop the application
   # Remove existing database file
   rm -f production_database.db
   ```

3. **Apply New Schema**
   ```bash
   # Apply the baseline migration
   alembic upgrade head
   
   # Verify schema creation
   alembic current
   ```

4. **Application Startup**
   ```bash
   # Start application with fresh database
   # All tables are created and ready
   ```

5. **Post-Deployment Verification**
   - Verify all commands work correctly
   - Test target addition with both location and geographic types
   - Confirm constraint validation is working
   - Monitor for any errors or issues

### Production Environment Variables

The deployment uses the following configuration:
- `DATABASE_PATH`: Path to the SQLite database file
- Database URL: Configured automatically via `alembic/env.py`

## Migration File Details

### Baseline Migration: `9275fe03c648_create_initial_baseline_from_new_schema.py`

This migration creates:
- **channel_configs** table with all configuration fields
- **monitoring_targets** table with the new normalized schema
- **seen_submissions** table for duplicate tracking
- **All constraints**: Check constraints, unique constraints, foreign keys
- **Proper data types**: BigInteger for Discord IDs, Float for coordinates
- **Validation rules**: Coordinate ranges, target type validation, data consistency

## User Impact and Communication

### What Users Need to Know
- **Brief downtime**: During database reset and migration
- **Re-add targets**: Previous monitoring targets will need to be added again
- **Improved commands**: New `!add location` and `!add geographic` subcommands
- **Better validation**: Invalid coordinates or data will be caught early

### User Communication Template
```
🔧 **Database Upgrade Notice**

We're upgrading our database to improve reliability and add new features!

**What's happening:**
- Brief maintenance downtime
- Fresh database with improved schema
- All monitoring targets will need to be re-added

**What's improved:**
- Better validation of coordinates and locations
- More reliable data storage
- Foundation for future features

**Action needed:**
After the upgrade, please re-add your monitoring targets using:
- `!add location <location_name>` for specific locations
- `!add geographic <lat> <lon> [radius]` for coordinate areas

Thank you for your patience! 🤖
```

## Rollback Procedures

### If Issues Occur During Deployment

1. **Stop the new version**
2. **Restore from backup** (if available)
3. **Revert to previous application version**
4. **Investigate and fix issues**
5. **Re-attempt deployment when ready**

### Rollback Commands
```bash
# Stop current application
# Restore previous database
cp database_backup.db production_database.db

# Revert to previous application version
git checkout previous_working_commit

# Restart application
```

## Monitoring and Validation

### Post-Deployment Monitoring
- Monitor application logs for errors
- Verify command functionality
- Check constraint validation
- Monitor user feedback

### Validation Tests
```bash
# Test location target addition
!add location "Test Location"

# Test geographic target addition  
!add geographic 40.7128 -74.0060 25

# Test constraint validation (should fail)
!add geographic 200 300 5  # Invalid coordinates
```

## Success Criteria

### Technical Success
- [ ] Database created successfully from baseline migration
- [ ] All tables and constraints present
- [ ] No migration errors or warnings
- [ ] All application functions work correctly
- [ ] Performance meets or exceeds previous version

### User Experience Success
- [ ] All commands work as documented
- [ ] Coordinate validation prevents invalid data
- [ ] Users can successfully re-add monitoring targets
- [ ] No user-visible functionality regressions

## Conclusion

The fresh-start approach provides a clean foundation for the redesigned schema while eliminating the complexity and risks associated with data migration. This approach ensures data integrity, simplifies deployment, and provides a solid foundation for future enhancements.

For technical details about the schema design, see the `SCHEMA_REDESIGN_PLAN.md` document.