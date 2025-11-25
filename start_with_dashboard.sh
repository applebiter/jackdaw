#!/bin/bash
#
# Start Voice Assistant with optional Dashboard
# Usage: ./start_with_dashboard.sh

echo "Starting Voice Assistant System with Dashboard..."
echo "=================================================="
echo ""

# Start the main voice assistant
./start_voice_assistant.sh &

# Wait a moment for it to initialize
sleep 3

# Start the dashboard
echo ""
echo "Starting Web Dashboard on port 7865..."
echo ""

.venv/bin/python gradio_dashboard.py

# When dashboard is stopped (Ctrl+C), optionally stop voice assistant
echo ""
echo "Dashboard stopped."
echo "Voice assistant is still running in background."
echo "To stop it, run: ./stop_voice_assistant.sh"
