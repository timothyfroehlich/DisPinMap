#!/bin/bash
# Script to send commands to the local development bot

# Parse arguments
AUTO_START=true
COMMAND=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-auto-start)
            AUTO_START=false
            shift
            ;;
        *)
            COMMAND="$1"
            shift
            ;;
    esac
done

if [ -z "$COMMAND" ]; then
    echo "Usage: ./send_command.sh [--no-auto-start] <command>"
    echo "Examples:"
    echo "  ./send_command.sh '!list'"
    echo "  ./send_command.sh '.status'"
    echo "  ./send_command.sh '.trigger'"
    echo "  ./send_command.sh '!check'"
    echo "  ./send_command.sh --no-auto-start '!list'  # Don't start bot automatically"
    exit 1
fi

# Get the project root directory (parent of scripts)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Check if bot is running
check_bot_running() {
    pgrep -f "python.*local_dev" > /dev/null
}

# Start bot if needed
if ! check_bot_running; then
    if [ "$AUTO_START" = true ]; then
        echo "Bot not running, starting it..."
        cd "$PROJECT_ROOT"
        source venv/bin/activate && python local_dev.py > /dev/null 2>&1 &
        BOT_PID=$!
        echo "Bot started with PID: $BOT_PID"
        echo "Waiting 3 seconds for bot to initialize..."
        sleep 3
    else
        echo "Error: Bot is not running. Start it with 'python local_dev.py' or remove --no-auto-start flag"
        exit 1
    fi
else
    echo "Bot is already running"
fi

echo "$COMMAND" >> "$PROJECT_ROOT/commands.txt"
echo "Command sent: $COMMAND"
echo "Monitor responses with: tail -f $PROJECT_ROOT/logs/bot.log"