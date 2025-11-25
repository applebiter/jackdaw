# Voice Assistant Dashboard

A web-based monitoring and control interface for the JACK Voice Assistant.

## Features

### 📊 Overview Tab
- **System Status**: Real-time process monitoring, JACK status, disk space
- **Now Playing**: Current track information with auto-refresh
- **Ring Buffer Status**: Recording state and buffer information
- **Music Library Stats**: Track count, artists, albums, total duration

### 📋 Logs Tab
- **Voice Commands**: Real-time voice command recognition log
- **LLM Processor**: LLM query and response log
- **TTS Client**: Text-to-speech synthesis log
- Auto-refreshing log tails (last 50 lines)

### 🎙️ Recordings Tab
- Browse recent ring buffer recordings
- File size and creation date
- Quick access to recordings directory

### ⚙️ Configuration Tab
- View current voice assistant configuration
- JSON display of all settings

## Usage

### Quick Start

```bash
# Install gradio (if not already installed)
pip install gradio

# Start dashboard only (voice assistant must already be running)
python gradio_dashboard.py

# Or start both together
./start_with_dashboard.sh
```

### Access

- **Local**: http://localhost:7865
- **Network**: http://YOUR_IP:7865 (accessible from any device on your network)
- **Mobile**: Works great on phones/tablets!

### Port Configuration

The dashboard runs on **port 7865** by default. To change:

```python
# In gradio_dashboard.py, modify:
interface.launch(
    server_port=YOUR_PORT  # Change this
)
```

## Requirements

- gradio >= 4.44.0 (automatically installed via requirements.txt)
- Voice assistant must be running for full functionality
- JACK server must be running for audio status

## Architecture

### Completely Optional
The dashboard is 100% optional and does not interfere with voice assistant operation:

- Voice assistant runs independently
- Dashboard reads log files and status
- No modification to core voice assistant code
- Can start/stop dashboard anytime

### Read-Only Monitoring
Current version is monitoring-only:
- Views logs in real-time
- Shows system status
- Displays recordings
- Does not send commands (voice control only)

**Future Enhancement**: Add control buttons for start/stop/save commands

### Data Sources

```
Dashboard reads from:
├── logs/voice_command.log    # Voice recognition events
├── logs/llm_processor.log     # LLM queries/responses
├── logs/tts_client.log        # TTS synthesis events
├── voice_assistant_config.json # Configuration
├── music_library.sqlite3       # Music database stats
└── ~/recordings/*.wav          # Ring buffer recordings
```

## Auto-Refresh Intervals

- System Status: 5 seconds
- Now Playing: 2 seconds
- Buffer Status: 3 seconds
- Voice Logs: 3 seconds
- LLM/TTS Logs: 5 seconds
- Recordings List: 5 seconds
- Music Stats: 30 seconds

## Use Cases

### 1. Remote Monitoring
Access dashboard from phone while playing music in another room.

### 2. Debugging
Watch real-time logs to troubleshoot voice recognition or command issues.

### 3. Session Recording
Monitor ring buffer status and browse/download recordings without SSH.

### 4. Music Library
View statistics about your music collection.

### 5. System Health
Check JACK status, process health, and disk space at a glance.

## Tips

### Enable Browser Auto-Open
```python
# In gradio_dashboard.py:
interface.launch(
    inbrowser=True  # Auto-opens browser on start
)
```

### Public Access (Gradio Share)
```python
# In gradio_dashboard.py:
interface.launch(
    share=True  # Creates public gradio.app link
)
```

**Warning**: Only enable share for temporary access. Anyone with the link can view your logs.

### Run Dashboard in Background
```bash
# Start dashboard as background process
nohup python gradio_dashboard.py > dashboard.log 2>&1 &

# View dashboard log
tail -f dashboard.log

# Stop dashboard
pkill -f gradio_dashboard.py
```

### Firewall Configuration
If accessing from other devices on network:

```bash
# Allow port 7865
sudo ufw allow 7865/tcp

# Or for specific subnet only
sudo ufw allow from 192.168.1.0/24 to any port 7865
```

## Troubleshooting

### Dashboard Won't Start

**Check if port is already in use:**
```bash
lsof -i :7865
```

**Change to different port** in `gradio_dashboard.py`

### No Data Showing

**Ensure voice assistant is running:**
```bash
ps aux | grep voice_command_client
```

**Check log files exist:**
```bash
ls -lh logs/
```

### Can't Access from Network

**Check firewall:**
```bash
sudo ufw status
```

**Verify server is listening on all interfaces:**
```bash
netstat -tulpn | grep 7865
```

Should show `0.0.0.0:7865` not `127.0.0.1:7865`

### High CPU Usage

The auto-refresh can use CPU. To reduce:

1. Increase refresh intervals in `gradio_dashboard.py`
2. Disable auto-refresh on tabs you're not using
3. Close dashboard when not needed

## Future Enhancements

### Planned Features
- [ ] Control buttons (start/stop buffer, volume control)
- [ ] Waveform visualization for recordings
- [ ] Album art display for now playing
- [ ] Command history and statistics
- [ ] JACK routing visualization
- [ ] Live audio level meters
- [ ] Dark/light theme toggle
- [ ] Export logs to file
- [ ] Search/filter logs

### Contributions Welcome!
The dashboard is designed to be easily extensible. See `gradio_dashboard.py` for the modular structure.

## Security Notes

- Dashboard runs on local network by default (0.0.0.0)
- No authentication built-in (assumes trusted network)
- Logs may contain sensitive information
- For public access, consider adding authentication
- Use SSH tunnel for remote access: `ssh -L 7865:localhost:7865 user@host`

## Performance

- **Lightweight**: ~50MB RAM, <1% CPU when idle
- **No impact**: Zero impact on voice assistant performance
- **Efficient**: Only reads log file changes, not full files
- **Responsive**: Updates feel real-time even on slower networks

## Summary

The Gradio dashboard transforms your headless voice assistant into a modern, accessible system you can monitor from anywhere on your network. Perfect for development, debugging, and day-to-day use!
