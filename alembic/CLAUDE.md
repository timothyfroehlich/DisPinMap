# Database Migration Agent Instructions

## Schema Redesign: Fresh Database Approach

As of the schema redesign, this project uses a **fresh database start** approach. The old migration history has been replaced with a single baseline migration that creates the new normalized schema from scratch.

## Key Files

- **env.py** - Migration environment, database URL configuration
- **script.py.mako** - Template for new migration files
- **versions/** - Contains the new baseline migration (old migrations removed)

## Current Normalized Schema

```sql
-- ChannelConfig: Discord channel monitoring settings
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

-- MonitoringTarget: Normalized schema with proper constraints
CREATE TABLE monitoring_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    target_type VARCHAR NOT NULL CHECK (target_type IN ('location', 'geographic')),
    display_name VARCHAR NOT NULL,      -- Always human-readable name
    
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

-- SeenSubmission: Tracks processed submissions
CREATE TABLE seen_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id BIGINT NOT NULL,
    submission_id BIGINT NOT NULL,
    seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_channel_submission UNIQUE (channel_id, submission_id),
    FOREIGN KEY (channel_id) REFERENCES channel_configs (channel_id)
);
```

## Common Commands

```bash
# Apply baseline migration to fresh database
alembic upgrade head

# Check current state
alembic current

# Show migration history (should show single baseline)
alembic history

# Create future migrations (after baseline is established)
alembic revision --autogenerate -m "description of changes"
```

## Fresh Database Deployment Strategy

### Production Deployment Process

1. **Pre-Deployment**:
   - Ensure all tests pass with new schema
   - Fresh baseline migration is generated
   - Create deployment checklist

2. **Deployment Execution**:
   - Stop bot temporarily (maintenance mode)
   - **Wipe existing database completely**
   - Create fresh database with new schema using Alembic baseline
   - Start bot with empty database (fresh start)
   - Verify all functionality works

3. **Post-Deployment**:
   - Monitor for errors or issues
   - Verify all commands work correctly
   - Users can re-add their monitoring targets as needed

## Database URL Configuration

- **Development**: Uses `DATABASE_PATH` environment variable
- **Production**: Set via environment or alembic.ini
- **Testing**: Temporary SQLite files per test worker

## Migration Best Practices

- **Baseline Approach**: Start with clean slate rather than complex migrations
- **Fresh Start Benefits**: No legacy data inconsistencies or migration complexity
- **Code Alignment**: All code references updated to use new field names
- **Database Constraints**: Full validation enforced at database level

## Schema Design Improvements

✅ **Data Overloading Eliminated**: Separate fields for different data types
✅ **Type Safety**: Proper data types with validation constraints  
✅ **Clear Semantics**: `display_name` always human-readable, coordinates always numeric
✅ **Data Integrity**: Comprehensive constraints prevent invalid data
✅ **Uniqueness**: Prevents duplicate targets per channel

## Troubleshooting

```bash
# Apply fresh baseline to new database
alembic upgrade head

# Validate schema matches models
python -c "from src.models import Base; print('Schema validated')"

# Check for old field references (should return nothing)
grep -r "target_name\|target_data" ../src/

# Validate migration integrity
alembic check
```
