#!/bin/bash
# Launcher script for Voice Assistant Tray Application with auto-restart

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Auto-restart loop
while true; do
    echo "[$(date)] Starting Jackdaw tray app..." >> logs/tray_restart.log
    
    # Activate virtual environment and run tray app
    "$DIR/.venv/bin/python" "$DIR/voice_assistant_tray.py"
    
    EXIT_CODE=$?
    
    # If exit code is 0, user quit intentionally - don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Jackdaw quit normally" >> logs/tray_restart.log
        break
    fi
    
    # Otherwise, it crashed - log and restart after a delay
    echo "[$(date)] Jackdaw crashed with exit code $EXIT_CODE, restarting in 3 seconds..." >> logs/tray_restart.log
    sleep 3
done
