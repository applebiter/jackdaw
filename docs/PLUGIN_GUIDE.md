# Voice Assistant Plugin System

## Overview

The voice assistant uses a plugin architecture to make it easy to add new voice commands and functionality without modifying the core code.

## Plugin Structure

Plugins are Python files in the `plugins/` directory that inherit from `VoiceAssistantPlugin`.

### Basic Plugin Template

```python
#!/usr/bin/env python3
"""
My Custom Plugin

Brief description of what this plugin does.
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin


class MyCustomPlugin(VoiceAssistantPlugin):
    """
    Plugin description for documentation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize any plugin-specific attributes here
        self.my_setting = config.get('my_setting', 'default_value')
    
    def get_name(self) -> str:
        return "my_custom_plugin"
    
    def get_description(self) -> str:
        return "Short description of what this plugin does"
    
    def initialize(self) -> bool:
        """
        Optional: Perform any setup needed before commands are registered.
        Return False if initialization fails.
        """
        print(f"[{self.get_name()}] Initialized")
        return True
    
    def get_commands(self) -> Dict[str, Callable]:
        """
        Return dict of command phrases to callback functions.
        Command phrases should NOT include the wake word.
        """
        return {
            "do something": self._cmd_do_something,
            "another command": self._cmd_another,
        }
    
    def cleanup(self):
        """Optional: Clean up resources when plugin is unloaded."""
        pass
    
    # Command handler methods
    def _cmd_do_something(self):
        """Handler for 'indigo, do something' command."""
        print("Doing something!")
    
    def _cmd_another(self):
        """Handler for 'indigo, another command'."""
        print("Another command executed!")
```

## Configuration

Add plugin configuration to `voice_assistant_config.json`:

```json
{
  "plugins": {
    "my_custom_plugin": {
      "enabled": true,
      "my_setting": "custom_value"
    }
  }
}
```

## Accessing Voice Client

If your plugin needs to interact with the voice client (e.g., to stop listening), add a `set_voice_client()` method:

```python
def set_voice_client(self, client):
    """Called by plugin loader after initialization."""
    self.voice_client = client

def _cmd_stop_listening(self):
    if self.voice_client:
        self.voice_client.stop()
```

## Example Plugins

See the existing plugins for examples:

- **`music_player.py`** - Music playback and volume control
- **`llm_recorder.py`** - Text capture for LLM queries (accesses voice_client)
- **`basic_commands.py`** - Simple system commands
- **`system_updates.py`** - System update checking with tray menu integration

## Plugin Discovery

Plugins are automatically discovered and loaded from the `plugins/` directory. The loader:

1. Scans for `.py` files (except `__init__.py` and files starting with `_`)
2. Imports each module
3. Finds classes inheriting from `VoiceAssistantPlugin`
4. Instantiates them with config
5. Calls `initialize()`
6. Registers all commands from `get_commands()`

## Disabling Plugins

To disable a plugin, set `enabled: false` in config:

```json
{
  "plugins": {
    "my_custom_plugin": {
      "enabled": false
    }
  }
}
```

## Adding New Plugins

1. Create a new `.py` file in `plugins/` directory
2. Implement a class inheriting from `VoiceAssistantPlugin`
3. Implement required methods: `get_name()`, `get_description()`, `get_commands()`
4. Add any needed configuration to `voice_assistant_config.json`
5. Restart the voice assistant

No changes to core code needed!

## Plugin Loading Order

Plugins are loaded in the order they're discovered (alphabetically by filename). Commands from all plugins are registered before the voice client starts running.

## Best Practices

- **Keep plugins focused**: Each plugin should handle one area of functionality
- **Use descriptive command phrases**: Make commands natural and easy to remember
- **Handle errors gracefully**: Don't crash the entire assistant if a command fails
- **Document your commands**: Use docstrings on command handler methods
- **Test initialization**: Return `False` from `initialize()` if setup fails
- **Clean up resources**: Implement `cleanup()` if your plugin uses external resources

## Debugging

Plugin loading is logged at startup:

```
=== Loading Plugins ===
[PluginLoader] Discovering plugins in plugins...
[PluginLoader] Loaded plugin: music_player - Control music playback...
[PluginLoader] Loaded plugin: llm_recorder - Record extended speech...
[PluginLoader] Loaded plugin: basic_commands - Basic system commands...
[PluginLoader] Loaded 3 plugins

=== Registering Commands ===
Registered command: 'hello'
Registered command: 'stop listening'
...
```

If a plugin fails to load, check the error message and ensure:
- The class inherits from `VoiceAssistantPlugin`
- All required methods are implemented
- Configuration is valid
- Any dependencies are installed
