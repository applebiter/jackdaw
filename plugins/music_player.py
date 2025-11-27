#!/usr/bin/env python3
"""
Music Player Plugin

Provides voice commands for playing, controlling, and managing music playback
through the audio JACK player. Supports both directory-based random playback
and database-driven queries (artist, album, genre, etc.).
"""

from typing import Dict, Callable, Any
from plugin_base import VoiceAssistantPlugin
from audio_jack_player import (
    play_random_audio_in_directory,
    play_playlist,
    skip_to_next_track,
    stop_playback,
    pause_playback,
    resume_playback,
    is_paused,
    set_volume,
    adjust_volume,
    get_volume,
    set_shuffle_mode,
    get_shuffle_mode,
    toggle_shuffle_mode
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
    
    def get_name(self) -> str:
        return "music_player"
    
    def get_description(self) -> str:
        return "Music Player Controls"
    
    def initialize(self) -> bool:
        if not self.music_library_path:
            print(f"[{self.get_name()}] Warning: No library_path configured")
            return False
        print(f"[{self.get_name()}] Initialized with library: {self.music_library_path}")
        return True
    
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
            "set volume hi": self._cmd_set_volume_high,  # Alternative recognition
            "set volume loud": self._cmd_set_volume_loud,
            "what's the volume": self._cmd_get_volume,
            
            # Library info
            "music library stats": self._cmd_library_stats,
            
            # Playback mode
            "shuffle on": self._cmd_shuffle_on,
            "shuffle off": self._cmd_shuffle_off,
            "toggle shuffle": self._cmd_toggle_shuffle,
        }
    
    # Command handlers
    def _cmd_play_random(self):
        """Play a random track from the music library."""
        if self.music_library_path:
            play_random_audio_in_directory(self.music_library_path)
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
        """Set volume to 20%."""
        set_volume(0.2)
    
    def _cmd_set_volume_medium(self):
        """Set volume to 50%."""
        set_volume(0.5)
    
    def _cmd_set_volume_high(self):
        """Set volume to 80%."""
        set_volume(0.8)
    
    def _cmd_set_volume_loud(self):
        """Set volume to 95%."""
        set_volume(0.95)
    
    def _cmd_get_volume(self):
        """Report current volume level."""
        vol = get_volume()
        print(f"Current volume: {int(vol * 100)}%")
        return f"Current volume is {int(vol * 100)} percent"
    
    def _cmd_pause_music(self):
        """Pause current music playback."""
        pause_playback()
        return "Music paused."
    
    def _cmd_resume_music(self):
        """Resume paused music playback."""
        resume_playback()
        return "Music resumed."
    
    def _cmd_play_artist(self, text: str = ""):
        """Play tracks by a specific artist."""
        try:
            # Extract artist name from the command text
            # Text format: "play artist <artist name>"
            if "play artist" in text.lower():
                artist_name = text.lower().split("play artist", 1)[1].strip()
            else:
                artist_name = text.strip()
            
            if not artist_name:
                print(f"[{self.get_name()}] No artist name provided")
                return "No artist specified."
            
            print(f"[{self.get_name()}] Searching for artist: {artist_name}")
            tracks = search_by_artist(artist_name, limit=200)
            
            if not tracks:
                print(f"[{self.get_name()}] No tracks found for artist {artist_name}")
                return f"No tracks found for artist {artist_name}."
            
            print(f"[{self.get_name()}] Found {len(tracks)} tracks by {artist_name}")
            stop_playback()  # Stop any currently playing music
            play_playlist(tracks, library_root=self.music_library_path or "/")
            return f"Playing {len(tracks)} tracks by {artist_name}."
        except Exception as e:
            print(f"[{self.get_name()}] Error in _cmd_play_artist: {e}")
            import traceback
            traceback.print_exc()
            return f"Error playing artist: {e}"
    
    def _cmd_play_album(self, text: str = ""):
        """Play tracks from a specific album."""
        try:
            # Extract album name from the command text
            if "play album" in text.lower():
                album_name = text.lower().split("play album", 1)[1].strip()
            else:
                album_name = text.strip()
            
            if not album_name:
                print(f"[{self.get_name()}] No album name provided")
                return "No album specified."
            
            print(f"[{self.get_name()}] Searching for album: {album_name}")
            tracks = search_by_album(album_name, limit=200)
            
            if not tracks:
                print(f"[{self.get_name()}] No tracks found for album {album_name}")
                return f"No tracks found for album {album_name}."
            
            print(f"[{self.get_name()}] Found {len(tracks)} tracks from {album_name}")
            stop_playback()  # Stop any currently playing music
            play_playlist(tracks, library_root=self.music_library_path or "/")
            return f"Playing album {album_name}."
        except Exception as e:
            print(f"[{self.get_name()}] Error in _cmd_play_album: {e}")
            import traceback
            traceback.print_exc()
            return f"Error playing album: {e}"
    
    def _cmd_play_genre(self, text: str = ""):
        """Play tracks from a specific genre."""
        try:
            # Extract genre name from the command text
            if "play genre" in text.lower():
                genre_name = text.lower().split("play genre", 1)[1].strip()
            else:
                genre_name = text.strip()
            
            if not genre_name:
                print(f"[{self.get_name()}] No genre provided")
                return "No genre specified."
            
            print(f"[{self.get_name()}] Searching for genre: {genre_name}")
            tracks = search_by_genre(genre_name, limit=200)
            
            if not tracks:
                print(f"[{self.get_name()}] No tracks found for genre {genre_name}")
                return f"No tracks found for genre {genre_name}."
            
            print(f"[{self.get_name()}] Found {len(tracks)} tracks in genre {genre_name}")
            stop_playback()  # Stop any currently playing music
            play_playlist(tracks, library_root=self.music_library_path or "/")
            return f"Playing {len(tracks)} tracks from {genre_name}."
        except Exception as e:
            print(f"[{self.get_name()}] Error in _cmd_play_genre: {e}")
            import traceback
            traceback.print_exc()
            return f"Error playing genre: {e}"
    
    def _cmd_play_song(self, text: str = ""):
        """Play a specific song by title."""
        try:
            # Extract song title from the command text
            if "play song" in text.lower():
                song_title = text.lower().split("play song", 1)[1].strip()
            else:
                song_title = text.strip()
            
            if not song_title:
                print(f"[{self.get_name()}] No song title provided")
                return "No song specified."
            
            print(f"[{self.get_name()}] Searching for song: {song_title}")
            tracks = search_by_title(song_title, limit=50)
            
            if not tracks:
                print(f"[{self.get_name()}] No tracks found with title {song_title}")
                return f"No tracks found with title {song_title}."
            
            print(f"[{self.get_name()}] Found {len(tracks)} tracks matching {song_title}")
            stop_playback()  # Stop any currently playing music
            play_playlist(tracks, library_root=self.music_library_path or "/")
            return f"Playing {len(tracks)} tracks matching {song_title}."
        except Exception as e:
            print(f"[{self.get_name()}] Error in _cmd_play_song: {e}")
            import traceback
            traceback.print_exc()
            return f"Error playing song: {e}"
    
    def _cmd_play_year(self, text: str = ""):
        """Play tracks from a specific year."""
        # Extract year from the command text
        if "play year" in text.lower():
            year_text = text.lower().split("play year", 1)[1].strip()
        else:
            year_text = text.strip()
        
        if not year_text:
            print(f"[{self.get_name()}] No year provided")
            return "No year specified."
        
        # Convert spoken numbers to digits (e.g., "nineteen eighty-five" -> "1985")
        year = self._convert_year_text_to_number(year_text)
        
        print(f"[{self.get_name()}] Searching for year: {year}")
        tracks = search_by_year(year, limit=200)
        
        if not tracks:
            return f"No tracks found from year {year}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks from {year}")
        stop_playback()  # Stop any currently playing music
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks from {year}."
    
    def _cmd_play_some(self, text: str = ""):
        """Play tracks matching a general search term."""
        # Extract search term from the command text
        if "play some" in text.lower():
            search_term = text.lower().split("play some", 1)[1].strip()
        else:
            search_term = text.strip()
        
        if not search_term:
            print(f"[{self.get_name()}] No search term provided")
            return "No search term specified."
        
        print(f"[{self.get_name()}] Searching for: {search_term}")
        
        # Try genre first
        tracks = search_by_genre(search_term, limit=200)
        
        if not tracks:
            return f"No tracks found matching {search_term}."
        
        print(f"[{self.get_name()}] Found {len(tracks)} tracks matching {search_term}")
        stop_playback()  # Stop any currently playing music
        play_playlist(tracks, library_root=self.music_library_path or "/")
        return f"Playing {len(tracks)} tracks."
    
    def _cmd_library_stats(self):
        """Report music library statistics."""
        stats = get_database_stats()
        return (f"Music library has {stats['total_tracks']} tracks, "
                f"{stats['total_artists']} artists, "
                f"{stats['total_albums']} albums, "
                f"and {stats['total_genres']} genres.")
    
    def _cmd_shuffle_on(self):
        """Enable shuffle mode for playback."""
        set_shuffle_mode(True)
        return "Shuffle mode enabled."
    
    def _cmd_shuffle_off(self):
        """Disable shuffle mode (sequential playback)."""
        set_shuffle_mode(False)
        return "Sequential playback enabled."
    
    def _cmd_toggle_shuffle(self):
        """Toggle between shuffle and sequential playback."""
        shuffle = toggle_shuffle_mode()
        mode = "shuffle" if shuffle else "sequential"
        return f"Playback mode: {mode}."
    
    def _convert_year_text_to_number(self, year_text: str) -> str:
        """
        Convert spoken year text to numeric year.
        
        Examples:
            "nineteen eighty-five" -> "1985"
            "two thousand five" -> "2005"
            "twenty twenty-three" -> "2023"
            "1985" -> "1985" (already numeric)
        
        Args:
            year_text: Spoken or numeric year text
            
        Returns:
            Numeric year string
        """
        # If already numeric, return as-is
        if year_text.strip().isdigit():
            return year_text.strip()
        
        # Define number word mappings
        ones = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9
        }
        
        teens = {
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
            'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19
        }
        
        tens = {
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
            'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
        }
        
        # Clean up the text
        text = year_text.lower().strip()
        
        # Handle "two thousand" style years (2000-2099)
        if text.startswith('two thousand'):
            remainder = text.replace('two thousand', '').strip()
            if not remainder or remainder == 'and':
                return '2000'
            
            # Parse the last part
            remainder = remainder.replace('and', '').strip()
            
            # Check for teens
            if remainder in teens:
                return f"20{teens[remainder]:02d}"
            
            # Parse tens and ones
            parts = remainder.split()
            last_two = 0
            for part in parts:
                if part in tens:
                    last_two += tens[part]
                elif part in ones:
                    last_two += ones[part]
            
            return f"20{last_two:02d}"
        
        # Handle "nineteen/eighteen/seventeen/sixteen" style years (1600-1999)
        century_words = {
            'sixteen': 1600,
            'seventeen': 1700,
            'eighteen': 1800,
            'nineteen': 1900,
            'twenty': 2000
        }
        
        for word, century in century_words.items():
            if text.startswith(word):
                remainder = text.replace(word, '', 1).strip()
                
                if not remainder:
                    return str(century)
                
                # Remove "hundred" if present
                remainder = remainder.replace('hundred', '').strip()
                
                # Check for teens
                if remainder in teens:
                    return str(century + teens[remainder])
                
                # Parse tens and ones
                parts = remainder.split()
                last_two = 0
                for part in parts:
                    if part in tens:
                        last_two += tens[part]
                    elif part in ones:
                        last_two += ones[part]
                
                return str(century + last_two)
        
        # If we can't parse it, return original text
        print(f"[{self.get_name()}] Warning: Could not parse year '{year_text}', using as-is")
        return year_text
    
    def create_gui_widget(self):
        """Create a GUI widget for music player controls."""
        try:
            from PySide6.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                QLabel, QSlider, QLineEdit, QGroupBox
            )
            from PySide6.QtCore import Qt, QTimer
            from pathlib import Path
            import json
            
            widget = QWidget()
            main_layout = QVBoxLayout()
            
            # Now Playing section
            now_playing_group = QGroupBox("Now Playing")
            now_playing_layout = QVBoxLayout()
            
            title_label = QLabel("No track playing")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            title_label.setWordWrap(True)
            now_playing_layout.addWidget(title_label)
            
            artist_label = QLabel("")
            now_playing_layout.addWidget(artist_label)
            
            album_label = QLabel("")
            now_playing_layout.addWidget(album_label)
            
            now_playing_group.setLayout(now_playing_layout)
            main_layout.addWidget(now_playing_group)
            
            # Playback controls
            controls_group = QGroupBox("Playback Controls")
            controls_layout = QVBoxLayout()
            
            button_layout = QHBoxLayout()
            
            play_random_btn = QPushButton("▶ Play Random")
            play_random_btn.clicked.connect(lambda: self._cmd_play_random())
            button_layout.addWidget(play_random_btn)
            
            next_btn = QPushButton("⏭ Next")
            next_btn.clicked.connect(lambda: self._cmd_next_track())
            button_layout.addWidget(next_btn)
            
            stop_btn = QPushButton("⏹ Stop")
            stop_btn.clicked.connect(lambda: self._cmd_stop_music())
            button_layout.addWidget(stop_btn)
            
            controls_layout.addLayout(button_layout)
            controls_group.setLayout(controls_layout)
            main_layout.addWidget(controls_group)
            
            # Volume control
            volume_group = QGroupBox("Volume")
            volume_layout = QVBoxLayout()
            
            volume_slider = QSlider(Qt.Horizontal)
            volume_slider.setMinimum(0)
            volume_slider.setMaximum(100)
            volume_slider.setValue(int(get_volume() * 100))
            volume_slider.valueChanged.connect(lambda v: set_volume(v / 100.0))
            
            volume_label = QLabel(f"{volume_slider.value()}%")
            volume_slider.valueChanged.connect(lambda v: volume_label.setText(f"{v}%"))
            
            volume_layout.addWidget(volume_slider)
            volume_layout.addWidget(volume_label)
            
            volume_group.setLayout(volume_layout)
            main_layout.addWidget(volume_group)
            
            # Search section
            search_group = QGroupBox("Search & Play")
            search_layout = QVBoxLayout()
            
            artist_layout = QHBoxLayout()
            artist_input = QLineEdit()
            artist_input.setPlaceholderText("Artist name...")
            artist_btn = QPushButton("Play Artist")
            artist_btn.clicked.connect(
                lambda: self._cmd_play_artist(f"play artist {artist_input.text()}")
            )
            artist_layout.addWidget(artist_input)
            artist_layout.addWidget(artist_btn)
            search_layout.addLayout(artist_layout)
            
            album_layout = QHBoxLayout()
            album_input = QLineEdit()
            album_input.setPlaceholderText("Album name...")
            album_btn = QPushButton("Play Album")
            album_btn.clicked.connect(
                lambda: self._cmd_play_album(f"play album {album_input.text()}")
            )
            album_layout.addWidget(album_input)
            album_layout.addWidget(album_btn)
            search_layout.addLayout(album_layout)
            
            genre_layout = QHBoxLayout()
            genre_input = QLineEdit()
            genre_input.setPlaceholderText("Genre name...")
            genre_btn = QPushButton("Play Genre")
            genre_btn.clicked.connect(
                lambda: self._cmd_play_genre(f"play genre {genre_input.text()}")
            )
            genre_layout.addWidget(genre_input)
            genre_layout.addWidget(genre_btn)
            search_layout.addLayout(genre_layout)
            
            search_group.setLayout(search_layout)
            main_layout.addWidget(search_group)
            
            # Library stats
            stats_label = QLabel("Loading stats...")
            main_layout.addWidget(stats_label)
            
            try:
                stats = get_database_stats()
                stats_text = (
                    f"Library: {stats['total_tracks']} tracks, "
                    f"{stats['total_artists']} artists, "
                    f"{stats['total_albums']} albums, "
                    f"{stats['total_genres']} genres"
                )
                stats_label.setText(stats_text)
            except Exception as e:
                stats_label.setText(f"Error loading stats: {e}")
            
            widget.setLayout(main_layout)
            
            # Update now playing info periodically
            def update_now_playing():
                try:
                    status_file = Path(".now_playing.json")
                    if status_file.exists():
                        with open(status_file, 'r') as f:
                            status = json.load(f)
                        
                        if status and 'tags' in status:
                            tags = status['tags']
                            title = tags.get('title', status.get('filename', 'Unknown'))
                            artist = tags.get('artist', 'Unknown Artist')
                            album = tags.get('album', '')
                            
                            title_label.setText(title)
                            artist_label.setText(f"Artist: {artist}")
                            album_label.setText(f"Album: {album}" if album else "")
                        else:
                            title_label.setText("No track playing")
                            artist_label.setText("")
                            album_label.setText("")
                    else:
                        title_label.setText("No track playing")
                        artist_label.setText("")
                        album_label.setText("")
                except Exception:
                    pass
            
            # Timer to update now playing
            timer = QTimer(widget)
            timer.timeout.connect(update_now_playing)
            timer.start(1000)  # Update every second
            
            # Initial update
            update_now_playing()
            
            return widget
            
        except ImportError:
            print(f"[{self.get_name()}] PySide6 not available, GUI disabled")
            return None
        except Exception as e:
            print(f"[{self.get_name()}] Error creating GUI widget: {e}")
            return None
