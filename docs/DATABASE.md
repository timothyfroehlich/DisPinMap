# Database Architecture Guide

This document provides comprehensive information about the DisPinMap database
architecture, migration procedures, and operational details.

## Architecture Overview

### Database Technology Stack

- **Primary Database**: SQLite 3
- **Backup System**: Litestream continuous replication
- **Storage Backend**: Google Cloud Storage (GCS)
- **Migration Framework**: Alembic (SQLAlchemy-based)

### Why SQLite + Litestream?

**SQLite Benefits**:

- Cost-effective (no managed database service costs)
- Sufficient for Discord bot workloads
- Simple deployment and maintenance
- ACID compliance and reliability

**Litestream Benefits**:

- Continuous backup to cloud storage
- Point-in-time recovery capabilities
- Handles container restarts and crashes
- Minimal operational overhead

## Production Database Access

### Current Deployment Location

- **Environment**: Google Cloud Run
- **Service URL**: https://dispinmap-bot-wos45oz7vq-uc.a.run.app
- **Database File**: `/tmp/pinball_bot.db` (in container)
- **Backup Location**: `gs://dispinmap-bot-sqlite-backups/db/`

### Accessing Production Data

#### Method 1: Download Latest Backup

```bash
# List available backup generations
gsutil ls gs://dispinmap-bot-sqlite-backups/db/generations/

# Find the latest generation
LATEST_GEN=$(gsutil ls gs://dispinmap-bot-sqlite-backups/db/generations/ | tail -1)

# Download snapshot
gsutil cp ${LATEST_GEN}snapshots/00000000.snapshot.lz4 ./production_snapshot.lz4

# Decompress
lz4 -d production_snapshot.lz4 production_backup.db

# Access with SQLite
sqlite3 production_backup.db
```

#### Method 2: Container Access (Advanced)

```bash
# Get running container instance
CONTAINER_ID=$(gcloud run services describe dispinmap-bot --region=us-central1 --format="value(status.latestRevisionName)")

# Connect to container (requires Cloud Run admin access)
gcloud run services proxy dispinmap-bot --port=8080
```

## Normalized Schema (Current Implementation)

### Fresh Database Approach

As of the schema redesign, this project uses a **fresh database start** approach. The old schema has been completely replaced with a normalized design that resolves previous data overloading and constraint issues. No data migration is performed; users re-add their monitoring targets using the improved command structure.

### Database Tables

#### ChannelConfig Table

```sql
CREATE TABLE channel_configs (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    poll_rate_minutes INTEGER DEFAULT 60,
    notification_types VARCHAR DEFAULT 'machines',
    is_active BOOLEAN DEFAULT true,
    last_poll_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### MonitoringTarget Table (Normalized Schema)

```sql
CREATE TABLE monitoring_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    target_type VARCHAR NOT NULL CHECK (target_type IN ('location', 'geographic')),
    display_name VARCHAR NOT NULL,      -- Always human-readable name for users
    
    -- Location-specific fields (for PinballMap locations)
    location_id INTEGER,               -- PinballMap location ID
    
    -- Geographic fields (for coordinate-based monitoring)
    latitude REAL,                     -- Decimal degrees (-90 to 90)
    longitude REAL,                    -- Decimal degrees (-180 to 180)
    radius_miles INTEGER DEFAULT 25,   -- Search radius (1 to 100)
    
    -- Settings
    poll_rate_minutes INTEGER DEFAULT 60,
    notification_types VARCHAR DEFAULT 'machines',
    last_checked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Data integrity constraints
    CONSTRAINT target_data_check CHECK (
        (target_type = 'location' AND location_id IS NOT NULL AND latitude IS NULL AND longitude IS NULL)
        OR
        (target_type = 'geographic' AND location_id IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL)
    ),
    CONSTRAINT valid_latitude CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CONSTRAINT valid_longitude CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),
    CONSTRAINT valid_radius CHECK (radius_miles IS NULL OR (radius_miles >= 1 AND radius_miles <= 100)),
    
    -- Uniqueness constraints
    CONSTRAINT unique_location UNIQUE (channel_id, location_id),
    CONSTRAINT unique_geographic UNIQUE (channel_id, latitude, longitude),
    
    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id)
);
```

#### SeenSubmission Table

```sql
CREATE TABLE seen_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    submission_id BIGINT NOT NULL,
    seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_channel_submission UNIQUE (channel_id, submission_id),
    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id)
);
```

### Schema Design Principles

#### 1. Normalized Data Structure
- **Single Responsibility**: Each field has one clear purpose
- **Type Safety**: Proper data types with validation constraints  
- **Clear Semantics**: `display_name` always human-readable, coordinates always numeric
- **Extensibility**: Easy to add new target types or geographic features

#### 2. Target Type Differentiation

**Location Targets** (`target_type = 'location'`):
- **Purpose**: Monitor specific PinballMap locations
- **Required Fields**: `location_id`, `display_name`
- **Null Fields**: `latitude`, `longitude`, `radius_miles`
- **Example**: "Austin Pinball Collective" (location_id: 26454)

**Geographic Targets** (`target_type = 'geographic'`):
- **Purpose**: Monitor by coordinates and radius
- **Required Fields**: `latitude`, `longitude`, `radius_miles`, `display_name`
- **Null Fields**: `location_id`
- **Example**: "Austin, TX" (30.26715, -97.74306, 25 miles)

#### 3. Data Integrity Constraints
- **Target Data Validation**: Ensures location targets have location_id, geographic targets have coordinates
- **Coordinate Validation**: Latitude (-90 to 90), longitude (-180 to 180), radius (1 to 100 miles)
- **Uniqueness**: Prevents duplicate location or geographic targets per channel
- **Referential Integrity**: Foreign key relationships maintain data consistency

### Data Examples

```sql
-- Location monitoring (PinballMap location)
INSERT INTO monitoring_targets (channel_id, target_type, display_name, location_id)
VALUES (1377474091149164584, 'location', 'Austin Pinball Collective', 26454);

-- Geographic monitoring (coordinate-based)
INSERT INTO monitoring_targets (channel_id, target_type, display_name, latitude, longitude, radius_miles)
VALUES (1377474127648133130, 'geographic', 'Austin, TX', 30.26715, -97.74306, 25);

-- Geographic monitoring with custom radius
INSERT INTO monitoring_targets (channel_id, target_type, display_name, latitude, longitude, radius_miles)
VALUES (1377474127648133130, 'geographic', 'Downtown Portland', 45.5152, -122.6784, 10);
```

### Resolved Schema Issues

#### ✅ Data Overloading Eliminated
- **Previous Issue**: `target_name` stored different data types (names vs coordinates)
- **Solution**: Separate fields (`display_name`, `latitude`, `longitude`, `location_id`) with clear purposes

#### ✅ Type Confusion Resolved  
- **Previous Issue**: 'city' targets caused crashes, should be 'geographic'
- **Solution**: Only two valid target types: 'location' and 'geographic' with proper validation

#### ✅ Coordinate Validation Added
- **Previous Issue**: String-based coordinates prevented proper validation
- **Solution**: Numeric latitude/longitude fields with range constraints

#### ✅ Consistent Data Access
- **Previous Issue**: Different fields used for different target types
- **Solution**: Standardized field usage enforced by database constraints

#### ✅ Duplicate Prevention
- **Previous Issue**: Duplicate geographic targets possible
- **Solution**: Unique constraints on (channel_id, location_id) and (channel_id, latitude, longitude)

## Migration Management

### Alembic Configuration

#### Setup

```bash
# Initialize Alembic (already done)
alembic init alembic

# Configure for SQLite
# Edit alembic.ini: sqlalchemy.url = sqlite:///pinball_bot.db
# Edit alembic/env.py: from src.models import Base; target_metadata = Base.metadata
```

#### Environment Variables

- `SQLALCHEMY_URL`: Override database URL for migrations
- `LITESTREAM_BUCKET`: GCS bucket for backups
- `LITESTREAM_PATH`: Database file path

#### Common Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history

# Rollback to previous version
alembic downgrade -1
```

### SQLite-Specific Migration Considerations

Migrating schemas in SQLite requires special care due to its limited
`ALTER TABLE` support. Unlike other databases like PostgreSQL, you cannot simply
drop a constraint. Complex changes often require recreating the table, which
Alembic handles through "batch mode".

However, even with batch mode, complex, multi-step operations within a single
migration can fail silently or unreliably. The migration may be marked as
"applied" in the `alembic_version` table, but the schema changes (like new
constraints) will not be present in the database.

#### Golden Rules for SQLite Migrations

Based on experience, follow these rules to ensure safe and reliable migrations:

1.  **Keep Migrations Atomic:** Each migration script should perform only one
    small, distinct task (e.g., add a column, or copy data, or create a
    constraint). Do not combine these into a single script.
2.  **Separate Schema and Data Changes:** Never mix schema changes (like adding
    a column) and data changes (like populating that column) in the same
    `batch_alter_table` block. Perform them in separate steps, often in separate
    migration files.
3.  **Always Test on Production Data:** Before running a migration in
    production, always test it on a fresh copy of the production database
    (`production_snapshot.lz4`).
4.  **Revert Models First:** Before generating a new migration, ensure your
    SQLAlchemy models in `src/models.py` match the _current_ state of the
    production database. Make the model changes _after_ generating the script.
5.  **Trust, but Verify:** After running a migration, manually inspect the
    database schema with `.schema` to ensure the changes were actually applied.

#### Constraint Changes Require Batch Mode

SQLite doesn't support `ALTER TABLE` for constraints. Use batch mode:

```python
# In migration file
def upgrade():
    with op.batch_alter_table('table_name', schema=None) as batch_op:
        batch_op.drop_constraint('old_constraint', type_='unique')
        batch_op.create_unique_constraint('new_constraint', ['col1', 'col2'])
```

#### Data Migration Pattern

A safe pattern for migrations that involve changing a column and preserving its
data is to do it in multiple, distinct migration scripts.

**Migration 1: Add the new column**

```python
# revision: 1_add_new_column
def upgrade():
    op.add_column('table_name', sa.Column('new_col', sa.String()))
```

**Migration 2: Copy data to the new column**

```python
# revision: 2_copy_data
def upgrade():
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE table_name SET new_col = old_col"))
```

**Migration 3: Drop the old column and apply new constraints**

```python
# revision: 3_finalize_schema
def upgrade():
    with op.batch_alter_table('table_name') as batch_op:
        batch_op.drop_column('old_col')
        # And/or update constraints, etc.
```

## Backup and Recovery

### Litestream Configuration

See `litestream.yml` in project root:

```yaml
dbs:
  - path: ${LITESTREAM_PATH}
    replicas:
      - type: gcs
        bucket: ${LITESTREAM_BUCKET}
        path: db
        sync-interval: 1s
        retention: 72h
```

### Recovery Procedures

#### Restore from Backup

```bash
# Using Litestream (in container)
litestream restore -config /app/litestream.yml /tmp/pinball_bot.db

# Manual restore from GCS
gsutil cp gs://dispinmap-bot-sqlite-backups/db/generations/LATEST/snapshots/00000000.snapshot.lz4 ./
lz4 -d 00000000.snapshot.lz4 restored.db
```

#### Backup Validation

```bash
# Run validation script
python scripts/validate_litestream.py

# Manual validation
sqlite3 backup.db ".schema"
sqlite3 backup.db "SELECT COUNT(*) FROM monitoring_targets;"
```

## Development Workflow

### Local Development

1. **Use Production Backup**: Copy latest backup for realistic testing
2. **Run Migrations**: Test migrations on production data copy
3. **Validate Changes**: Ensure data integrity after migrations

### Migration Testing

```bash
# 1. Get production backup
gsutil cp gs://dispinmap-bot-sqlite-backups/db/generations/LATEST/snapshots/00000000.snapshot.lz4 ./
lz4 -d 00000000.snapshot.lz4 test_migration.db

# 2. Test migration
SQLALCHEMY_URL=sqlite:///test_migration.db alembic stamp 6f6f6afb1af3  # Current version
SQLALCHEMY_URL=sqlite:///test_migration.db alembic upgrade head

# 3. Validate results
sqlite3 test_migration.db ".schema monitoring_targets"
sqlite3 test_migration.db "SELECT COUNT(*) FROM monitoring_targets;"
```

### Production Deployment

1. **Container Update**: Migration runs automatically on container startup
2. **Litestream Backup**: Continuous backup ensures safety
3. **Rollback Available**: Can restore from pre-migration backup if needed

## Troubleshooting

### Common Issues

#### Migration Fails with "duplicate column"

- **Cause**: Model changes applied before migration created
- **Solution**: Reset models to production state, generate migration, then apply
  model changes

#### SQLite constraint errors

- **Cause**: Trying to use PostgreSQL-style ALTER TABLE
- **Solution**: Use Alembic batch mode with `render_as_batch=True`

#### Backup restoration fails

- **Cause**: Litestream version mismatch or configuration issues
- **Solution**: Use manual GCS download and lz4 decompression

### Useful Queries

```sql
-- Check table structure
PRAGMA table_info(monitoring_targets);

-- View constraints
SELECT sql FROM sqlite_master WHERE name='monitoring_targets';

-- Check data integrity
SELECT channel_id, target_type, target_data, COUNT(*) as count
FROM monitoring_targets
GROUP BY channel_id, target_type, target_data
HAVING COUNT(*) > 1;  -- Find duplicates

-- Migration version
SELECT version_num FROM alembic_version;
```

## Security Considerations

- **No Direct Database Access**: Database is inside container, not exposed
- **Backup Security**: GCS bucket uses Cloud Run service account authentication
- **Migration Safety**: Always test on backup copy first
- **Data Integrity**: Use transactions for multi-step migrations

## Performance Notes

- **SQLite Limitations**: Single writer, but sufficient for Discord bot workload
- **Backup Overhead**: Litestream adds minimal performance impact
- **Container Storage**: Database file is ephemeral, relies on Litestream for
  persistence
- **Recovery Time**: Fast restoration from GCS (typically < 30 seconds)
