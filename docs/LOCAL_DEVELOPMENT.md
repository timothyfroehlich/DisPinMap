# Local Development Guide

## Overview

The local development environment allows you to run and test the DisPinMap bot
on your local machine with:

- Production database data
- Console-based Discord interaction
- Enhanced logging and monitoring
- Zero Cloud Run costs during development

## Quick Start

```bash
# 1. Ensure virtual environment is active
source venv/bin/activate

# 2. Download production database (one-time setup)
python scripts/download_production_db.py

# 3. Start local development session
python src/local_dev.py
```

## Console Interface

### Overview

The console interface simulates Discord channel interaction through
stdin/stdout. You can type bot commands and see responses in real-time while the
bot continues normal monitoring operations.

### Command Types

#### Discord Bot Commands (prefix with `!`)

These are the same commands users would type in Discord:

```
!add location "Ground Kontrol"    # Add location monitoring
!list                             # Show all monitored targets
!check                           # Manual check all targets
!remove location "Ground Kontrol" # Remove location monitoring
!help                            # Show available commands
```

#### Console Special Commands (prefix with `.`)

These are local development utilities:

```
.quit      # Exit local development session gracefully
.health    # Show bot health status (Discord connection, database, monitoring loop)
.status    # Show monitoring statistics (target counts, recent additions)
.trigger   # Force immediate monitoring loop iteration
```

### Example Session

```
> !list
[11:30:15] [BOT] 📋 **Current monitoring targets (10 total):**
[11:30:15] [BOT] 🎯 Ground Kontrol (ID: 26454) - Channel: #pinball-oregon
[11:30:15] [BOT] 🎯 8-Bit Arcade (ID: 12345) - Channel: #pinball-oregon
...

> .health
[11:30:20] [BOT] 🏥 Bot Health Status:
[11:30:20] [BOT]    Discord: 🟢 Connected
[11:30:20] [BOT]    Database: 🟢 Connected (10 targets)
[11:30:20] [BOT]    Monitoring Loop: 🟢 Running (iteration #42)

> .trigger
[11:30:25] [BOT] 🔄 Triggering monitoring loop iteration...
[11:30:25] [MONITOR] 🔄 Monitor loop iteration #43 starting
[11:30:26] [BOT] ✅ Monitoring loop triggered

> .quit
[11:30:30] [BOT] 👋 Goodbye!
```

## Logging System

### Log File Location

All activity is logged to `logs/bot.log` with automatic rotation:

- Maximum file size: 10MB
- Backup files kept: 5
- Encoding: UTF-8

### Log Categories

- `[BOT]` - Main bot events and responses
- `[DISCORD]` - Discord connection events
- `[MONITOR]` - Monitoring loop activity
- `[CONSOLE]` - Console interface activity
- `[API]` - External API calls (PinballMap, etc.)

### Monitoring Logs

```bash
# Watch logs in real-time
tail -f logs/bot.log

# Monitor just monitoring loop activity
grep "MONITOR" logs/bot.log

# Check for errors
grep "ERROR" logs/bot.log

# See API calls
grep "API" logs/bot.log
```

### Example Log Output

```
[2025-07-04 11:58:54] [MONITOR] INFO - 🚀 Running immediate first check to avoid startup delay...
[2025-07-04 11:58:54] [MONITOR] INFO - 📋 Found 5 active channels with monitoring targets
[2025-07-04 11:58:54] [API] INFO - 🌐 API: location
[2025-07-04 11:58:54] [MONITOR] INFO - Polling channel 1377474091149164584...
```

## Database Access

### Production Data

The local environment uses a real copy of the production database:

- Downloaded from Litestream backups in GCS
- Includes all current monitoring targets and channel configurations
- Updated manually by running the download script

### Database Commands

```bash
# Download latest production data
python scripts/download_production_db.py

# The script will show you what it finds:
# Database contains 6 tables:
#   - alembic_version: 1 rows
#   - channel_configs: 5 rows
#   - monitoring_targets: 10 rows
#   - seen_submissions: 0 rows
```

## Monitoring Loop Testing

### Normal Operation

The monitoring loop runs automatically when the bot starts:

- Connects to Discord
- Starts monitoring all configured targets
- Makes real API calls to PinballMap
- Processes and logs all activity

### Manual Testing

```bash
# Force immediate monitoring check
> .trigger

# Check monitoring status
> .status

# View health information
> .health
```

### What to Monitor

- **Startup time**: Should connect within 3-5 seconds
- **API calls**: Should see successful PinballMap API requests
- **Database queries**: Should load targets and channels correctly
- **Error handling**: Monitor for any exceptions or connection issues

## Troubleshooting

### Common Issues

#### Console Not Responding

- **Cause**: Input thread may have stopped
- **Solution**: Restart local development session
- **Prevention**: Avoid Ctrl+D or EOF signals

#### Database Not Found

- **Cause**: Database file missing or corrupted
- **Solution**: Re-run `python scripts/download_production_db.py`
- **Check**: Verify `local_db/pinball_bot.db` exists and has size > 0

#### Discord Connection Errors

- **Cause**: Invalid or missing Discord token
- **Solution**: Verify `DISCORD_BOT_TOKEN` in `.env.local`
- **Check**: Token should start with `MTM3...`

#### Monitoring Loop Not Starting

- **Cause**: Database connection or cog loading issues
- **Solution**: Check logs for specific error messages
- **Debug**: Use `.health` command to see component status

### Environment Variables

Required in `.env.local`:

```bash
DISCORD_BOT_TOKEN=MTM3NjYyOTMzNzE0MjQ2MDQ0Ng.G9TOao...
DB_TYPE=sqlite
DATABASE_PATH=local_db/pinball_bot.db
LOCAL_DEV_MODE=true
LOG_LEVEL=DEBUG
```

### Log Analysis

```bash
# Check startup sequence
head -50 logs/bot.log

# Look for connection issues
grep -i "error\|fail\|exception" logs/bot.log

# Monitor API rate limiting
grep "rate" logs/bot.log

# Check memory usage patterns (if implemented)
grep -i "memory\|usage" logs/bot.log
```

## Development Workflow

### Typical Session

1. Start local development: `python src/local_dev.py`
2. Test console commands to verify functionality
3. Let monitoring loop run for extended period
4. Monitor logs for stability issues
5. Use `.quit` to exit gracefully

### Extended Testing

For long-term stability testing:

```bash
# Run in background with log capture
nohup python src/local_dev.py > local_dev_session.log 2>&1 &

# Monitor the session
tail -f local_dev_session.log
tail -f logs/bot.log

# Stop the session
# Find the process and kill gracefully
ps aux | grep local_dev.py
kill -TERM <pid>
```

### Debugging Cloud Run Issues

Use local development to:

1. Verify monitoring loop stability over 24+ hours
2. Identify memory leaks or connection issues
3. Test API rate limiting behavior
4. Validate database operations under load
5. Document findings for Cloud Run configuration fixes

## Cost Management

### Cloud Run Status

While in local development:

- Cloud Run service scaled to 0 instances (no charges)
- No compute or memory costs
- Storage costs minimal (just for container images)

### Return to Production

To resume Cloud Run operation:

```bash
# Scale back up (when ready)
gcloud run services update dispinmap-bot --region=us-central1 --min-instances=1
```

## Next Steps

After successful local testing:

1. Document any stability issues found
2. Investigate Cloud Run health check configuration
3. Apply fixes to Cloud Run deployment
4. Test fixes locally first
5. Deploy improved version to production
