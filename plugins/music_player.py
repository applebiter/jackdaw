#!/usr/bin/env python3
"""
Music Player Plugin

Provides voice commands for playing, controlling, and managing music playback
through the OGG JACK player.
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin
from ogg_jack_player import (
    play_random_ogg_in_directory,
    skip_to_next_track,
    stop_playback,
    pause_playback,
    resume_playback,
    is_paused,
    set_volume,
    adjust_volume,
    get_volume
)


class MusicPlayerPlugin(VoiceAssistantPlugin):
    """
    Plugin for music playback control via voice commands.
    
    Supports playing random tracks from a configured library,
    skip/next track control, stop playback, and volume adjustment.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.music_library_path = config.get('library_path', None)
    
    def get_name(self) -> str:
        return "music_player"
    
    def get_description(self) -> str:
        return "Control music playback with commands like play, stop, next track, and volume control"
    
    def initialize(self) -> bool:
        if not self.music_library_path:
            print(f"[{self.get_name()}] Warning: No library_path configured")
            return False
        print(f"[{self.get_name()}] Initialized with library: {self.music_library_path}")
        return True
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register all music-related commands."""
        return {
            "play random track": self._cmd_play_random,
            "next track": self._cmd_next_track,
            "stop playing music": self._cmd_stop_music,
            "pause music": self._cmd_pause_music,
            "resume music": self._cmd_resume_music,
            "volume up": self._cmd_volume_up,
            "volume down": self._cmd_volume_down,
            "set volume low": self._cmd_set_volume_low,
            "set volume medium": self._cmd_set_volume_medium,
            "set volume high": self._cmd_set_volume_high,
            "what's the volume": self._cmd_get_volume,
        }
    
    # Command handlers
    def _cmd_play_random(self):
        """Play a random track from the music library."""
        if self.music_library_path:
            play_random_ogg_in_directory(self.music_library_path)
        else:
            print(f"[{self.get_name()}] No music library path configured")
    
    def _cmd_next_track(self):
        """Skip to the next random track."""
        skip_to_next_track()
    
    def _cmd_stop_music(self):
        """Stop music playback."""
        stop_playback()
    
    def _cmd_volume_up(self):
        """Increase volume by 10%."""
        adjust_volume(0.1)
    
    def _cmd_volume_down(self):
        """Decrease volume by 10%."""
        adjust_volume(-0.1)
    
    def _cmd_set_volume_low(self):
        """Set volume to 30%."""
        set_volume(0.3)
    
    def _cmd_set_volume_medium(self):
        """Set volume to 60%."""
        set_volume(0.6)
    
    def _cmd_set_volume_high(self):
        """Set volume to 90%."""
        set_volume(0.9)
    
    def _cmd_get_volume(self):
        """Report current volume level."""
        vol = get_volume()
        print(f"Current volume: {int(vol * 100)}%")
    
    def _cmd_pause_music(self):
        """Pause current music playback."""
        pause_playback()
        return "Music paused."
    
    def _cmd_resume_music(self):
        """Resume paused music playback."""
        resume_playback()
        return "Music resumed."
