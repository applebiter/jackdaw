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

# Stop any FFmpeg processes (Icecast streaming)
echo "Stopping Icecast streaming (jd_stream)..."
pkill -f "ffmpeg.*jd_stream" 2>/dev/null
echo "✅ Cleanup complete."
