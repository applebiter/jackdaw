#!/usr/bin/env python3
"""
Music Player Plugin

Provides voice commands for playing, controlling, and managing music playback
through the OGG JACK player. Supports both directory-based random playback
and database-driven queries (artist, album, genre, etc.).
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin
from ogg_jack_player import (
    play_random_ogg_in_directory,
    play_playlist,
    skip_to_next_track,
    stop_playback,
    pause_playback,
    resume_playback,
    is_paused,
    set_volume,
    adjust_volume,
    get_volume
)
from music_query import (
    search_by_artist,
    search_by_album,
    search_by_genre,
    search_by_title,
    search_by_year,
    get_database_stats
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
        self.voice_client = None  # Will be set by set_voice_client()
    
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
    
    def set_voice_client(self, voice_client):
        """Set the voice client for accessing user input."""
        self.voice_client = voice_client
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register all music-related commands."""
        return {
            # Random playback
            "play random track": self._cmd_play_random,
            
            # Database queries
            "play artist": self._cmd_play_artist,
            "play album": self._cmd_play_album,
            "play genre": self._cmd_play_genre,
            "play song": self._cmd_play_song,
            "play year": self._cmd_play_year,
            "play some": self._cmd_play_some,
            
            # Playback control
            "next track": self._cmd_next_track,
            "stop playing music": self._cmd_stop_music,
            "pause music": self._cmd_pause_music,
            "resume music": self._cmd_resume_music,
            
            # Volume control
            "volume up": self._cmd_volume_up,
            "volume down": self._cmd_volume_down,
            "set volume low": self._cmd_set_volume_low,
            "set volume medium": self._cmd_set_volume_medium,
            "set volume high": self._cmd_set_volume_high,
            "what's the volume": self._cmd_get_volume,
            
            # Library info
            "music library stats": self._cmd_library_stats,
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
    
    def _cmd_play_artist(self):
        """Play tracks by a specific artist."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get artist name."
        
        # Get artist name from user
        artist_name = self.voice_client.get_user_input("What artist?")
        if not artist_name:
            return "No artist specified."
        
        print(f"[{self.get_name()}] Searching for artist: {artist_name}")
        tracks = search_by_artist(artist_name, limit=200)
        
        if not tracks:
            return f"No tracks found for artist {artist_name}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks by {artist_name}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks by {artist_name}."
    
    def _cmd_play_album(self):
        """Play tracks from a specific album."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get album name."
        
        album_name = self.voice_client.get_user_input("What album?")
        if not album_name:
            return "No album specified."
        
        print(f"[{self.get_name()}] Searching for album: {album_name}")
        tracks = search_by_album(album_name, limit=200)
        
        if not tracks:
            return f"No tracks found for album {album_name}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks from {album_name}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing album {album_name}."
    
    def _cmd_play_genre(self):
        """Play tracks from a specific genre."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get genre."
        
        genre_name = self.voice_client.get_user_input("What genre?")
        if not genre_name:
            return "No genre specified."
        
        print(f"[{self.get_name()}] Searching for genre: {genre_name}")
        tracks = search_by_genre(genre_name, limit=200)
        
        if not tracks:
            return f"No tracks found for genre {genre_name}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks in genre {genre_name}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks from {genre_name}."
    
    def _cmd_play_song(self):
        """Play a specific song by title."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get song title."
        
        song_title = self.voice_client.get_user_input("What song?")
        if not song_title:
            return "No song specified."
        
        print(f"[{self.get_name()}] Searching for song: {song_title}")
        tracks = search_by_title(song_title, limit=50)
        
        if not tracks:
            return f"No tracks found with title {song_title}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks matching {song_title}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks matching {song_title}."
    
    def _cmd_play_year(self):
        """Play tracks from a specific year."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get year."
        
        year = self.voice_client.get_user_input("What year?")
        if not year:
            return "No year specified."
        
        print(f"[{self.get_name()}] Searching for year: {year}")
        tracks = search_by_year(year, limit=200)
        
        if not tracks:
            return f"No tracks found from year {year}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks from {year}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks from {year}."
    
    def _cmd_play_some(self):
        """Play tracks matching a general search term."""
        if not self.voice_client:
            print(f"[{self.get_name()}] Voice client not set")
            return "Cannot get search term."
        
        search_term = self.voice_client.get_user_input("Play some what?")
        if not search_term:
            return "No search term specified."
        
        print(f"[{self.get_name()}] Searching for: {search_term}")
        
        # Try genre first
        tracks = search_by_genre(search_term, limit=200)
        
        if not tracks:
            return f"No tracks found matching {search_term}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks matching {search_term}")
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks."
    
    def _cmd_library_stats(self):
        """Report music library statistics."""
        stats = get_database_stats()
        return (f"Music library has {stats['total_tracks']} tracks, "
                f"{stats['total_artists']} artists, "
                f"{stats['total_albums']} albums, "
                f"and {stats['total_genres']} genres.")
