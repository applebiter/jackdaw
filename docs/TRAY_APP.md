# Jackdaw System Tray Application

Jackdaw includes a system tray application that provides a graphical interface for controlling the voice assistant and accessing plugin features.

## Features

- **System tray icon** with status indication
- **Start/Stop** voice assistant from the tray menu
- **Now Playing** display showing current track information
- **Plugin GUI Forms** - each plugin can provide its own control panel
- **Log Viewer** for debugging
- **Status Monitoring** to ensure all components are running

## Installation

The tray application requires PySide6 and Qt platform libraries.

### Python Dependencies

PySide6 is included in `requirements.txt` and installed automatically by `./install.sh`.

### System Dependencies (Required!)

**Debian/Ubuntu:**
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
```

**Fedora:**
```bash
sudo dnf install libxcb xcb-util-cursor
```

**Why are these needed?** PySide6 (Qt) requires XCB platform libraries to display GUI elements on Linux. Without them, you'll see errors like:
```
Could not load the Qt platform plugin 'xcb'
```

The `./install.sh` script checks for these dependencies automatically.

## Starting Jackdaw

### From Applications Menu

Search for "Jackdaw" in your applications menu and click to launch.

### From Terminal

```bash
# From the project directory:
./launch_tray_app.sh

# Or manually:
source .venv/bin/activate
python voice_assistant_tray.py
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
- **📖 Reference**: Submenu containing:
  - **Voice Commands**: Comprehensive command reference
- **ℹ About**: Submenu containing:
  - **✓ System Up to Date / ⚠ Update Available**: Update status (click to check)
  - **Jackdaw Info**: Application information and credits
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

### Automatic Setup (Recommended)

The installation script automatically sets up autostart and desktop launcher:

```bash
./install.sh
```

This creates:
- Desktop launcher at `~/.local/share/applications/jackdaw.desktop`
- Autostart entry at `~/.config/autostart/jackdaw.desktop`

Jackdaw will appear in your applications menu and start automatically at login.

### Manual Setup

If you need to set it up manually:

**Desktop Launcher:**
```bash
cp jackdaw.desktop ~/.local/share/applications/
```

**Autostart:**
```bash
cp jackdaw.desktop ~/.config/autostart/
```

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
