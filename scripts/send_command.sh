#!/bin/bash
# Simple script to send commands to the local development bot

if [ $# -eq 0 ]; then
    echo "Usage: ./send_command.sh <command>"
    echo "Examples:"
    echo "  ./send_command.sh '!list'"
    echo "  ./send_command.sh '.status'"
    echo "  ./send_command.sh '.trigger'"
    echo "  ./send_command.sh '!check'"
    exit 1
fi

# Get the project root directory (parent of scripts)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "$1" >> "$PROJECT_ROOT/commands.txt"
echo "Command sent: $1"
echo "Monitor responses with: tail -f $PROJECT_ROOT/logs/bot.log"