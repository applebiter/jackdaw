# Systemd Service Setup

The voice assistant can be installed as a systemd user service to start automatically at login with the dashboard enabled.

## Installation

The installer will prompt you to set this up:

```bash
./install.sh
# Answer 'y' when asked about installing as a service
```

## Manual Installation

If you skipped the service installation during setup:

```bash
# Create user systemd directory
mkdir -p ~/.config/systemd/user

# Copy the service file
cp voice-assistant.service ~/.config/systemd/user/voice-assistant@.service

# Edit the service file to update paths if needed
nano ~/.config/systemd/user/voice-assistant@.service

# Enable lingering (allows service to run without active login)
loginctl enable-linger $USER

# Enable and start the service
systemctl --user daemon-reload
systemctl --user enable voice-assistant@$USER.service
systemctl --user start voice-assistant@$USER.service
```

## Service Management

```bash
# Start the service
systemctl --user start voice-assistant@$USER.service

# Stop the service
systemctl --user stop voice-assistant@$USER.service

# Check status
systemctl --user status voice-assistant@$USER.service

# View logs
journalctl --user -u voice-assistant@$USER.service -f

# Disable auto-start
systemctl --user disable voice-assistant@$USER.service

# Enable auto-start
systemctl --user enable voice-assistant@$USER.service
```

## What the Service Does

- Starts the voice assistant with all components
- Starts the Gradio web dashboard on port 7865
- Runs as your user (not root)
- Automatically starts at login
- Restarts on failure
- Logs to systemd journal

## Accessing the Dashboard

Once the service is running, access the dashboard at:
- Local: http://localhost:7865
- Network: http://your-hostname:7865 (if share=True in config)

## Troubleshooting

### Service won't start
```bash
# Check the logs
journalctl --user -u voice-assistant@$USER.service -n 50

# Check if JACK is running
jack_lsp

# Verify paths in service file
nano ~/.config/systemd/user/voice-assistant@.service
```

### Dashboard not accessible
```bash
# Check if gradio_dashboard.py is running
ps aux | grep gradio

# Check the service status
systemctl --user status voice-assistant@$USER.service

# View dashboard logs
tail -f logs/gradio_dashboard.log
```

### Service starts but voice assistant doesn't work
```bash
# Check component logs
tail -f logs/voice_command_client.log
tail -f logs/llm_processor.log
tail -f logs/tts_client.log

# Verify audio routing in JACK
jack_lsp -c
```

## Uninstalling the Service

```bash
# Stop and disable
systemctl --user stop voice-assistant@$USER.service
systemctl --user disable voice-assistant@$USER.service

# Remove service file
rm ~/.config/systemd/user/voice-assistant@.service

# Reload systemd
systemctl --user daemon-reload

# Disable lingering (optional)
loginctl disable-linger $USER
```

## Notes

- The service uses `start_with_dashboard.sh` to launch everything
- Type is `forking` because the script backgrounds components
- `RestartSec=10` waits 10 seconds before restarting on failure
- Service runs in user context, not system-wide
- Requires JACK audio to be available
- PipeWire users: ensure pipewire-jack is installed
