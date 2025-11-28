<div align="center">

<img src="icons/hicolor/256x256/apps/jackdaw.png" alt="Jackdaw" width="128" />

# Jackdaw Voice Assistant

**A privacy-first, voice-controlled audio system that lives in your professional audio workflow.**

</div>

Jackdaw is a modular voice assistant built on JACK Audio, featuring speech recognition (Vosk), local AI chat (Ollama), and text-to-speech (Piper). Control your music library, stream to the internet, record retroactively, and collaborate over networks—all with your voice, all running locally on your machine.

**No cloud. No subscriptions. No privacy concerns.** Everything runs on your computer.

---

## ✨ What Can Jackdaw Do?

- 🎵 **Control your music library** - "Play artist Pink Floyd", "Next track", "Shuffle on"
- 🎙️ **Stream to Icecast2** - Broadcast audio to the internet with voice commands
- ⏮️ **Retroactive recording** - Save audio that already happened with buffer
- 💬 **Chat with local AI** - Ask questions, get spoken responses (via Ollama)
- 🌐 **Network collaboration** - Real-time audio with JackTrip
- 🎛️ **Professional audio routing** - Integrates seamlessly with JACK ecosystem
- 🔌 **Extensible plugins** - Add your own voice commands easily

---

## 🚀 Quick Start

**New to Jackdaw?** Read **[GETTING_STARTED.md](GETTING_STARTED.md)** for a complete beginner-friendly guide!

**Already familiar with JACK?** Here's the express setup:

```bash
# 1. Install system dependencies
sudo apt install jackd2 ffmpeg libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 git  # Ubuntu/Debian
sudo dnf install jack-audio-connection-kit ffmpeg libxcb xcb-util-cursor git          # Fedora

# 2. Install Ollama (optional, for AI features)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull granite3.1:2b

# 3. Clone and install Jackdaw
git clone https://github.com/applebiter/jackdaw.git
cd jackdaw
./install.sh

# 4. Download models (follow prompts from installer)
# - Vosk speech recognition: https://alphacephei.com/vosk/models
# - Piper TTS voices: https://huggingface.co/rhasspy/piper-voices

# 5. Launch!
./launch_tray_app.sh
# Or from your applications menu: Search "Jackdaw"
```

**That's it!** Jackdaw appears in your system tray. Connect your microphone and speakers in your JACK patchbay, then say your wake word followed by commands.

---

## 📖 Documentation

- **[GETTING_STARTED.md](GETTING_STARTED.md)** ⭐ **Start here!** Complete beginner guide
- **[docs/README.md](docs/README.md)** - Detailed system documentation
- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - All voice commands at a glance
- **[docs/TRAY_APP.md](docs/TRAY_APP.md)** - Using the system tray interface
- **[docs/MUSIC_DATABASE.md](docs/MUSIC_DATABASE.md)** - Music library system guide
- **[docs/MUSIC_BROWSER.md](docs/MUSIC_BROWSER.md)** - GUI music browser and playlists
- **[docs/STREAMING.md](docs/STREAMING.md)** - Icecast2 streaming and JackTrip setup
- **[docs/TIMEMACHINE.md](docs/TIMEMACHINE.md)** - Retroactive recording explained
- **[docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md)** - Create custom voice commands

---

## 🎤 Example Voice Commands

```
"[wake word], hello"                          # Test command
"[wake word], play artist Pink Floyd"         # Play music
"[wake word], next track"                     # Skip track
"[wake word], volume up"                      # Adjust volume
"[wake word], start chat"                     # Begin AI query
"[wake word], stop chat"                      # Send to AI and get response
"[wake word], start streaming"                # Begin Icecast2 broadcast
"[wake word], save that"                      # Retroactive recording
"[wake word], stop listening"                 # Shut down
```

**Default wake word:** "alpha" (change in `voice_assistant_config.json`)

See **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** for complete command list.

---

## 💻 System Requirements

- **OS:** Linux (Ubuntu, Fedora, Arch, Debian, etc.)
- **Python:** 3.8 or newer
- **RAM:** 4GB minimum, 8GB+ recommended for AI features
- **Disk:** 2GB free space (more for music libraries)
- **Audio:** Microphone and speakers/headphones

**Required system packages:**
- JACK Audio (jackd2 or pipewire-jack)
- FFmpeg (audio processing)
- Qt/XCB libraries (for GUI)
- Ollama (optional, for AI chat)

All included in the installation script!

## Directory Structure

```
voiceassistant/
├── docs/                       # Documentation
│   ├── README.md              # Detailed setup guide
│   ├── PLUGIN_GUIDE.md        # How to create plugins
│   ├── QUICK_REFERENCE.md     # Command reference
│   ├── MUSIC_DATABASE.md      # Music library system guide
│   ├── TIMEMACHINE.md         # Retroactive recording plugin
│   ├── STREAMING.md           # Icecast2 streaming guide
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── brainstorm.md
│
├── plugins/                    # Voice command plugins
│   ├── __init__.py
│   ├── basic_commands.py      # Hello, stop listening, etc.
│   ├── llm_recorder.py        # Start/stop recording for LLM
│   ├── music_player.py        # Music playback & volume control
│   ├── buffer.py              # Retroactive audio recording
│   └── icecast_streamer.py    # Icecast2 streaming plugin
│
├── tools/                      # Utility scripts
│   ├── inspect_conversations.py    # View SQLite conversations
│   ├── remember_jack_routing.py    # Save JACK routing config
│   └── scan_music_library.py       # Scan music directory to database
│
├── music_library_browser.py   # GUI music library browser & player
├── launch_music_browser.sh    # Launch the music browser
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
├── voice_assistant_tray.py    # System tray GUI application
├── voice_command_client.py    # Main voice recognition & command dispatcher
├── llm_query_processor.py     # LLM query handler with conversation history
├── tts_jack_client.py         # Text-to-speech JACK client
├── audio_jack_player.py       # Multi-format music player with skip/volume control
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

## 🔧 Core Features

### Voice-Controlled Music Player
Play and control your music library entirely by voice. Supports Ogg Vorbis, Opus, FLAC, and MP3 formats.

**Scan your music:**
```bash
source .venv/bin/activate
python tools/scan_music_library.py
```

**Voice commands:** "play artist...", "play album...", "next track", "shuffle on", "volume up"

### AI Chat with Conversation Memory
Ask questions and get spoken responses using Ollama LLM. Jackdaw remembers your conversation history.

**Commands:** "start chat" → ask your question → "stop chat"

### Icecast2 Streaming
Broadcast your audio to the internet with simple voice commands. Perfect for internet radio or podcasting.

**Commands:** "start streaming", "stop streaming"

See **[docs/STREAMING.md](docs/STREAMING.md)** for server setup.

### Retroactive Recording (Buffer)
Keep a rolling audio buffer and save recordings of things that already happened.

**Commands:** "start the buffer", "save that" (saves last 5 minutes), "stop the buffer"

See **[docs/TIMEMACHINE.md](docs/TIMEMACHINE.md)** for details.

### GUI Music Browser
Browse and control your music library with a graphical interface featuring:
- Searchable, sortable table view
- Playlist management with drag-and-drop
- Local playback or streaming
- Save/load playlists as JSON

**Launch:** `./launch_music_browser.sh` or from the tray menu

### Network Audio Collaboration
Use JackTrip for real-time, low-latency audio collaboration over the internet. Jam with friends across the globe!

See **[docs/STREAMING.md](docs/STREAMING.md)** for JackTrip setup and usage.

## 🔌 Extensible Plugin System

Create custom voice commands easily! Jackdaw's plugin architecture makes it simple to add new functionality.

**Quick example:**
```python
from plugin_base import VoiceAssistantPlugin

class MyPlugin(VoiceAssistantPlugin):
    def get_name(self):
        return "my_plugin"
    
    def get_description(self):
        return "My custom voice commands"
    
    def get_commands(self):
        return {
            "do something cool": self._do_it,
            "another command": self._other_action
        }
    
    def _do_it(self):
        print("Doing something cool!")
        # Your code here
```

Save as `plugins/my_plugin.py`, enable in config, and start using your commands!

**Plugins can also have GUI interfaces** - add control panels to the system tray menu.

See **[docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md)** for complete plugin development guide.

---

## 🗂️ Project Structure

```
jackdaw/
├── 📄 GETTING_STARTED.md           ⭐ Start here!
├── 📄 README.md                    This file
├── 🛠️ install.sh                   Automated installer
├── 🚀 launch_tray_app.sh           Launch GUI
├── ▶️ start_voice_assistant.sh     Launch CLI mode
├── ⏹️ stop_voice_assistant.sh      Shutdown script
│
├── 📁 docs/                        📚 Full documentation
│   ├── README.md                   Detailed setup guide
│   ├── QUICK_REFERENCE.md          Command cheat sheet
│   ├── TRAY_APP.md                 GUI application guide
│   ├── MUSIC_DATABASE.md           Music library system
│   ├── MUSIC_BROWSER.md            GUI browser guide
│   ├── STREAMING.md                Icecast2 & JackTrip
│   ├── TIMEMACHINE.md              Retroactive recording
│   └── PLUGIN_GUIDE.md             Plugin development
│
├── 📁 plugins/                     🔌 Voice command plugins
│   ├── basic_commands.py           Hello, stop listening
│   ├── music_player.py             Music control
│   ├── llm_recorder.py             AI chat capture
│   ├── buffer.py                   Retroactive recording
│   └── icecast_streamer.py         Icecast2 streaming
│
├── 📁 tools/                       🔧 Utility scripts
│   ├── scan_music_library.py       Index your music
│   ├── inspect_conversations.py    View chat history
│   └── remember_jack_routing.py    Save JACK connections
│
├── 🎵 music_library_browser.py     GUI music browser
├── 🎙️ voice_command_client.py      Speech recognition
├── 🤖 llm_query_processor.py       AI chat handler
├── 🔊 tts_jack_client.py           Text-to-speech
├── 🎶 audio_jack_player.py         Multi-format music player
├── 🎛️ voice_assistant_tray.py      System tray GUI
│
├── 📁 model/                       🧠 Vosk speech model (download)
├── 📁 voices/                      🗣️ Piper TTS voices (download)
├── 📁 logs/                        📋 Runtime logs
└── ⚙️ voice_assistant_config.json  Configuration file
```

---

## 🐛 Troubleshooting

**Jackdaw not responding?**
- Check logs in `logs/` directory
- Verify audio connections in JACK patchbay
- See **[GETTING_STARTED.md](GETTING_STARTED.md#troubleshooting)** for detailed help

**Common issues:**
- **No wake word detection:** Check microphone connection, try different wake word
- **No speech output:** Verify TTS connections, check FFmpeg installed
- **Music won't play:** Run music scanner, check player connections
- **AI not responding:** Verify Ollama is running (`ollama list`)

**Logs are your friend:**
```bash
tail -f logs/voice_command.log   # Voice recognition
tail -f logs/llm_processor.log   # AI chat
tail -f logs/tts_client.log      # Speech synthesis
```

---

## 📜 License

See [LICENSE](LICENSE) file for details.

---

## 🙏 Credits

Jackdaw is built on the shoulders of giants:

- **[Vosk](https://alphacephei.com/vosk/)** - Offline speech recognition
- **[Piper](https://github.com/rhasspy/piper)** - Fast, local text-to-speech
- **[Ollama](https://ollama.com)** - Local LLM runtime
- **[JACK Audio](https://jackaudio.org)** - Professional audio routing
- **[PySide6](https://www.qt.io/qt-for-python)** - GUI framework
- **[Mutagen](https://mutagen.readthedocs.io/)** - Audio metadata handling

Special thanks to the open source community and **[Xiph.Org](https://xiph.org/)** for Ogg Vorbis, Opus, and FLAC - the foundation of open audio formats.

---

## 🚀 Get Started Now!

Ready to try Jackdaw? Head over to **[GETTING_STARTED.md](GETTING_STARTED.md)** for the complete setup guide!

**Questions?** Open an issue on [GitHub](https://github.com/applebiter/jackdaw/issues).

**Enjoy your voice-controlled audio system!** 🎵🎤
