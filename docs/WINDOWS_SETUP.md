# Jackdaw Windows Setup Guide

**Quick Start Guide for Windows 10/11**

Get Jackdaw running on Windows for JackTrip collaboration and voice-controlled audio.

---

## Prerequisites

### Required Software

1. **Python 3.8 or newer**
   - Download: https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation
   - Verify: Open Command Prompt and run `python --version`

2. **JACK Audio Connection Kit for Windows**
   - Download: https://jackaudio.org/downloads/
   - Install QjackCtl (JACK control GUI) for easier setup
   - Start JACK before running Jackdaw

3. **JackTrip** (for network collaboration)
   - Download: https://github.com/jacktrip/jacktrip/releases
   - Extract `jacktrip.exe` to a folder in your PATH
   - Or place in the Jackdaw directory

4. **Git for Windows** (for cloning repository)
   - Download: https://git-scm.com/download/win
   - Or download ZIP from GitHub

---

## Installation Steps

### 1. Clone or Download Jackdaw

**Option A: Using Git**
```cmd
cd %USERPROFILE%\Documents
git clone https://github.com/applebiter/jackdaw.git
cd jackdaw
```

**Option B: Download ZIP**
1. Go to https://github.com/applebiter/jackdaw
2. Click "Code" → "Download ZIP"
3. Extract to `Documents\jackdaw`
4. Open Command Prompt in that folder

### 2. Create Virtual Environment

```cmd
python -m venv .venv
```

This creates a `.venv` folder with an isolated Python environment.

### 3. Activate Virtual Environment

```cmd
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your prompt.

### 4. Install Dependencies

```cmd
pip install -r requirements.txt
```

This will take a few minutes. It installs:
- PySide6 (GUI)
- JACK-Client (audio)
- Vosk (speech recognition)
- Piper TTS (text-to-speech)
- And other required packages

### 5. Download Speech Recognition Model

1. Go to https://alphacephei.com/vosk/models
2. Download `vosk-model-en-us-0.22` (or similar English model)
3. Extract to `model/` folder in jackdaw directory
4. The structure should be: `jackdaw/model/am/`, `jackdaw/model/conf/`, etc.

### 6. Download TTS Voice

1. Go to https://huggingface.co/rhasspy/piper-voices/tree/main
2. Navigate to `en/en_US/`
3. Download a voice (e.g., `lessac/medium/`)
   - Download both `.onnx` and `.onnx.json` files
4. Place in `voices/` folder

### 7. Configure Jackdaw

```cmd
copy voice_assistant_config.json.example voice_assistant_config.json
```

Edit `voice_assistant_config.json` with Notepad:

**Minimal Configuration for JackTrip Client:**
```json
{
  "voice": {
    "recognition": {
      "model_path": "model",
      "wake_word": "alpha",
      "sample_rate": 16000
    }
  },
  "tts": {
    "voice_model": "voices/en_US-lessac-medium.onnx",
    "sample_rate": 22050
  },
  "plugins": {
    "basic_commands": {
      "enabled": true
    },
    "jacktrip_client": {
      "enabled": true
    }
  },
  "jacktrip_hub": {
    "hub_url": "https://YOUR_HUB_IP:8000",
    "username": "your_username",
    "password": "your_password"
  }
}
```

**Important**: Replace `YOUR_HUB_IP`, `your_username`, and `your_password` with your actual hub details.

---

## Running Jackdaw

### 1. Start JACK Audio

1. Open QjackCtl (JACK Control)
2. Click "Start"
3. Verify JACK is running (icon turns green)

### 2. Launch Jackdaw

**From Command Prompt:**
```cmd
cd %USERPROFILE%\Documents\jackdaw
python launch.py
```

**Or create a shortcut:**
1. Right-click on desktop → New → Shortcut
2. Location: `python.exe C:\Users\YourName\Documents\jackdaw\launch.py`
3. Name it "Jackdaw"

### 3. Check System Tray

Look for the Jackdaw icon in your system tray (bottom-right corner, near the clock).

Right-click the icon to access the menu.

---

## Connecting Audio in JACK

### Using QjackCtl Patchbay

1. Open QjackCtl
2. Click "Connect" button
3. Connect your microphone to Jackdaw inputs
4. Connect Jackdaw outputs to your speakers/headphones

**Typical connections for JackTrip:**
```
Microphone → jacktrip_client:send_1
jacktrip_client:receive_1 → system:playback_1
```

---

## Voice Commands

Once running, say your wake word followed by commands:

**JackTrip Collaboration:**
```
"Alpha, start jam session"       # Connect to hub and join room
"Alpha, jam session status"      # Check connection status
"Alpha, who's in the jam"        # See participant count
"Alpha, stop jam session"        # Disconnect from hub
```

**Basic Commands:**
```
"Alpha, hello"                   # Test recognition
"Alpha, stop listening"          # Shut down Jackdaw
```

---

## Troubleshooting

### Python not found
- Reinstall Python and check "Add Python to PATH"
- Or use full path: `C:\Python311\python.exe`

### pip install fails
- Update pip: `python -m pip install --upgrade pip`
- Try: `.venv\Scripts\pip.exe install -r requirements.txt`

### JACK won't start
- Close other audio applications
- Check sample rate matches your audio interface
- Try running QjackCtl as Administrator

### No wake word detection
- Check microphone is connected in JACK patchbay
- Verify model is in `model/` folder
- Try speaking louder or closer to microphone
- Check `logs/voice_command.log` for errors

### Voice commands not working
- Verify plugins are enabled in config
- Check wake word is correct ("alpha" by default)
- Look in system tray menu → View Logs

### JackTrip connection fails
- Verify hub URL is correct (must start with `https://`)
- Check firewall allows port 8000 (TCP) and 4464-4563 (UDP)
- Confirm username and password in config
- Check `logs/voice_command.log` for error details

### Process cleanup issues on Windows
- Jackdaw should auto-cleanup on exit
- If stuck, use Task Manager to end Python processes
- Or run: `taskkill /F /IM python.exe`

---

## Logs Location

Logs are in the `logs/` folder:
```
jackdaw\logs\voice_command.log    # Voice recognition
jackdaw\logs\llm_processor.log    # AI chat (if enabled)
jackdaw\logs\tts_client.log       # Text-to-speech
```

View with: `notepad logs\voice_command.log`

---

## Updating Jackdaw

```cmd
cd %USERPROFILE%\Documents\jackdaw
git pull origin main
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

---

## Minimal Testing Checklist

Before your first band session, test:

- [ ] JACK starts without errors
- [ ] Jackdaw launches (icon in system tray)
- [ ] Wake word detection works ("Alpha, hello")
- [ ] JackTrip connects to hub ("Alpha, start jam session")
- [ ] Audio routes through JACK (hear yourself)
- [ ] Can disconnect cleanly ("Alpha, stop jam session")

---

## Network Setup for Band

### Firewall Rules

Open Windows Defender Firewall:
1. Start → "Windows Defender Firewall with Advanced Security"
2. Inbound Rules → New Rule
3. Port → TCP → 8000 → Allow
4. Inbound Rules → New Rule
5. Port → UDP → 4464-4563 → Allow

### Router Port Forwarding (if hosting hub)

Forward these ports to your PC:
- TCP 8000 (Hub API)
- UDP 4464-4563 (JackTrip audio)

Consult your router manual for port forwarding setup.

---

## Performance Tips

### For Best Latency

1. **Use wired Ethernet** (not WiFi)
2. **Close unnecessary programs** (browsers, etc.)
3. **Reduce JACK buffer size** (in QjackCtl settings)
4. **Disable Windows audio enhancements**
   - Sound Settings → Device Properties → Disable all enhancements
5. **Use ASIO audio interface** (better than Windows audio)

### If Audio Crackles

- Increase JACK buffer size (256 or 512 samples)
- Close background programs
- Check CPU usage in Task Manager
- Update audio interface drivers

---

## Getting Help

- **Documentation**: `docs/` folder in Jackdaw directory
- **Issues**: https://github.com/applebiter/jackdaw/issues
- **Logs**: Check `logs/` folder for error details
- **Voice Commands**: System tray menu → Reference → Voice Commands

---

## What Works on Windows

✅ System tray application
✅ Voice recognition (Vosk)
✅ Text-to-speech (Piper)
✅ JackTrip client plugin
✅ JACK audio routing
✅ Basic voice commands
✅ Plugin system

⚠️ **Not yet tested on Windows:**
- Music library scanning (Linux paths)
- LLM chat (Ollama on Windows)
- Icecast streaming
- Buffer recording

**Focus**: JackTrip collaboration is the primary use case for Windows.

---

## Next Steps

1. **Test locally** - Verify everything works on your PC
2. **Join a session** - Connect to your hub server
3. **Invite bandmates** - Share this guide with them
4. **Practice** - Get comfortable with voice commands
5. **Jam!** - Collaborate in real-time

---

## Frequently Asked Questions

**Q: Do I need a hub server?**
A: Yes, for JackTrip collaboration. One person (usually on Linux) runs the hub, others connect as clients.

**Q: Can I run the hub on Windows?**
A: Not yet tested. The hub is designed for Linux VPS. Use Windows as a client only for now.

**Q: Why does it need JACK?**
A: JACK provides low-latency audio routing needed for real-time collaboration.

**Q: Can I use a different wake word?**
A: Yes! Edit `"wake_word": "alpha"` in the config to any word in your vocabulary.

**Q: How much bandwidth does JackTrip use?**
A: Depends on channels and quality. Typically 1-5 Mbps per participant.

**Q: Can I test without a hub?**
A: Yes! You can test voice commands and TTS without JackTrip. Just disable the plugin in config.

---

## Contact & Support

- GitHub: https://github.com/applebiter/jackdaw
- Issues: https://github.com/applebiter/jackdaw/issues

**For band collaboration setup, coordinate with your hub operator for connection details.**

Happy jamming! 🎵🎤
