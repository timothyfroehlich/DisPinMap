# Database Migration Agent Instructions

## CRITICAL: Recent Migration Impact

**Migration `5c8e4212f5ed`** renamed `target_data` → `location_id`

**IMPORTANT**: Issue #68 shows some code still uses old field name

- ❌ `target["target_data"]` causes KeyError in production
- ✅ Use `target["location_id"]` everywhere

## Key Files

- **env.py** - Migration environment, database URL configuration
- **script.py.mako** - Template for new migration files
- **versions/** - Individual migration scripts (chronological order)

## Database Schema

```sql
-- ChannelConfig: Discord channel monitoring settings
CREATE TABLE channel_configs (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT,
    poll_rate_minutes INTEGER DEFAULT 60,
    notification_type TEXT DEFAULT 'machines',
    is_active BOOLEAN DEFAULT FALSE  -- See Issue #47
);

-- MonitoringTarget: Individual locations/cities to monitor
CREATE TABLE monitoring_targets (
    id INTEGER PRIMARY KEY,
    channel_id BIGINT,
    target_type TEXT,  -- 'location', 'city', 'coordinates'
    target_name TEXT,
    location_id INTEGER,  -- NEW NAME (was target_data)
    radius_miles INTEGER
);
```

## Common Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Check current state
alembic current

# Rollback one migration
alembic downgrade -1

# Show migration history
alembic history
```

## Database URL Configuration

- **Development**: Uses `DATABASE_PATH` environment variable
- **Production**: Set via environment or alembic.ini
- **Testing**: Temporary SQLite files per test worker

## Migration Best Practices

- **Test both up and down**: Ensure migrations are reversible
- **Data compatibility**: Consider existing data when changing schemas
- **Code updates**: Update all code references when renaming fields
- **Database compatibility**: Ensure migrations work correctly with SQLite

## Current Schema Issues

**Issue #47**: `is_active` defaults to `False` causing silent monitoring
failures

- Channels with targets but `is_active=False` are skipped silently
- Consider changing default to `True` to prevent confusion

## Troubleshooting

```bash
# Reset to clean state (DESTRUCTIVE)
alembic downgrade base
alembic upgrade head

# Check for field name issues
grep -r "target_data" ../src/  # Should return nothing!

# Validate migration integrity
alembic check
```
