# Voice Assistant

A modular, real-time voice assistant system using JACK Audio, Vosk speech recognition, Ollama LLM, and Piper TTS.

## Quick Start

```bash
# First time setup: Copy the example config
cp voice_assistant_config.json.example voice_assistant_config.json

# Edit config with your settings (Ollama host, music path, wake word, etc.)
nano voice_assistant_config.json

# Start all components
./start_voice_assistant.sh

# Stop all components
./stop_voice_assistant.sh

# Or manually:
Ctrl+C in the terminal where start script is running
```

## Directory Structure

```
voiceassistant/
├── docs/                       # Documentation
│   ├── README.md              # Detailed setup guide
│   ├── PLUGIN_GUIDE.md        # How to create plugins
│   ├── QUICK_REFERENCE.md     # Command reference
│   ├── MUSIC_DATABASE.md      # Music library system guide
│   ├── TIMEMACHINE.md         # Retroactive recording plugin
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── brainstorm.md
│
├── plugins/                    # Voice command plugins
│   ├── __init__.py
│   ├── basic_commands.py      # Hello, stop listening, etc.
│   ├── llm_recorder.py        # Start/stop recording for LLM
│   ├── music_player.py        # Music playback & volume control
│   └── timemachine.py         # Retroactive audio recording
│
├── tools/                      # Utility scripts
│   ├── inspect_conversations.py    # View SQLite conversations
│   ├── remember_jack_routing.py    # Save JACK routing config
│   └── scan_music_library.py       # Scan music directory to database
│
├── tests/                      # Test files
│   ├── test_database.py
│   ├── test_local_conversation_store.py
│   └── conversations_test.sqlite3
│
├── logs/                       # Runtime logs (auto-created)
│   ├── voice_command.log
│   ├── llm_processor.log
│   └── tts_client.log
│
├── model/                      # Vosk speech recognition model
│   └── README                 # Download instructions
│
├── voices/                     # Piper TTS voice models
│   ├── README.md              # Download instructions & voice guide
│   ├── en_US-amy-medium.onnx
│   ├── en_US-amy-medium.onnx.json
│   ├── en_US-arctic-medium.onnx
│   ├── en_US-arctic-medium.onnx.json
│   ├── en_US-joe-medium.onnx
│   ├── en_US-joe-medium.onnx.json
│   ├── en_US-lessac-medium.onnx
│   └── en_US-lessac-medium.onnx.json
│
├── voice_command_client.py    # Main voice recognition & command dispatcher
├── llm_query_processor.py     # LLM query handler with conversation history
├── tts_jack_client.py         # Text-to-speech JACK client
├── ogg_jack_player.py         # Music player with skip/volume control
├── music_query.py             # Music database query handler
├── ring_buffer_recorder.py    # Python-based retroactive audio recorder
├── plugin_base.py             # Plugin base class
├── plugin_loader.py           # Dynamic plugin loader
│
├── voice_assistant_config.json     # Main configuration
├── voice_assistant_config.json.example
├── requirements.txt           # Python dependencies
├── conversations.sqlite3      # Local conversation storage
├── music_library.sqlite3      # Music metadata database
├── music_library_schema.sql   # Database schema
├── jack_routing.json          # Saved JACK connections
│
├── start_voice_assistant.sh   # Launch all components
├── stop_voice_assistant.sh    # Shutdown script
├── LICENSE
└── README.md                  # This file
```

## Core Components

1. **voice_command_client.py** - Listens to JACK audio, performs speech recognition, detects wake word (configurable), executes commands
2. **llm_query_processor.py** - Polls for LLM queries, maintains conversation history in SQLite, sends to Ollama
3. **tts_jack_client.py** - Reads responses, synthesizes speech with Piper, outputs to JACK

## Configuration

Edit `voice_assistant_config.json` to customize:
- Wake word (configurable, e.g., "alpha")
- Ollama host and model
- Music library path
- Plugin enable/disable
- VAD settings
- Session timeouts

## Available Commands

Say your wake word followed by:

**Basic Commands:**
- **hello** - Test command
- **stop listening** - Shut down assistant

**Music Player:**
- **play random track** - Play music from library
- **play artist <name>** - Play tracks by artist (e.g., "play artist pink floyd")
- **play album <name>** - Play album (e.g., "play album dark side of the moon")
- **play song <title>** - Play song by title
- **play genre <genre>** - Play tracks from genre
- **next track** - Skip to next song (sequential or random based on mode)
- **stop playing music** - Stop playback
- **shuffle on/off** - Enable/disable shuffle mode (default: sequential)
- **toggle shuffle** - Switch between shuffle and sequential
- **volume up/down** - Adjust volume by 10%
- **set volume low/medium/high** - Set to 30%/60%/90%
- **what's the volume** - Report current volume

**LLM Recording:**
- **start recording** - Begin capturing text for LLM
- **stop recording** - Send captured text to LLM

**Timemachine (Retroactive Recording):**
- **start the buffer** - Begin buffering audio for retroactive save
- **stop the buffer** - Stop buffering
- **save that** - Save the last N seconds to WAV file
- **buffer status** - Check if timemachine is running

## Adding New Functionality

Create a new plugin in `plugins/` directory. See `docs/PLUGIN_GUIDE.md` for details.

Example:
```python
from plugin_base import VoiceAssistantPlugin

class MyPlugin(VoiceAssistantPlugin):
    def get_name(self): return "my_plugin"
    def get_description(self): return "My custom commands"
    def get_commands(self):
        return {"do something": self._handler}
    def _handler(self):
        print("Command executed!")
```

Enable in config:
```json
{
  "plugins": {
    "my_plugin": {"enabled": true}
  }
}
```

## Logs

All logs are written to `logs/` directory and auto-rotate at 10MB.

## Dependencies

- Python 3.8+
- JACK Audio Connection Kit
- Vosk speech recognition model (see `model/README`)
- Piper TTS voice model (see `voices/README.md`)
- Ollama LLM server

See `requirements.txt` for Python packages.

**First-time setup:** Download the Vosk model and Piper voice files - see the README files in `model/` and `voices/` directories for download links and instructions.

## Documentation

- `docs/README.md` - Complete setup guide
- `docs/PLUGIN_GUIDE.md` - Plugin development guide
- `docs/QUICK_REFERENCE.md` - Command and config reference
- `docs/MUSIC_DATABASE.md` - Music library system and scanner
- `docs/TIMEMACHINE.md` - Retroactive recording plugin guide
