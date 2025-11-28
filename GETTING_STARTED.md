# Getting Started with Jackdaw

**Welcome!** This guide will help you set up and use Jackdaw, a voice-controlled networked audio system. Whether you're completely new to JACK Audio or an experienced audio engineer, this guide walks you through everything step-by-step.

## What is Jackdaw?

Jackdaw is a voice assistant that lives in your audio system. Instead of being yet another smart speaker, it integrates directly with professional audio software, letting you:

- **Control your music library by voice** - "Play artist Pink Floyd", "Next track", "Volume up"
- **Stream to Icecast2 servers** - Broadcast your audio to the internet
- **Record retroactively** - Save audio that already happened using buffer
- **Chat with an AI** - Ask questions and get spoken responses using local LLM (Ollama)
- **Collaborate over networks** - Use JackTrip for real-time audio with friends

All of this runs locally on your computer with full privacy - no cloud required!

## Who is this for?

- **Musicians** wanting voice control over their setup
- **Podcasters** needing easy recording and streaming
- **Radio stations** looking for automated broadcasting
- **Audio enthusiasts** exploring networked audio
- **Privacy-conscious users** who want local AI assistants

**No previous JACK experience required!** This guide assumes you're starting from scratch.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Installation](#quick-installation)
3. [First Time Setup](#first-time-setup)
4. [Basic Usage](#basic-usage)
5. [Common Tasks](#common-tasks)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps](#next-steps)

---

## Prerequisites

### What You'll Need

**Hardware:**
- Any computer running Linux (Ubuntu, Fedora, Arch, etc.)
- Microphone (built-in or USB)
- Speakers or headphones
- At least 2GB free disk space
- Ideally 8GB+ RAM (for LLM features)

**Software (we'll install these):**
- JACK Audio Connection Kit (sound routing system)
- FFmpeg (audio/video processing)
- Ollama (local AI assistant - optional but recommended)
- Python 3.8 or newer

**Time Required:** 15-30 minutes for first-time setup

---

## Quick Installation

### Step 1: Install System Dependencies

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install jackd2 ffmpeg libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 git
```

**On Fedora:**
```bash
sudo dnf install jack-audio-connection-kit ffmpeg libxcb xcb-util-cursor git
```

**On Arch Linux:**
```bash
sudo pacman -S jack2 ffmpeg libxcb xcb-util-cursor git
```

**What are these?**
- `jackd2` - Professional audio routing (like virtual audio cables)
- `ffmpeg` - Audio format conversion and streaming
- `libxcb-*` - Required for the graphical tray application
- `git` - For downloading Jackdaw

### Step 2: Install Ollama (Optional but Recommended)

Ollama provides the AI chat features. Skip this if you only want music control.

```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download a small, fast language model
ollama pull granite3.1:2b
```

**Alternative models:**
- `llama3.2:3b` - Very good, 3GB RAM
- `granite3.1:2b` - Faster, 2GB RAM
- `qwen2.5:3b` - Excellent for chat, 3GB RAM

### Step 3: Download Jackdaw

```bash
# Go to your preferred installation location
cd ~

# Clone the repository
git clone https://github.com/applebiter/jackdaw.git
cd jackdaw
```

### Step 4: Run the Installer

```bash
./install.sh
```

The installer will:
1. ✅ Check for required system packages
2. ✅ Create a Python virtual environment
3. ✅ Install Python dependencies
4. ✅ Create necessary directories
5. ✅ Set up configuration files
6. ✅ Install desktop launcher and autostart
7. ⚠️ Remind you to download models (next step)

This takes 2-5 minutes depending on your internet speed.

---

## First Time Setup

### Step 5: Download Voice Models

Jackdaw needs two models to understand and speak:

#### A) Speech Recognition Model (Vosk)

**What it does:** Converts your speech to text so Jackdaw understands commands.

```bash
cd ~/jackdaw

# Download the small English model (40 MB, recommended)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

# Extract it
unzip vosk-model-small-en-us-0.15.zip

# Move files into the model directory
rm -rf model/*  # Clear the empty model directory
mv vosk-model-small-en-us-0.15/* model/

# Clean up
rm vosk-model-small-en-us-0.15.zip
rmdir vosk-model-small-en-us-0.15
```

**Other languages?** Visit https://alphacephei.com/vosk/models for models in 20+ languages.

#### B) Text-to-Speech Voice (Piper)

**What it does:** Converts Jackdaw's responses to spoken audio.

```bash
cd ~/jackdaw/voices

# Download the recommended voice (lessac - clear and professional)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Make sure you got BOTH files (.onnx and .onnx.json)
ls -lh
```

**Want a different voice?** Listen to samples at https://rhasspy.github.io/piper-samples/ and download from https://huggingface.co/rhasspy/piper-voices/tree/main/en

**Important:** Always download BOTH the `.onnx` and `.onnx.json` files!

### Step 6: Configure Your Wake Word

The wake word is what you say to get Jackdaw's attention (like "Alexa" or "Hey Siri").

```bash
cd ~/jackdaw
nano voice_assistant_config.json
```

Find this line:
```json
"wake_word": "alpha",
```

Change it to something you like:
- `"jackdaw"` - Say the name of the program
- `"computer"` - Star Trek style
- `"jarvis"` - Iron Man style
- Your computer's hostname (if on a network)

**Tips for choosing a wake word:**
- Short words (1-2 syllables) work best
- Avoid common words you use in conversation
- Test different words to find what Vosk recognizes well

Save and exit (Ctrl+X, then Y, then Enter).

### Step 7: Configure the LLM Model

If you installed Ollama and pulled a different model, update the config:

```bash
nano voice_assistant_config.json
```

Find:
```json
"ollama": {
  "model": "granite3.1:2b"
}
```

Change to your preferred model if different. Save and exit.

---

## Basic Usage

### Starting Jackdaw

You have three ways to start Jackdaw:

**Option 1: Applications Menu (Easiest)**
1. Open your applications menu (press Super/Windows key)
2. Search for "Jackdaw"
3. Click the icon

**Option 2: Desktop Tray App**
```bash
cd ~/jackdaw
./launch_tray_app.sh
```
A bird icon appears in your system tray (top-right or bottom-right corner).

**Option 3: Command Line**
```bash
cd ~/jackdaw
./start_voice_assistant.sh
```

**What's happening behind the scenes:**
1. JACK audio system starts (if not already running)
2. Voice recognition begins listening
3. LLM processor starts waiting for queries
4. Text-to-speech engine loads
5. All plugins activate

### Connecting Your Audio

**Using Carla (Recommended for Beginners):**

Carla is a visual audio patchbay that makes JACK connections easy.

```bash
# Install Carla
sudo apt install carla  # Ubuntu/Debian
sudo dnf install carla  # Fedora

# Start Carla
carla
```

In Carla's patchbay view:
1. Find "**VoiceCommandClient**" - this needs audio INPUT
2. Find your microphone (might be called "system:capture_1" or your USB device name)
3. **Drag a cable** from your microphone to VoiceCommandClient:input

4. Find "**TTSJackClient**" - this produces audio OUTPUT
5. Find your speakers (usually "system:playback_1" and "playback_2")
6. **Drag cables** from TTSJackClient:out_L → playback_1 and out_R → playback_2

**Using QjackCtl (Alternative):**
```bash
qjackctl
```
Click the "Graph" button and make the same connections visually.

**Using Command Line:**
```bash
# List all audio ports
jack_lsp

# Connect microphone to voice recognition
jack_connect system:capture_1 VoiceCommandClient:input

# Connect speech output to speakers
jack_connect TTSJackClient:out_L system:playback_1
jack_connect TTSJackClient:out_R system:playback_2
```

### Your First Voice Command

Now for the moment of truth! Let's test if Jackdaw can hear you:

1. **Speak clearly into your microphone:**
   ```
   "[YOUR WAKE WORD], hello"
   ```
   For example: **"jackdaw, hello"**

2. **What should happen:**
   - Jackdaw recognizes your wake word
   - Processes the "hello" command
   - Speaks back: "Hello! How can I help you?"

3. **If it works:** 🎉 Congratulations! Jackdaw is listening!

4. **If nothing happens:** See [Troubleshooting](#troubleshooting) below.

### Stopping Jackdaw

**Voice command (easiest):**
```
"[wake word], stop listening"
```

**From tray app:**
Right-click the tray icon → Stop Voice Assistant

**From command line:**
```bash
cd ~/jackdaw
./stop_voice_assistant.sh
```

---

## Common Tasks

### Playing Music

First, you need to scan your music collection into Jackdaw's database:

```bash
cd ~/jackdaw
source .venv/bin/activate
python tools/scan_music_library.py
```

This will prompt you for your music folder location and scan for:
- Ogg Vorbis (.ogg)
- Opus (.opus)
- FLAC (.flac)
- MP3 (.mp3)

**Now try these voice commands:**

```
"[wake word], play random track"
"[wake word], play artist Pink Floyd"
"[wake word], play album Dark Side of the Moon"
"[wake word], play genre jazz"
"[wake word], next track"
"[wake word], volume up"
"[wake word], shuffle on"
"[wake word], stop playing music"
```

**Connect the music player output:**
In Carla/QjackCtl, connect:
- OggPlayer:out_L → system:playback_1
- OggPlayer:out_R → system:playback_2

### Browsing Your Music Library

Launch the graphical music browser:

```bash
cd ~/jackdaw
./launch_music_browser.sh
```

**Or from the tray app:** Right-click tray icon → Tools → Music Library Browser

**Features:**
- **Search** by artist, album, title, genre, or year
- **Sort** by clicking column headers
- **Select multiple tracks** (Ctrl+Click or Shift+Click)
- **Build playlists** with the playlist panel
- **Play locally** on your JACK audio system
- **Stream to Icecast2** if configured
- **Save/load playlists** as JSON files

### Chatting with AI

**Start the chat:**
```
"[wake word], start chat"
```

**Ask your question:**
```
"Who were the original members of The Beatles?"
```
(Or any question you'd ask ChatGPT)

**Send it to the AI:**
```
"[wake word], stop chat"
```

**Wait for response:**
Jackdaw will:
1. Send your question to Ollama
2. Get the AI's response
3. Speak it back to you through your speakers

**Conversation memory:**
Jackdaw remembers previous conversations! Ask follow-up questions and it will understand context.

### Retroactive Recording (Buffer)

Ever wish you could record something that just happened? The buffer keeps a rolling recording:

```
"[wake word], start the buffer"
```
(Now everything is being buffered in memory)

**Later, when something cool happens:**
```
"[wake word], save that"
```

This saves the last 300 seconds (5 minutes) to a WAV file in `~/recordings/`.

**Stop buffering:**
```
"[wake word], stop the buffer"
```

**Check status:**
```
"[wake word], buffer status"
```

### Streaming to Icecast2

Broadcasting to the internet requires an Icecast2 server. See `docs/STREAMING.md` for complete setup, but here's the quick version:

**Configure streaming:**
```bash
nano voice_assistant_config.json
```

Add your Icecast2 server details:
```json
"icecast_streamer": {
  "enabled": true,
  "server": "localhost",
  "port": 8000,
  "password": "hackme",
  "mount": "/stream",
  "format": "ogg",
  "bitrate": 128
}
```

**Voice commands:**
```
"[wake word], start streaming"
"[wake word], stop streaming"
```

---

## Troubleshooting

### Jackdaw doesn't respond to wake word

**Check if voice recognition is working:**
```bash
tail -f ~/jackdaw/logs/voice_command.log
```
Speak into your microphone. You should see your words appear in the log.

**If you see nothing:**
1. Check microphone is connected in Carla/QjackCtl
2. Test microphone: `arecord -l` (should list your device)
3. Check JACK is capturing audio: `jack_meter VoiceCommandClient:input`

**If you see words but not your wake word:**
1. Try a different wake word (some words are recognized better)
2. Speak more clearly and slowly
3. Make sure you're saying the EXACT wake word in your config

### No speech from Jackdaw

**Check if TTS is producing audio:**
```bash
tail -f ~/jackdaw/logs/tts_client.log
```

**Common issues:**
1. **TTS output not connected to speakers** - Check connections in Carla
2. **FFmpeg not installed** - Run: `ffmpeg -version`
3. **Wrong voice model path** - Check `voice_assistant_config.json`
4. **Missing .onnx.json file** - Download both voice files!

### Music won't play

**Check the music database:**
```bash
cd ~/jackdaw
source .venv/bin/activate
python tools/scan_music_library.py
```

Make sure it found your music files.

**Check if player is connected:**
In Carla, connect OggPlayer outputs to speakers.

**Check logs:**
```bash
tail -f ~/jackdaw/logs/voice_command.log
```

### LLM/AI not responding

**Is Ollama running?**
```bash
ollama list
```
Should show your installed models.

**Is the model pulled?**
```bash
ollama pull granite3.1:2b
```

**Check logs:**
```bash
tail -f ~/jackdaw/logs/llm_processor.log
```

### System tray icon missing

**Install system tray support:**

**GNOME users:**
```bash
# Install AppIndicator extension
gnome-extensions-app
# Search for "AppIndicator" and enable it
```

**Alternative:** Use command-line mode instead:
```bash
./start_voice_assistant.sh
```

### High CPU usage

**Disable Voice Activity Detection for testing:**
```bash
nano voice_assistant_config.json
```

Set:
```json
"vad_enabled": false
```

**Use a smaller Vosk model:**
The small model (40MB) uses much less CPU than large models.

---

## Next Steps

### Explore Advanced Features

**Read the documentation:**
- `docs/MUSIC_DATABASE.md` - Music library system details
- `docs/STREAMING.md` - Icecast2 broadcasting setup
- `docs/TIMEMACHINE.md` - Retroactive recording guide
- `docs/PLUGIN_GUIDE.md` - Create your own voice commands

**Try the music browser:**
```bash
./launch_music_browser.sh
```

**Create playlists:**
Open music browser, select tracks, click "Add to Playlist", save as JSON.

### Customize Your Setup

**Change the voice:**
Download different Piper voices from https://rhasspy.github.io/piper-samples/

**Add custom commands:**
See `docs/PLUGIN_GUIDE.md` for creating your own plugins.

**Adjust sensitivity:**
Edit `voice_assistant_config.json`:
- `vad_energy_threshold` - Lower = more sensitive (0.001 to 0.1)
- `vad_speech_timeout` - How long to wait for speech (seconds)

### Join the Network

**Use JackTrip for real-time collaboration:**
Connect with friends over the internet for zero-latency jamming!

**Set up Icecast2 for broadcasting:**
Stream your audio to listeners worldwide.

See `docs/STREAMING.md` for the complete guide.

---

## Getting Help

**Check the logs first:**
```bash
cd ~/jackdaw/logs
tail -f voice_command.log    # Voice recognition
tail -f llm_processor.log    # AI chat
tail -f tts_client.log       # Speech synthesis
```

**Use verbose mode for debugging:**
```bash
nano voice_assistant_config.json
```
Change `"log_level": "INFO"` to `"log_level": "DEBUG"`

**Read the docs:**
- Main README: `README.md`
- Full documentation: `docs/README.md`
- Quick command reference: `docs/QUICK_REFERENCE.md`

**Report issues:**
https://github.com/applebiter/jackdaw/issues

---

## Summary Checklist

Before asking for help, verify:

- ✅ System dependencies installed (JACK, FFmpeg, libxcb)
- ✅ Ollama installed and model pulled
- ✅ Vosk model downloaded to `model/` directory
- ✅ Piper voice files (BOTH .onnx and .onnx.json) in `voices/`
- ✅ Configuration file has correct wake word
- ✅ Audio connections made in Carla/QjackCtl
- ✅ Microphone working and connected to VoiceCommandClient
- ✅ TTS output connected to speakers
- ✅ Logs checked for error messages

---

## Frequently Asked Questions (FAQ)

### General Questions

**Q: Do I need to be connected to the internet?**
A: Only for initial setup (downloading models and packages). Once installed, Jackdaw runs 100% offline. Ollama LLM runs locally on your machine.

**Q: Is my conversation data sent anywhere?**
A: No. Everything is stored locally in `conversations.sqlite3`. Your voice, questions, and responses never leave your computer.

**Q: How much disk space do I need?**
A: Minimum 2GB:
- Vosk model: 40 MB (small) to 1.8 GB (large)
- Piper voice: 20-30 MB per voice
- Ollama models: 2-7 GB depending on model
- Python packages: ~500 MB
- Your music library database: varies

**Q: What if I don't have a music library?**
A: That's fine! You can still use all other features (AI chat, buffer recording, streaming). Music features are optional.

**Q: Can I use Jackdaw without JACK Audio?**
A: No, JACK is fundamental to how Jackdaw routes audio. But don't worry - JACK is easier than it sounds! This guide walks you through it.

### Technical Questions

**Q: Why does Jackdaw use JACK instead of PulseAudio/PipeWire?**
A: JACK provides professional-grade, low-latency audio routing. It lets you connect any audio source to any destination, essential for live streaming, recording, and networked audio. Many modern systems use PipeWire which includes JACK compatibility.

**Q: Can I use PipeWire instead of JACK?**
A: Yes! PipeWire includes JACK compatibility. Install `pipewire-jack` and Jackdaw will work seamlessly.

**Q: Does Jackdaw work on Wayland?**
A: Yes, the tray app works on both X11 and Wayland.

**Q: What about macOS or Windows?**
A: Jackdaw is Linux-only currently. JACK exists on macOS/Windows, but other components (Ollama, installation script) are Linux-specific. Contributions welcome!

**Q: How do I update Jackdaw?**
A: ```bash
cd ~/jackdaw
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Voice Recognition Questions

**Q: Why doesn't Jackdaw understand my accent?**
A: Vosk models are language-specific. Visit https://alphacephei.com/vosk/models and download a model trained for your language or dialect.

**Q: Can I use a different language?**
A: Yes! Download Vosk and Piper models for your language:
- Vosk models: https://alphacephei.com/vosk/models (20+ languages)
- Piper voices: https://huggingface.co/rhasspy/piper-voices (40+ languages)

**Q: What are good wake words?**
A: Short, distinct words work best:
- ✅ Good: "alpha", "bravo", "jackdaw", "computer"
- ❌ Avoid: "hey", "okay", "yes" (too common in speech)

Test different words to see what Vosk recognizes consistently.

**Q: Can I have multiple wake words?**
A: Not currently. Each Jackdaw instance has one wake word. For multi-user setups, run multiple instances with different wake words.

### Performance Questions

**Q: How much RAM does Jackdaw need?**
A: Typical usage:
- Vosk (small model): ~440 MB
- Piper TTS: ~490 MB
- Ollama LLM: 2-7 GB depending on model
- Total: 4-8 GB recommended

**Q: Is Jackdaw CPU-intensive?**
A: With Voice Activity Detection enabled:
- Idle: 0-2% CPU
- During speech: ~20% CPU
- TTS synthesis: ~19% CPU (only when speaking)

Very lightweight when not actively processing.

**Q: Can I run Jackdaw on a Raspberry Pi?**
A: Possibly on Pi 4 or 5 with 4GB+ RAM. Use small Vosk model and lightweight Ollama model (granite3.1:2b). Not recommended for older Pis.

### Troubleshooting Questions

**Q: "Could not load the Qt platform plugin 'xcb'" error?**
A: Install Qt platform libraries:
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
```

**Q: "JACK server not running" error?**
A: Start JACK first:
```bash
# Option 1: Use QjackCtl
qjackctl

# Option 2: Start manually
jackd -d alsa
```

**Q: Jackdaw seems frozen - how do I force stop it?**
A: ```bash
cd ~/jackdaw
./stop_voice_assistant.sh
# If that doesn't work:
pkill -9 -f voice_command_client
pkill -9 -f llm_query_processor
pkill -9 -f tts_jack_client
```

**Q: Where can I get more help?**
A: 
1. Check the full documentation in `docs/`
2. Enable debug logging: Set `"log_level": "DEBUG"` in config
3. Check logs in `logs/` directory
4. Open an issue: https://github.com/applebiter/jackdaw/issues

---

## What's Next?

Now that you're set up, here are some ideas:

🎵 **Build a music playlist** - Open the music browser and create your first playlist

🤖 **Have a conversation with AI** - Ask Jackdaw complex, multi-part questions

📡 **Set up streaming** - Share your audio with the world via Icecast2

🎙️ **Try retroactive recording** - Capture that amazing guitar riff after it happened

🔌 **Write a plugin** - Add your own custom voice commands

👥 **Connect with friends** - Use JackTrip for real-time audio collaboration

---

**Welcome to Jackdaw!**

You now have a privacy-respecting, locally-running voice assistant integrated into your professional audio workflow. Experiment, explore, and make it your own!

**Questions?** Check the docs or open an issue on GitHub.

**Enjoy!** 🎵🎤🎧
