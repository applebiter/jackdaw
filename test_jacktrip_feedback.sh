#!/bin/bash
# Test JackTrip feedback mechanisms

echo "=== JackTrip Feedback Test ==="
echo

# 1. Check if hub is running
echo "1. Checking hub server..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✓ Hub server is running"
else
    echo "   ✗ Hub server is NOT running"
    echo "   Start it with: cd tools/jacktrip_hub && ./run_local_hub.sh"
fi
echo

# 2. Check if TTS is running
echo "2. Checking TTS process..."
if pgrep -f "tts_jack_client.py" > /dev/null; then
    echo "   ✓ TTS client is running"
else
    echo "   ✗ TTS client is NOT running"
    echo "   It should start with the voice assistant"
fi
echo

# 3. Check plugin is enabled
echo "3. Checking plugin configuration..."
if grep -q '"jacktrip_client".*"enabled".*true' voice_assistant_config.json 2>/dev/null; then
    echo "   ✓ JackTrip plugin is enabled"
else
    echo "   ✗ JackTrip plugin is NOT enabled or config not found"
fi
echo

# 4. Test TTS feedback directly
echo "4. Testing TTS feedback mechanism..."
echo "Writing test message to llm_response.txt..."
echo "This is a test of the JackTrip feedback system." > llm_response.txt
echo "   ✓ File written"
echo "   → TTS should speak this message within 5 seconds"
echo "   → Watch for console output from tts_jack_client.py"
echo
sleep 6

# 5. Check if file was consumed
if [ -f llm_response.txt ]; then
    echo "   ⚠ llm_response.txt still exists (TTS may not be polling)"
else
    echo "   ✓ llm_response.txt was consumed by TTS"
fi
echo

# 6. Show tray app status
echo "6. Checking tray application..."
if pgrep -f "voice_assistant_tray.py" > /dev/null; then
    echo "   ✓ Tray application is running"
    echo "   → Look for '🔧 JackTrip Client' in the tray menu"
else
    echo "   ✗ Tray application is NOT running"
fi
echo

echo "=== Summary ==="
echo "Visual feedback: Click tray icon → look for '🔧 JackTrip Client'"
echo "Voice feedback: Commands should write to llm_response.txt → TTS speaks it"
echo
echo "Try a command: Say 'Indigo, list jam rooms'"
echo "Then check: tail -f logs/voice_command_client.log"
