# Database Migration Agent Instructions

This document provides instructions for managing database migrations with Alembic.

**For detailed schema information, always refer to `docs/DATABASE.md`.**

## Key Files

- **env.py** - Migration environment, database URL configuration
- **script.py.mako** - Template for new migration files
- **versions/** - Contains all migration files

## Migration Workflow

From this point forward, all database schema changes must be managed through Alembic migrations. The initial database is created by the application, and subsequent changes are handled by migration scripts.

### Common Commands

```bash
# Create a new migration after changing models in src/models.py
alembic revision --autogenerate -m "Brief description of schema changes"

# Apply all migrations to the database
alembic upgrade head

# Check the current migration version of the database
alembic current

# Show migration history
alembic history

# Downgrade to a specific version (use with caution)
alembic downgrade -1
```

## Migration Best Practices

- **Keep Migrations Atomic**: Each migration script should perform one small, distinct task (e.g., add a column, create a constraint).
- **Separate Schema and Data Changes**: Do not mix schema changes (like adding a column) and data changes (like populating that column) in the same migration.
- **Always Test Migrations**: Before applying migrations in production, test them on a copy of the production database.
- **Verify After Applying**: After running `alembic upgrade head`, manually inspect the database schema to ensure the changes were applied correctly.

## Troubleshooting

```bash
# Validate that the current models match the database schema
# (This command may need to be adapted based on the current state)
python -c "from src.models import Base; print('Schema validated')"

# Check for old, problematic field references in the codebase
grep -r "target_name\|target_data" ../src/

# Check the integrity of the migration history
alembic check
```