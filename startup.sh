#!/bin/bash
#
# Startup script for Discord bot with Litestream SQLite backup
#
# This script:
# 1. Restores database from Litestream backup if it exists
# 2. Starts Litestream replication in background
# 3. Starts the Discord bot application
# 4. Handles graceful shutdown of both processes
#

set -e

echo "=== Discord Bot with Litestream Startup ==="

# Check required environment variables
if [ -z "$LITESTREAM_BUCKET" ]; then
    echo "ERROR: LITESTREAM_BUCKET environment variable not set"
    exit 1
fi

if [ -z "$LITESTREAM_PATH" ]; then
    echo "ERROR: LITESTREAM_PATH environment variable not set"
    exit 1
fi

# Create directory for database if it doesn't exist
mkdir -p "$(dirname "$LITESTREAM_PATH")"

echo "Database path: $LITESTREAM_PATH"
echo "Backup bucket: $LITESTREAM_BUCKET"

# Function to handle graceful shutdown
cleanup() {
    echo "Received shutdown signal, cleaning up..."

    # Stop Litestream replication
    if [ ! -z "$LITESTREAM_PID" ]; then
        echo "Stopping Litestream..."
        kill $LITESTREAM_PID 2>/dev/null || true
        wait $LITESTREAM_PID 2>/dev/null || true
    fi

    # Stop Discord bot
    if [ ! -z "$BOT_PID" ]; then
        echo "Stopping Discord bot..."
        kill $BOT_PID 2>/dev/null || true
        wait $BOT_PID 2>/dev/null || true
    fi

    echo "Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Step 1: Restore database from backup if it exists and database file doesn't exist
if [ ! -f "$LITESTREAM_PATH" ]; then
    echo "Database file not found, attempting restore from backup..."
    if litestream restore -config /app/litestream.yml "$LITESTREAM_PATH"; then
        echo "Database restored successfully from backup"
    else
        echo "No backup found or restore failed, will create new database"
    fi
else
    echo "Database file exists, skipping restore"
fi

# Step 2: Start Litestream replication in background
echo "Starting Litestream replication..."
litestream replicate -config /app/litestream.yml &
LITESTREAM_PID=$!
echo "Litestream started with PID: $LITESTREAM_PID"

# Give Litestream a moment to initialize
sleep 2

# Step 3: Start Discord bot application
echo "Starting Discord bot application..."
python -u bot.py &
BOT_PID=$!
echo "Discord bot started with PID: $BOT_PID"

# Step 4: Wait for either process to exit
wait_for_any() {
    while kill -0 $LITESTREAM_PID 2>/dev/null && kill -0 $BOT_PID 2>/dev/null; do
        sleep 1
    done
}

echo "Both processes started, monitoring..."
wait_for_any

# If we get here, one of the processes has exited
if ! kill -0 $LITESTREAM_PID 2>/dev/null; then
    echo "ERROR: Litestream process has exited unexpectedly"
    exit 1
fi

if ! kill -0 $BOT_PID 2>/dev/null; then
    echo "ERROR: Discord bot process has exited unexpectedly"
    exit 1
fi

# This should not be reached under normal operation
echo "Startup script exiting unexpectedly"
exit 1
