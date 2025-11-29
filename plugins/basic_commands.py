#!/usr/bin/env python3
"""
Basic Commands Plugin

Provides simple system control and greeting commands.
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin


class BasicCommandsPlugin(VoiceAssistantPlugin):
    """
    Plugin for basic system commands like greetings and stop listening.
    
    These are simple commands that demonstrate the plugin system
    and provide essential control functions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.voice_client = None  # Will be set by plugin loader
    
    def get_name(self) -> str:
        return "basic_commands"
    
    def get_description(self) -> str:
        return "Basic system commands like hello and stop listening"
    
    def set_voice_client(self, client):
        """
        Set reference to the VoiceCommandClient for stop control.
        Called by the plugin loader after initialization.
        """
        self.voice_client = client
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register basic system commands."""
        return {
            "stop listening": self._cmd_stop_listening,
        }
    
    # Command handlers
    def _cmd_hello(self):
        """Respond to greeting."""
        print("Hello! Voice assistant is active.")
    
    def _cmd_stop_listening(self):
        """Stop the voice assistant."""
        print("Stopping voice assistant...")
        if self.voice_client:
            self.voice_client.stop()
        else:
            print(f"[{self.get_name()}] Error: No voice client available")
