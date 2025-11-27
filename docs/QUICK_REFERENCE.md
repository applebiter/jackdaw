# Quick Reference - Jackdaw Voice Assistant 🐦‍⬛

**New user?** Start with [GETTING_STARTED.md](../GETTING_STARTED.md) first!

---

## ⚡ Quick Command Card

Replace `[wake]` with your configured wake word (default: "alpha")

| Category | Command | What it does |
|----------|---------|-------------|
| **Testing** | `[wake], hello` | Test if Jackdaw is listening |
| **Music** | `[wake], play random track` | Start playing music |
| | `[wake], play artist [name]` | Play specific artist |
| | `[wake], next track` | Skip to next song |
| | `[wake], volume up/down` | Adjust volume ±10% |
| | `[wake], shuffle on` | Enable random playback |
| **AI Chat** | `[wake], start recording` | Begin question capture |
| | `[wake], stop recording` | Send to AI and get response |
| **Recording** | `[wake], start the buffer` | Begin retroactive recording |
| | `[wake], save that` | Save last 5 minutes to file |
| **Streaming** | `[wake], start streaming` | Broadcast to Icecast2 |
| | `[wake], stop streaming` | End broadcast |
| **System** | `[wake], stop listening` | Shut down Jackdaw |

---

## 🚀 Initial Setup (One Time)

```bash
# 1. Install dependencies
cd ~/jackdaw
./install.sh

# 2. Download speech model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip && rm -rf model/*
mv vosk-model-small-en-us-0.15/* model/

# 3. Download voice model
cd voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
cd ..

# 4. Configure wake word
nano voice_assistant_config.json
# Change "wake_word" to your preferred word

# 5. Scan music (optional)
source .venv/bin/activate
python tools/scan_music_library.py
```

---

## 🎯 Daily Usage

### Start/Stop

**GUI Mode (Recommended):**
- Search "Jackdaw" in applications menu
- Or run: `./launch_tray_app.sh`

**CLI Mode:**
```bash
./start_voice_assistant.sh    # Start all components
./stop_voice_assistant.sh     # Stop all components
```

**Voice Command:**
```
"[wake], stop listening"      # Shut down everything
```

### Voice Commands

#### Basic Commands
```
"[wake], hello"                    Test if Jackdaw responds
"[wake], stop listening"           Shut down all components
```

#### AI Chat
```
"[wake], start recording"          Begin capturing your question
    [speak your question/request]
"[wake], stop recording"           Send to AI and get spoken response
```

**Examples:**
- "What's the weather forecast?"
- "Explain quantum computing in simple terms"
- "Tell me a joke"
- "What should I make for dinner?"

#### Music Player

**Playing Music:**
```
"[wake], play random track"               Play from music library
"[wake], play artist [name]"              Play tracks by artist
"[wake], play album [name]"               Play specific album
"[wake], play song [title]"               Play song by title
"[wake], play genre [genre]"              Play genre (jazz, rock, etc.)
"[wake], play year [year]"                Play tracks from specific year
```

**Examples:**
- `"[wake], play artist Pink Floyd"`
- `"[wake], play album Dark Side of the Moon"`
- `"[wake], play genre electronic"`

**Playback Control:**
```
"[wake], next track"                      Skip (sequential or shuffle mode)
"[wake], stop playing music"              Stop playback
"[wake], pause music"                     Pause
"[wake], resume music"                    Resume from pause
```

**Playback Mode:**
```
"[wake], shuffle on"                      Enable random playback
"[wake], shuffle off"                     Enable sequential playback
"[wake], toggle shuffle"                  Switch between modes
```

**Volume Control:**
```
"[wake], volume up"                       Increase by 10%
"[wake], volume down"                     Decrease by 10%
"[wake], set volume low"                  Set to 30%
"[wake], set volume medium"               Set to 60%
"[wake], set volume high"                 Set to 90%
"[wake], what's the volume"               Report current level
```

**Library Info:**
```
"[wake], music library stats"             Show library statistics
```

#### Timemachine (Retroactive Recording)

**What it does:** Keeps a rolling 5-minute buffer so you can save audio *after* it happens!

```
"[wake], start the buffer"                Start buffering audio
"[wake], save that"                       Save last 5 minutes to WAV file
"[wake], stop the buffer"                 Stop buffering
"[wake], buffer status"                   Check if running
```

**Example workflow:**
1. `"[wake], start the buffer"` - Now recording into memory
2. Play guitar, jam, experiment...
3. You just played something amazing!
4. `"[wake], save that"` - Captures what you just played
5. File saved to `~/recordings/timemachine_TIMESTAMP.wav`

**Use cases:** Jam sessions, podcast moments, live performances, experimentation

See [TIMEMACHINE.md](TIMEMACHINE.md) for details.

#### Icecast2 Streaming

**What it does:** Broadcasts your audio to the internet for listeners worldwide.

```
"[wake], start streaming"                 Begin broadcast to Icecast2
"[wake], stop streaming"                  End broadcast
"[wake], stream status"                   Check current status
"[wake], begin broadcast"                 Alternative to "start streaming"
"[wake], end broadcast"                   Alternative to "stop streaming"
```

**Prerequisites:** Icecast2 server configured in `voice_assistant_config.json`

See [STREAMING.md](STREAMING.md) for server setup and configuration.

---

## 📊 Monitoring & Debugging

### Check Logs (Most Useful)

```bash
# Real-time log viewing
tail -f logs/voice_command.log      # Voice recognition
tail -f logs/llm_processor.log      # AI chat
tail -f logs/tts_client.log         # Speech synthesis

# Search logs for errors
grep -i error logs/*.log
```

### Conversation History (SQLite)
```bash
# Inspect sessions
python tools/inspect_conversations.py --sessions --limit 10

# Inspect recent messages
python tools/inspect_conversations.py --messages --limit 10
```

### JACK Audio Status

```bash
# List all audio ports
jack_lsp

# Check specific connections
jack_lsp -c | grep VoiceCommandClient
jack_lsp -c | grep TTSJackClient

# Monitor audio levels
jack_meter VoiceCommandClient:input
```

---

## 🔧 Troubleshooting

### Wake Word Not Working

**Check if voice recognition is active:**
```bash
tail -f logs/voice_command.log
# Speak into microphone - you should see words appear
```

**If nothing appears:**
- ❌ Microphone not connected in JACK
- ❌ JACK not capturing audio
- ❌ Wrong audio device selected

**If words appear but not wake word:**
- Try different wake word (some work better with Vosk)
- Speak more clearly and slowly
- Make sure wake word exactly matches config

### No Speech from Jackdaw

**Quick checks:**
```bash
ffmpeg -version                  # Should show version
ls -la voices/*.onnx*            # Should show both .onnx files
jack_lsp | grep TTSJackClient    # Should show output ports
```

**Common causes:**
- TTS not connected to speakers in JACK
- Missing voice model .onnx.json file
- FFmpeg not installed
- Wrong voice model path in config

### Music Won't Play

**Did you scan your library?**
```bash
source .venv/bin/activate
python tools/scan_music_library.py
```

**Check database:**
```bash
sqlite3 music_library.sqlite3 "SELECT COUNT(*) FROM sounds;"
# Should show number of tracks
```

**Check player connections:**
```bash
jack_lsp -c | grep OggPlayer
# Should be connected to speakers
```

### AI Not Responding

**Is Ollama running?**
```bash
ollama list                      # Should show installed models
ollama ps                        # Should show active models
```

**Test Ollama directly:**
```bash
ollama run granite3.1:2b "Hello"
# Should get a response
```

**Check logs:**
```bash
tail -f logs/llm_processor.log
```

### System Issues

**JACK not running:**
```bash
# Start JACK
qjackctl                         # GUI
# or
jackd -d alsa                    # CLI
```

**Force stop Jackdaw:**
```bash
./stop_voice_assistant.sh
# or force kill:
pkill -9 -f "voice_command_client|llm_query_processor|tts_jack_client"
```

**Check processes:**
```bash
ps aux | grep -E "voice_command|llm_processor|tts_jack"
```

---

## ⚙️ Configuration Quick Guide

Edit `voice_assistant_config.json` to customize Jackdaw.

### Essential Settings

**Wake Word:**
```json
"wake_word": "alpha"
```
Change to any word you like. Short, distinct words work best.

**Voice Model:**
```json
"model_path": "voices/en_US-lessac-medium.onnx"
```
Switch to different Piper voice (lessac, amy, joe).

**LLM Model:**
```json
"model": "granite3.1:2b"
```
Any Ollama model you've installed.

**Music Library:**
```json
"music_library_path": "/path/to/your/music"
```

### Advanced Settings

**Voice Activity Detection (VAD):**
```json
"vad_enabled": true,              // Enable/disable VAD
"vad_energy_threshold": 0.01      // 0.001-0.1, lower = more sensitive
```

**Logging:**
```json
"log_level": "INFO"               // INFO or DEBUG
```
- `INFO`: Clean output, recognized commands only
- `DEBUG`: Verbose, shows all speech recognition in real-time

**Conversation History:**
```json
"database": {
  "enabled": true,                // false = stateless
  "path": "conversations.sqlite3"
},
"session": {
  "inactivity_timeout_minutes": 30,
  "max_context_tokens": 30000
}
```

**Timemachine Buffer:**
```json
"buffer_seconds": 300             // 300 = 5 minutes
```

**Icecast2 Streaming:**
```json
"icecast_streamer": {
  "enabled": true,
  "server": "localhost",
  "port": 8000,
  "password": "hackme",
  "mount": "/stream",
  "format": "ogg",                // ogg, opus, flac, mp3
  "bitrate": 128
}
```

---

## 🌐 Network Audio (Advanced)

### JackTrip for Real-Time Collaboration

**Purpose:** Low-latency (20-50ms) audio collaboration over internet

**Use cases:**
- Remote jam sessions
- Distributed band practice  
- Multi-location recording

**Setup:** See [STREAMING.md](STREAMING.md) for complete JackTrip guide.

### Multi-Host Wake Words

For networked setups where multiple computers share audio:

| Computer | Wake Word | Purpose |
|----------|-----------|---------|
| studio   | `studio`  | Main recording |
| synth    | `synth`   | Synthesizers |
| drums    | `drums`   | Drum machine |
| mixer    | `mixer`   | Final output |

Each host responds only to its own wake word on shared audio network.

---

## 📈 Performance Reference

**Typical Resource Usage:**

| Component | Active | Idle (VAD enabled) |
|-----------|--------|-------------------|
| Vosk | 20% CPU | 0-2% CPU |
| Piper TTS | 19% CPU | 0% CPU |
| LLM Processor | <1% CPU | <1% CPU |
| **Total** | **~40% CPU** | **~2% CPU** |

**Memory:**
- Vosk: ~440 MB
- Piper: ~490 MB  
- Ollama: 2-7 GB (model dependent)
- Other: ~50 MB
- **Total: 3-8 GB**

**Recommendations:**
- 4-8 GB RAM minimum
- Enable VAD for better idle performance
- Use small Vosk model on limited hardware
- Close unused applications when using LLM

---

## 📚 More Information

**Complete Guides:**
- [GETTING_STARTED.md](../GETTING_STARTED.md) - Beginner setup walkthrough
- [README.md](../README.md) - Main documentation
- [TRAY_APP.md](TRAY_APP.md) - GUI application guide
- [MUSIC_DATABASE.md](MUSIC_DATABASE.md) - Music library details
- [MUSIC_BROWSER.md](MUSIC_BROWSER.md) - GUI music browser
- [STREAMING.md](STREAMING.md) - Icecast2 & JackTrip setup
- [TIMEMACHINE.md](TIMEMACHINE.md) - Retroactive recording
- [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) - Create custom commands

**Quick Links:**
- Models: [model/README.md](../model/README.md) & [voices/README.md](../voices/README.md)
- GitHub: https://github.com/applebiter/jackdaw
- Issues: https://github.com/applebiter/jackdaw/issues

---

**This is a quick reference. For detailed help, see [GETTING_STARTED.md](../GETTING_STARTED.md)!**
