# System Tray Application

The voice assistant includes a system tray application that provides a graphical interface for controlling the voice assistant and accessing plugin features.

## Features

- **System tray icon** with status indication
- **Start/Stop** voice assistant from the tray menu
- **Now Playing** display showing current track information
- **Plugin GUI Forms** - each plugin can provide its own control panel
- **Log Viewer** for debugging
- **Status Monitoring** to ensure all components are running

## Installation

The tray application requires PySide6, which is included in `requirements.txt`:

```bash
# If not already installed:
.venv/bin/pip install PySide6
```

## Starting the Tray App

```bash
# From the project directory:
.venv/bin/python voice_assistant_tray.py
```

The application will:
1. Show a system tray icon
2. Load all enabled plugins
3. Create menu items for plugins with GUI forms
4. Allow you to start/stop the voice assistant

## Using the Tray App

### Main Menu

- **Status**: Shows if the voice assistant is running or stopped
- **Now Playing**: Displays current track (if music is playing)
- **▶ Start Voice Assistant**: Starts all components
- **⏹ Stop Voice Assistant**: Stops all components
- **Plugin Controls**: Each plugin with a GUI appears here
- **📋 View Logs**: Opens log viewer
- **ℹ About**: Shows application information
- **✕ Quit**: Stops voice assistant and exits

### Plugin GUI Forms

Plugins can provide custom GUI forms accessible from the tray menu. For example, the Music Player plugin provides:

- **Now Playing** section with track details
- **Playback Controls** (Play Random, Next, Stop)
- **Volume Slider** for real-time volume control
- **Search & Play** forms for artist, album, genre queries
- **Library Statistics**

## Auto-Start on Login

To have the tray application start automatically when you log in:

### GNOME/Ubuntu

1. Open "Startup Applications"
2. Click "Add"
3. Name: `Voice Assistant`
4. Command: `/home/YOUR_USERNAME/jack-voice-assistant/.venv/bin/python /home/YOUR_USERNAME/jack-voice-assistant/voice_assistant_tray.py`
5. Click "Add"

### KDE Plasma

1. System Settings → Startup and Shutdown → Autostart
2. Click "Add Application"
3. Select "Add Custom Program"
4. Command: `/home/YOUR_USERNAME/jack-voice-assistant/.venv/bin/python /home/YOUR_USERNAME/jack-voice-assistant/voice_assistant_tray.py`

### Generic Desktop Entry

Create `~/.config/autostart/voice-assistant.desktop`:

```desktop
[Desktop Entry]
Type=Application
Name=Voice Assistant
Exec=/home/YOUR_USERNAME/jack-voice-assistant/.venv/bin/python /home/YOUR_USERNAME/jack-voice-assistant/voice_assistant_tray.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

Replace `YOUR_USERNAME` with your actual username.

## Creating Plugin GUIs

Plugins can provide GUI forms by implementing the `create_gui_widget()` method. See `plugins/music_player.py` for a complete example.

### Basic Example

```python
from plugin_base import VoiceAssistantPlugin

class MyPlugin(VoiceAssistantPlugin):
    def get_name(self):
        return "my_plugin"
    
    def get_description(self):
        return "My Awesome Plugin"
    
    def get_commands(self):
        return {
            "do something": self._do_something
        }
    
    def create_gui_widget(self):
        """Create a GUI widget for this plugin."""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel("My Plugin Controls")
        layout.addWidget(label)
        
        button = QPushButton("Do Something")
        button.clicked.connect(self._do_something)
        layout.addWidget(button)
        
        widget.setLayout(layout)
        return widget
    
    def _do_something(self):
        print("Doing something!")
```

When the user clicks your plugin in the tray menu, your widget will appear in a dialog window.

## Troubleshooting

### Tray icon doesn't appear

Some desktop environments require a system tray extension:

- **GNOME**: Install [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/)
- **KDE**: System tray should work by default
- **XFCE**: System tray panel should be present

### PySide6 import errors

```bash
# Reinstall PySide6
.venv/bin/pip install --force-reinstall PySide6
```

### Voice assistant won't start

Check the logs in `logs/` directory:
- `voice_command.log` - Voice recognition issues
- `llm_processor.log` - LLM communication issues
- `tts_client.log` - Text-to-speech issues

Or use the **View Logs** option in the tray menu.

## Running Without GUI

If you prefer command-line control, you can still use:

```bash
# Start
./start_voice_assistant.sh

# Stop
./stop_voice_assistant.sh
```

The tray app and manual scripts work independently - use whichever you prefer!
