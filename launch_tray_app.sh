#!/bin/bash
# Launcher script for Voice Assistant Tray Application with auto-restart

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Remove stale heartbeat file
rm -f .tray_heartbeat

# Auto-restart loop
while true; do
    echo "[$(date)] Starting Jackdaw tray app..." >> logs/tray_restart.log
    
    # Start tray app in background and get PID
    "$DIR/.venv/bin/python" "$DIR/voice_assistant_tray.py" &
    TRAY_PID=$!
    
    # Monitor for crashes or hangs
    CRASH_COUNT=0
    while kill -0 $TRAY_PID 2>/dev/null; do
        # Check if heartbeat file is being updated
        if [ -f .tray_heartbeat ]; then
            CURRENT_TIME=$(date +%s)
            HEARTBEAT_TIME=$(date -r .tray_heartbeat +%s 2>/dev/null || echo 0)
            TIME_DIFF=$((CURRENT_TIME - HEARTBEAT_TIME))
            
            # If heartbeat hasn't updated in 30 seconds, app might be frozen
            if [ $TIME_DIFF -gt 30 ]; then
                echo "[$(date)] Warning: Heartbeat stale for ${TIME_DIFF}s, app may be frozen" >> logs/tray_restart.log
                CRASH_COUNT=$((CRASH_COUNT + 1))
                
                # If frozen for multiple checks, kill and restart
                if [ $CRASH_COUNT -gt 2 ]; then
                    echo "[$(date)] App appears frozen, killing process..." >> logs/tray_restart.log
                    kill -9 $TRAY_PID 2>/dev/null
                    break
                fi
            else
                CRASH_COUNT=0
            fi
        fi
        
        sleep 10
    done
    
    # Wait for process to finish
    wait $TRAY_PID 2>/dev/null
    EXIT_CODE=$?
    
    # If exit code is 0, user quit intentionally - don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Jackdaw quit normally" >> logs/tray_restart.log
        break
    fi
    
    # Otherwise, it crashed - log and restart after a delay
    echo "[$(date)] Jackdaw crashed with exit code $EXIT_CODE, restarting in 3 seconds..." >> logs/tray_restart.log
    sleep 3
    
    # Clean up stale files
    rm -f .tray_heartbeat
done

# Cleanup
rm -f .tray_heartbeat
