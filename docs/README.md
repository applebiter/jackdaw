# JACK Voice Assistant

A voice-activated assistant system that runs on the JACK Audio Connection Kit, featuring wake word detection, speech recognition, LLM integration, and text-to-speech responses.

## Features

- **Always-on voice recognition** using Vosk
- **Wake word detection** for multi-host audio networks (default: "indigo")
- **Text capture** for LLM queries via voice commands
- **Local LLM integration** with Ollama
- **Text-to-speech responses** using Piper TTS
- **JACK audio integration** for professional audio routing
- **Multi-host support** - multiple machines can share the same JACK audio bus with unique wake words

## System Requirements

- **Python 3.12+**
- **JACK Audio Connection Kit** (jackd/pipewire-jack)
- **FFmpeg** (for audio conversion)
- **Ollama** (for local LLM)

### Ubuntu/Debian Installation
```bash
sudo apt install jackd2 ffmpeg
# Install Ollama from https://ollama.ai
```

## Installation

### Prerequisites

This system is designed for a **multi-host setup** where all hosts:
- Are connected via JackTrip for networked audio
- Maintain their **own local SQLite database** for conversation history
- Have unique hostnames matching their wake words

Each host stores its own conversations in a local SQLite database (default: `conversations.sqlite3`).

### 1. Install on Each Host

On each host:

1. **Clone or download this project**

2. **Create a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Download Vosk model**
```bash
# See model/README for download instructions
# For English, recommended: vosk-model-small-en-us-0.15
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model
```

5. **Download Piper TTS voice**
```bash
# See voices/README.md for download instructions and voice options
# IMPORTANT: Download BOTH .onnx and .onnx.json files for each voice!
# Example for lessac voice:
cd voices
wget https://github.com/rhasspy/piper/releases/latest/download/en_US-lessac-medium.onnx
wget https://github.com/rhasspy/piper/releases/latest/download/en_US-lessac-medium.onnx.json
```

6. **Install and start Ollama**
```bash
# Install from https://ollama.ai
# Pull a model (e.g., granite4:tiny-h)
ollama pull granite4:tiny-h
```

## Configuration

Edit `voice_assistant_config.json` on each host:

### Wake Word (IMPORTANT)
```json
"wake_word": "indigo"
```
**Set this to match the hostname** on each machine:
- alpha host → `"wake_word": "alpha"`
- bravo host → `"wake_word": "bravo"`
- charlie host → `"wake_word": "charlie"`

This allows each host to respond only to its own name on the shared audio network.

### Conversation Storage (Local SQLite)
```json
"database": {
  "enabled": true,
  "backend": "sqlite",
  "path": "conversations.sqlite3"
}
```
Each host writes to its own SQLite file. You can change `path` to any writable location (e.g. `"~/.local/share/jack-voice-assistant/conversations.sqlite3"`).

Set `"enabled": false` to disable conversation history and run stateless.

### LLM Model
```json
"ollama": {
  "model": "granite4:tiny-h"
}
```
Use any Ollama model you have installed.

### Voice Model
```json
"voice": {
  "synthesis": {
    "model_path": "voices/en_US-lessac-medium.onnx"
  }
}
```
Available voices: `lessac` (default), `amy`, `joe`

### Voice Activity Detection (VAD)
```json
"voice": {
  "recognition": {
    "vad_enabled": true,
    "vad_energy_threshold": 0.01,
    "vad_speech_timeout": 1.5
  }
}
```
- **vad_enabled** - Enable/disable VAD to reduce CPU during silence
- **vad_energy_threshold** - Energy level to detect speech (0.001-0.1, lower = more sensitive)
- **vad_speech_timeout** - Seconds to continue processing after speech stops (0.5-3.0)

## Usage

### Start the Voice Assistant
```bash
./start_voice_assistant.sh
```

This launches three components:
- **Voice Command Client** - Listens for voice commands via JACK
- **LLM Query Processor** - Sends queries to Ollama
- **TTS JACK Client** - Speaks responses through JACK

### Stop the Voice Assistant
```bash
./stop_voice_assistant.sh
```
Or use voice command: **"[wake word], stop listening"**

### Voice Commands

All commands must be prefaced with your wake word (e.g., "alpha"):

- **"[wake word], start recording"** - Begin capturing text for LLM query
- *Speak your question or request*
- **"[wake word], stop recording"** - End capture and send to LLM
- **"[wake word], stop listening"** - Shut down all components

### Connecting Audio

The voice assistant creates JACK ports:
- **VoiceCommandClient:input** - Connect your microphone here
- **TTSJackClient:output_L/R** - Connect to speakers/headphones

Use JACK connection tools:
```bash
jack_lsp                    # List ports
jack_connect <src> <dst>    # Connect ports
qjackctl                    # GUI connection manager
```

Or use JACK Studio/Carla/etc. for visual connection management.

## Architecture

### Components

1. **voice_command_client.py**
   - Captures audio from JACK
   - Performs speech recognition with Vosk
   - Detects wake word and commands
   - Captures text between start/stop recording commands
   - Writes queries to `llm_query.txt`

2. **llm_query_processor.py**
   - Polls for `llm_query.txt`
   - Sends queries to Ollama
   - Writes responses to `llm_response.txt`

3. **tts_jack_client.py**
   - Polls for `llm_response.txt`
   - Converts text to speech using Piper
   - Outputs audio to JACK (stereo, 44.1kHz)

### File-Based IPC

Components communicate via files:
- `llm_query.txt` - Voice queries
- `llm_response.txt` - LLM responses
- `.voice_assistant.pid` - Process IDs

### Logs

- `voice_command.log` - Voice recognition events
- `llm_processor.log` - LLM queries and responses
- `tts_client.log` - TTS synthesis events

Logs are auto-rotated at startup if >10MB.

## Multi-Host Conversation Memory

### How It Works

All hosts keep their own conversation history in a **local SQLite file**:

1. **Each host maintains its own session**
  - Sessions are identified by hostname and a `session_id` (UUID)
  - Each query/response is stored with hostname tag
  - Conversations are independent per host and do not leave the machine

2. **Conversation history is included in LLM context**
  - Previous messages are loaded from the local SQLite database
  - Sent to Ollama along with the new query
  - Token limit enforced (default: 30,000 tokens)

3. **Session management**
  - Active sessions auto-resume if within timeout (30 min default)
  - Old sessions marked inactive after timeout
  - New session created automatically when needed

### Example Workflow

```
User on host: "[wake word], start recording"
User: "What's the weather like?"
User: "[wake word], stop recording"
→ host stores query in its local SQLite DB, sends to LLM, stores response

Later...
User on same host: "[wake word], start recording"  
User: "Should I bring an umbrella?"
User: "[wake word], stop recording"
→ host loads previous weather conversation from its local DB
→ LLM has context to provide relevant answer
```

### Inspecting the Local Database

Use the `sqlite3` CLI to inspect a host's conversations:

```bash
sqlite3 conversations.sqlite3 'SELECT hostname, session_id, created_at, last_activity, is_active FROM conversation_sessions ORDER BY id DESC LIMIT 5;'

sqlite3 conversations.sqlite3 "SELECT role, substr(content,1,80) AS preview, tokens, created_at FROM messages ORDER BY id DESC LIMIT 10;"
```

## Troubleshooting

### No audio capture
- Verify JACK is running: `jack_lsp`
- Connect microphone to `VoiceCommandClient:input`
- Check audio levels in JACK mixer

### No TTS playback
- Verify FFmpeg is installed: `ffmpeg -version`
- Check JACK connections to speakers
- Review `tts_client.log` for errors

### Vosk not recognizing speech
- Verify model downloaded to `model/` directory
- Check microphone levels and JACK sample rate (44.1kHz recommended)
- Review `voice_command.log`

### Ollama not responding
- Verify Ollama is running: `ollama list`
- Check model is installed: `ollama pull granite4:tiny-h`
- Review `llm_processor.log`

### Wake word not working
- Speak clearly with a short pause before the command
- Try adjusting `wake_word` in config (shorter words work better)
- Check `voice_command.log` to see what's being recognized

## Testing the System

### 1. Test Conversation Store (Optional)
```bash
python test_local_conversation_store.py
```
This verifies the local SQLite-backed history store.

### 2. Test End-to-End
On any host:
```bash
./start_voice_assistant.sh

# In audio setup (Carla/QJackCtl):
# - Connect microphone to VoiceCommandClient:input
# - Connect TTSJackClient outputs to speakers

# Speak commands:
"[your wake word], start recording"
"What is the capital of France?"
"[your wake word], stop recording"
# Wait for TTS response

# Check database for stored conversation
sqlite3 conversations.sqlite3 "SELECT * FROM messages WHERE hostname='$(hostname)' ORDER BY created_at DESC LIMIT 4;"
```

### 3. Test Multi-Host
Repeat on another host (e.g., violet) with different wake word.
Both conversations will be stored independently in the same database.

## Development

### Project Structure
```
jack_experiments/
├── voice_command_client.py      # Voice recognition & command detection
├── llm_query_processor.py       # LLM integration
├── tts_jack_client.py          # Text-to-speech output
├── voice_assistant_config.json  # Unified configuration
├── start_voice_assistant.sh     # Launcher script
├── stop_voice_assistant.sh      # Shutdown script
├── model/                       # Vosk speech recognition model
└── voices/                      # Piper TTS voice models
    ├── en_US-lessac-medium.onnx
    ├── en_US-amy-medium.onnx
    └── en_US-joe-medium.onnx
```

### Adding Custom Commands

Edit `voice_command_client.py` and add to the `main()` function:

```python
def my_custom_command():
    print("Custom command executed!")

client.register_command("my phrase", my_custom_command)
```

## License

This is an experimental project. Use at your own risk.

## Credits

- **Vosk** - Speech recognition (https://alphacephei.com/vosk/)
- **Piper** - Text-to-speech (https://github.com/rhasspy/piper)
- **Ollama** - Local LLM runtime (https://ollama.ai)
- **JACK** - Professional audio routing (https://jackaudio.org)
