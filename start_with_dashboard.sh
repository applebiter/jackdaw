#!/bin/bash
#
# Start Voice Assistant with Dashboard
# Usage: ./start_with_dashboard.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Voice Assistant System with Dashboard..."
echo "=================================================="
echo ""

# Start the main voice assistant
./start_voice_assistant.sh

# Wait for components to initialize
sleep 3

# Start the dashboard
echo ""
echo "Starting Web Dashboard on port 7865..."
echo "Dashboard will be accessible at: http://localhost:7865"
echo ""

# Activate virtual environment and start dashboard
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    python gradio_dashboard.py
else
    # Fallback if running as service
    .venv/bin/python gradio_dashboard.py
fi

# When dashboard is stopped (Ctrl+C), optionally stop voice assistant
echo ""
echo "Dashboard stopped."
echo "Voice assistant is still running in background."
echo "To stop it, run: ./stop_voice_assistant.sh"
