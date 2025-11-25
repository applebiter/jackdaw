#!/usr/bin/env python3
"""
Base class for voice assistant plugins.

Each plugin should inherit from VoiceAssistantPlugin and implement
the required methods to register commands and handle initialization.
"""

from abc import ABC, abstractmethod
from typing import Dict, Callable, Any, Optional


class VoiceAssistantPlugin(ABC):
    """
    Base class for all voice assistant plugins.
    
    Plugins should inherit from this class and implement the abstract methods.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the plugin with configuration data.
        
        Args:
            config: Dictionary containing plugin-specific configuration
        """
        self.config = config
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Return the plugin name for identification and logging.
        
        Returns:
            Plugin name as a string
        """
        pass
    
    @abstractmethod
    def get_commands(self) -> Dict[str, Callable]:
        """
        Return a dictionary mapping command phrases to callback functions.
        
        The command phrases should NOT include the wake word.
        Example: "play random track" not "[wake word], play random track"
        
        Returns:
            Dictionary where keys are command phrases and values are callbacks
        """
        pass
    
    def initialize(self) -> bool:
        """
        Perform any initialization needed before commands can be used.
        Called after plugin is loaded but before commands are registered.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        return True
    
    def cleanup(self):
        """
        Perform any cleanup needed when the plugin is unloaded or
        the application is shutting down.
        """
        pass
    
    def get_description(self) -> str:
        """
        Return a brief description of what this plugin does.
        
        Returns:
            Plugin description string
        """
        return "No description available"
