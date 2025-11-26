# Quick Reference - Multi-Host Voice Assistant

## Initial Setup (One Time Per Host)

```bash
# Install dependencies
pip install -r requirements.txt

# Edit config file
nano voice_assistant_config.json
# Change "wake_word" to match hostname
```

## Daily Usage

### Start/Stop
```bash
./start_voice_assistant.sh    # Start all components
./stop_voice_assistant.sh     # Stop all components
```

### Voice Commands

#### Basic Commands
```
"[hostname], hello"             - Test command
"[hostname], stop listening"    - Shutdown all components
```

#### LLM Chat
```
"[hostname], start chat"   - Begin capturing query
[speak your question]
"[hostname], stop chat"    - Send to LLM
[wait for TTS response]
```

#### Music Player
```
# Playing Music
"[hostname], play random track"           - Play from music library
"[hostname], play artist pink floyd"      - Play tracks by artist
"[hostname], play album dark side"        - Play album
"[hostname], play song comfortably numb"  - Play song by title
"[hostname], play genre jazz"             - Play genre
"[hostname], play year 1985"              - Play tracks from year

# Playback Control
"[hostname], next track"                  - Skip to next (sequential or shuffle)
"[hostname], stop playing music"          - Stop playback
"[hostname], pause music"                 - Pause playback
"[hostname], resume music"                - Resume from pause

# Playback Mode
"[hostname], shuffle on"                  - Enable shuffle/random mode
"[hostname], shuffle off"                 - Enable sequential mode (default)
"[hostname], toggle shuffle"              - Switch between modes

# Volume Control
"[hostname], volume up"                   - Increase by 10%
"[hostname], volume down"                 - Decrease by 10%
"[hostname], set volume low"              - 30%
"[hostname], set volume medium"           - 60%
"[hostname], set volume high"             - 90%
"[hostname], what's the volume"           - Report level

# Library Info
"[hostname], music library stats"         - Show library statistics
```

#### Timemachine (Retroactive Recording)
```
"[hostname], start the buffer"   - Begin buffering audio
"[hostname], save that"          - Save last N seconds to WAV file
"[hostname], stop the buffer"    - Stop buffering
"[hostname], buffer status"      - Check if running
```

## Monitoring

### Local Conversation Store (SQLite):
```bash
# Inspect sessions
python tools/inspect_conversations.py --sessions --limit 10

# Inspect recent messages
python tools/inspect_conversations.py --messages --limit 10
```

### Logs:
```bash
tail -f logs/voice_command.log   # Voice recognition
tail -f llm_processor.log   # LLM queries/responses
tail -f tts_client.log      # Text-to-speech
```

## Troubleshooting

### Voice not recognized:
- Check JACK connections in Carla
- Verify microphone connected to VoiceCommandClient:input
- Check VAD threshold in config (lower = more sensitive)
- Review voice_command.log

### No TTS output:
- Check JACK connections from TTSJackClient to speakers
- Verify FFmpeg installed: `ffmpeg -version`
- Check tts_client.log for errors

### LLM not responding:
- Verify Ollama running: `ollama list`
- Check model exists: `ollama pull granite4:tiny-h`
- Review llm_processor.log

## Configuration Reference

### voice_assistant_config.json Key Settings:

```json
{
  "database": {
    "enabled": true,            // Set false to disable history
    "backend": "sqlite",       // Local per-host SQLite store
    "path": "conversations.sqlite3"  // Path to SQLite file
  },
  "session": {
    "inactivity_timeout_minutes": 30,  // Reset session after N minutes
    "max_context_tokens": 30000        // History token limit
  },
  "logging": {
    "log_level": "INFO"        // INFO (default) or DEBUG (verbose)
  },
  "voice": {
    "recognition": {
      "wake_word": "alpha",            // Should match hostname
      "vad_enabled": true,             // Voice activity detection
      "vad_energy_threshold": 0.01     // Lower = more sensitive
    }
  },
  "ollama": {
    "model": "granite4:tiny-h",        // LLM model to use
    "options": {
      "num_ctx": 32768                 // LLM context window
    }
  }
}
```

**Log Levels:**
- `INFO` (default): Shows recognized commands and responses, suppresses partial speech recognition
- `DEBUG`: Verbose mode - shows all partial speech recognition results as you speak

## Network Topology

```
alpha   ─┐
bravo   ─┤
charlie ─┼─→ JackTrip Audio Network
delta   ─┤
echo    ─┘
```

## Host Assignments (Example)

| Hostname | Wake Word | Role              |
|----------|-----------|-------------------|
| alpha    | alpha     | Voice client      |
| bravo    | bravo     | Voice client      |
| charlie  | charlie   | Voice client      |
| delta    | delta     | Voice client      |
| echo     | echo      | Voice client      |

## Performance Notes

- **Vosk CPU:** ~20% when speaking, ~0-2% when silent (VAD enabled)
- **Piper CPU:** ~19% when synthesizing, 0% idle
- **LLM Processor:** Negligible (~0%)
- **Memory:** ~440 MB (Vosk) + ~490 MB (Piper) + ~27 MB (Processor)

With VAD enabled, idle resource usage is minimal.
