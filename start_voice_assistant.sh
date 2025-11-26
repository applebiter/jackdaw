#!/bin/bash
# Voice Assistant Launcher
# Starts all three components of the voice assistant system

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Activate virtual environment
source .venv/bin/activate

echo "Starting Voice Assistant System..."
echo "=================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Rotate/truncate old logs if they exist and are large
for logfile in logs/voice_command.log logs/llm_processor.log logs/tts_client.log; do
    if [ -f "$logfile" ] && [ $(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile") -gt 10485760 ]; then
        echo "Rotating large log file: $logfile"
        tail -n 5000 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
    fi
done

# Start components in background
# Voice command client can be very verbose, so limit its logging
echo "Starting Voice Command Client..."
python voice_command_client.py >> logs/voice_command.log 2>&1 &
VOICE_PID=$!

echo "Starting LLM Query Processor..."
python -u llm_query_processor.py > logs/llm_processor.log 2>&1 &
LLM_PID=$!

echo "Starting TTS JACK Client..."
python tts_jack_client.py > logs/tts_client.log 2>&1 &
TTS_PID=$!

echo ""
echo "✅ All components started!"
echo "   Voice Command Client PID: $VOICE_PID"
echo "   LLM Processor PID: $LLM_PID"
echo "   TTS Client PID: $TTS_PID"
echo ""
echo "Logs are being written to:"
echo "   - logs/voice_command.log"
echo "   - logs/llm_processor.log"
echo "   - logs/tts_client.log"
echo ""
echo "To stop all components, run: kill $VOICE_PID $LLM_PID $TTS_PID"
echo "Or use: ./stop_voice_assistant.sh"

# Save PIDs to file for easy stopping
echo "$VOICE_PID $LLM_PID $TTS_PID" > .voice_assistant.pid

# Wait for interrupt
trap "kill $VOICE_PID $LLM_PID $TTS_PID 2>/dev/null; rm -f .voice_assistant.pid; echo ''; echo 'Voice Assistant stopped.'; exit 0" INT TERM

echo ""
echo "Press Ctrl+C to stop all components..."
wait
