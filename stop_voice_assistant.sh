#!/bin/bash
# Stop Voice Assistant
# Stops all running components

if [ -f .voice_assistant.pid ]; then
    PIDS=$(cat .voice_assistant.pid)
    echo "Stopping Voice Assistant components..."
    kill $PIDS 2>/dev/null
    rm -f .voice_assistant.pid
    echo "✅ Voice Assistant stopped."
else
    echo "No PID file found. Components may not be running."
    echo "Trying to stop by process name..."
    pkill -f "voice_command_client.py"
    pkill -f "llm_query_processor.py"
    pkill -f "tts_jack_client.py"
fi

# Also stop dashboard if running
if pgrep -f "gradio_dashboard.py" > /dev/null; then
    echo "Stopping Gradio dashboard..."
    pkill -f "gradio_dashboard.py"
    echo "✅ Dashboard stopped."
fi
