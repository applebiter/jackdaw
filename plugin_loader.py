#!/usr/bin/env python3
"""
Plugin Loader

Dynamically loads and manages voice assistant plugins from the plugins directory.
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any
from plugin_base import VoiceAssistantPlugin


class PluginLoader:
    """
    Loads and manages voice assistant plugins.
    
    Discovers plugins in the plugins/ directory, initializes them with config,
    and provides access to their commands.
    """
    
    def __init__(self, config: Dict[str, Any], plugins_dir: str = "plugins"):
        """
        Initialize the plugin loader.
        
        Args:
            config: Full application configuration dictionary
            plugins_dir: Directory containing plugin modules
        """
        self.config = config
        self.plugins_dir = Path(plugins_dir)
        self.plugins: List[VoiceAssistantPlugin] = []
        self.plugin_config = config.get('plugins', {})
        
        # Add plugins directory to Python path if not already there
        plugins_path = str(self.plugins_dir.absolute().parent)
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
    
    def load_all_plugins(self) -> List[VoiceAssistantPlugin]:
        """
        Discover and load all plugins from the plugins directory.
        
        Returns:
            List of successfully loaded plugin instances
        """
        if not self.plugins_dir.exists():
            print(f"[PluginLoader] Plugins directory not found: {self.plugins_dir}")
            return []
        
        # Find all Python files in plugins directory (except __init__.py)
        plugin_files = [
            f for f in self.plugins_dir.glob("*.py")
            if f.stem != "__init__" and not f.stem.startswith("_")
        ]
        
        print(f"[PluginLoader] Discovering plugins in {self.plugins_dir}...")
        
        for plugin_file in plugin_files:
            try:
                self._load_plugin_from_file(plugin_file)
            except Exception as e:
                print(f"[PluginLoader] Error loading plugin {plugin_file.stem}: {e}")
        
        print(f"[PluginLoader] Loaded {len(self.plugins)} plugins")
        return self.plugins
    
    def _load_plugin_from_file(self, plugin_file: Path):
        """
        Load a single plugin from a Python file.
        
        Args:
            plugin_file: Path to the plugin Python file
        """
        module_name = f"plugins.{plugin_file.stem}"
        
        # Import the module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            print(f"[PluginLoader] Could not import {module_name}: {e}")
            return
        
        # Find plugin classes (subclasses of VoiceAssistantPlugin)
        plugin_classes = [
            obj for name, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, VoiceAssistantPlugin) and obj != VoiceAssistantPlugin
        ]
        
        if not plugin_classes:
            print(f"[PluginLoader] No plugin class found in {module_name}")
            return
        
        # Instantiate each plugin class found
        for plugin_class in plugin_classes:
            try:
                plugin_name = plugin_class.__name__
                
                # Get plugin-specific config
                plugin_config = self._get_plugin_config(plugin_file.stem)
                
                # Check if plugin is enabled
                if not plugin_config.get('enabled', True):
                    print(f"[PluginLoader] Plugin {plugin_name} is disabled in config")
                    continue
                
                # Instantiate plugin
                plugin_instance = plugin_class(plugin_config)
                
                # Initialize plugin
                if plugin_instance.initialize():
                    self.plugins.append(plugin_instance)
                    print(f"[PluginLoader] Loaded plugin: {plugin_instance.get_name()} - {plugin_instance.get_description()}")
                else:
                    print(f"[PluginLoader] Plugin {plugin_name} initialization failed")
                    
            except Exception as e:
                print(f"[PluginLoader] Error instantiating {plugin_class.__name__}: {e}")
    
    def _get_plugin_config(self, plugin_file_stem: str) -> Dict[str, Any]:
        """
        Get configuration for a specific plugin.
        
        Looks for config under plugins.<plugin_name> in the main config file.
        Falls back to checking common config sections (e.g., 'music' for music_player).
        
        Args:
            plugin_file_stem: Plugin filename without .py extension
            
        Returns:
            Plugin configuration dictionary
        """
        # First check plugins.<plugin_name>
        plugin_config = self.plugin_config.get(plugin_file_stem, {}).copy()
        
        # For music_player, merge with the 'music' config section
        if plugin_file_stem == 'music_player':
            music_config = self.config.get('music', {})
            # Merge music config into plugin config (plugin config takes precedence)
            for key, value in music_config.items():
                if key not in plugin_config:
                    plugin_config[key] = value
        
        # Ensure 'enabled' defaults to True if not specified
        if 'enabled' not in plugin_config:
            plugin_config['enabled'] = True
        
        return plugin_config
    
    def register_all_commands(self, register_func):
        """
        Register all commands from all loaded plugins.
        
        Args:
            register_func: Function to call for each command (takes phrase, callback)
        """
        for plugin in self.plugins:
            try:
                commands = plugin.get_commands()
                for phrase, callback in commands.items():
                    register_func(phrase, callback)
            except Exception as e:
                print(f"[PluginLoader] Error registering commands from {plugin.get_name()}: {e}")
    
    def set_voice_client_for_plugins(self, voice_client):
        """
        Set the voice client reference for plugins that need it.
        
        Args:
            voice_client: VoiceCommandClient instance
        """
        for plugin in self.plugins:
            if hasattr(plugin, 'set_voice_client'):
                try:
                    plugin.set_voice_client(voice_client)
                except Exception as e:
                    print(f"[PluginLoader] Error setting voice client for {plugin.get_name()}: {e}")
    
    def cleanup_all_plugins(self):
        """Clean up all loaded plugins."""
        for plugin in self.plugins:
            try:
                plugin.cleanup()
            except Exception as e:
                print(f"[PluginLoader] Error cleaning up {plugin.get_name()}: {e}")
