#!/usr/bin/env python3
"""
LLM Recorder Plugin

Provides voice commands for capturing extended speech and sending it to the LLM
for processing through file-based IPC.
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin


class LLMRecorderPlugin(VoiceAssistantPlugin):
    """
    Plugin for recording voice input and sending to LLM.
    
    Allows users to start/stop text capture for longer form queries
    to the language model.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.voice_client = None  # Will be set by plugin loader
    
    def get_name(self) -> str:
        return "llm_recorder"
    
    def get_description(self) -> str:
        return "Record extended speech and send to LLM for processing"
    
    def set_voice_client(self, client):
        """
        Set reference to the VoiceCommandClient for text capture.
        Called by the plugin loader after initialization.
        """
        self.voice_client = client
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register LLM recording commands."""
        return {
            "start chat": self._cmd_start_recording,
            "stop chat": self._cmd_stop_recording,
        }
    
    # Command handlers
    def _cmd_start_recording(self):
        """Start capturing text for LLM query."""
        if self.voice_client:
            self.voice_client.start_text_capture()
        else:
            print(f"[{self.get_name()}] Error: No voice client available")
    
    def _cmd_stop_recording(self):
        """Stop capturing and send to LLM."""
        if self.voice_client:
            self.voice_client.stop_text_capture()
        else:
            print(f"[{self.get_name()}] Error: No voice client available")
