#!/usr/bin/env python3
"""
Simple OGG player over JACK.

Usage example (from another module):

    from ogg_jack_player import play_random_ogg_in_directory

    # Somewhere in a command handler:
    play_random_ogg_in_directory("/path/to/samples")
"""

import os
import random
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

import jack
import numpy as np
import soundfile as sf  # pip install soundfile

# Global state for skip/next-track control
_playback_lock = threading.Lock()
_skip_requested = threading.Event()
_stop_requested = threading.Event()
_paused = threading.Event()  # Set when paused
_current_music_dir: Optional[str] = None
_current_playlist: Optional[List[Path]] = None  # Custom playlist
_volume: float = 0.7  # Default volume (0.0 to 1.0)


class OggJackPlayer:
    """
    Play an OGG Vorbis file over JACK, resampled to JACK's sample rate.

    - Creates its own JACK client (stereo out).
    - Auto-connects to system:playback_1 and system:playback_2.
    - Uses ffmpeg to convert the OGG to a temporary WAV file
      at the JACK sample rate and 2 channels (stereo).
    - Streams the WAV into JACK in real time.
    """

    def __init__(self, client_name: str = "OggPlayer"):
        self.client = jack.Client(client_name)
        self.client.set_process_callback(self.process)
        self.client.set_shutdown_callback(self.shutdown)

        # Stereo outputs
        self.out_l = self.client.outports.register("out_L")
        self.out_r = self.client.outports.register("out_R")

        self.sample_rate = self.client.samplerate
        self.blocksize = self.client.blocksize

        # Playback state
        self._audio = np.zeros((0, 2), dtype=np.float32)  # stereo buffer
        self._position = 0
        self._playing = False

        # Thread-safe-ish flag (JACK callback is in RT thread)
        self._running = False

    def shutdown(self, status, reason):
        print(f"JACK shutdown in OggJackPlayer: {status} - {reason}")
        self._running = False

    def process(self, frames):
        """
        JACK process callback: called in RT context.
        """
        out_l = self.out_l.get_array()
        out_r = self.out_r.get_array()

        # Default to silence
        out_l[:] = 0.0
        out_r[:] = 0.0

        # Check for skip or stop request
        if _skip_requested.is_set() or _stop_requested.is_set():
            self._playing = False
            return

        # Check for pause - output silence but maintain position
        if _paused.is_set():
            return

        if not self._playing or self._audio.size == 0:
            return

        end_pos = self._position + frames
        chunk = self._audio[self._position:end_pos]

        if len(chunk) < frames:
            # Last chunk; pad remaining with silence
            if len(chunk) > 0:
                out_l[: len(chunk)] = chunk[:, 0] * _volume
                out_r[: len(chunk)] = chunk[:, 1] * _volume
            self._playing = False  # stop after this buffer
            return

        out_l[:] = chunk[:, 0] * _volume
        out_r[:] = chunk[:, 1] * _volume
        self._position = end_pos

    def _decode_ogg_to_wav(self, ogg_path: Path) -> Optional[Path]:
        """
        Use ffmpeg to decode and resample the ogg file into a stereo WAV
        at JACK's sample rate.
        """
        tmp = tempfile.NamedTemporaryFile(suffix="_ogg_resampled.wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(ogg_path),
            "-ac",
            "2",  # stereo
            "-ar",
            str(self.sample_rate),
            str(tmp_path),
        ]
        print(f"[OggJackPlayer] Running ffmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[OggJackPlayer] ffmpeg error:\n{result.stderr}")
            tmp_path.unlink(missing_ok=True)
            return None

        return tmp_path

    def load_ogg(self, ogg_path: Path) -> bool:
        """
        Convert and load an OGG file into memory for playback.
        """
        ogg_path = ogg_path.expanduser().resolve()
        if not ogg_path.exists():
            print(f"[OggJackPlayer] File not found: {ogg_path}")
            return False

        wav_path = self._decode_ogg_to_wav(ogg_path)
        if not wav_path:
            return False

        try:
            data, sr = sf.read(str(wav_path), dtype="float32")
        except Exception as e:
            print(f"[OggJackPlayer] Error reading WAV: {e}")
            wav_path.unlink(missing_ok=True)
            return False

        # Ensure shape (n_frames, 2)
        if data.ndim == 1:
            data = np.stack([data, data], axis=-1)  # mono -> stereo
        elif data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)

        if sr != self.sample_rate:
            # Should not happen if ffmpeg respected -ar, but guard anyway
            print(
                f"[OggJackPlayer] Warning: WAV SR {sr} != JACK SR {self.sample_rate}"
            )

        self._audio = data
        self._position = 0
        self._playing = True

        # Clean up temp file
        wav_path.unlink(missing_ok=True)
        return True

    def play_blocking(self, ogg_path: Path):
        """
        Load and play an OGG file, blocking until finished.
        """
        print(f"[OggJackPlayer] Preparing to play: {ogg_path}")
        if not self.load_ogg(ogg_path):
            print("[OggJackPlayer] Failed to load OGG; aborting.")
            return

        # Activate JACK client
        self.client.activate()

        # Auto-connect to system playback
        try:
            self.client.connect(self.out_l, "system:playback_1")
            self.client.connect(self.out_r, "system:playback_2")
            print("[OggJackPlayer] Connected to system:playback_1/2")
        except jack.JackError as e:
            print(f"[OggJackPlayer] Could not auto-connect: {e}")
            print("  You may need to connect manually in qjackctl/Carla.")

        self._running = True
        print("[OggJackPlayer] Starting playback...")
        import time

        # Block until playback finishes, JACK stops, skip or stop is requested
        while self._running and self._playing and not _skip_requested.is_set() and not _stop_requested.is_set():
            time.sleep(0.1)

        if _skip_requested.is_set():
            print("[OggJackPlayer] Skip requested; stopping current track.")
        elif _stop_requested.is_set():
            print("[OggJackPlayer] Stop requested; halting playback.")

        print("[OggJackPlayer] Playback finished; deactivating client.")
        self.client.deactivate()
        self.client.close()


def _collect_ogg_files(root_dir: Path) -> List[Path]:
    oggs: List[Path] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.lower().endswith(".ogg"):
                oggs.append(Path(dirpath) / fn)
    return oggs


def skip_to_next_track():
    """
    Signal the current OGG playback to stop and play the next random track
    from the same directory.

    Call this from a voice command handler, e.g.:

        from ogg_jack_player import skip_to_next_track

        def cmd_next_track():
            skip_to_next_track()

        client.register_command("next track", cmd_next_track)
    """
    global _skip_requested
    _skip_requested.set()
    print("[OggJackPlayer] Skip requested; will play next track.")


def stop_playback():
    """
    Signal the current OGG playback to stop completely without playing
    the next track.

    Call this from a voice command handler, e.g.:

        from ogg_jack_player import stop_playback

        def cmd_stop_music():
            stop_playback()

        client.register_command("stop playing music", cmd_stop_music)
    """
    global _stop_requested
    _stop_requested.set()
    print("[OggJackPlayer] Stop requested; will halt playback.")


def set_volume(level: float):
    """
    Set the playback volume level.

    Args:
        level: Volume level from 0.0 (silent) to 1.0 (full volume)
    """
    global _volume
    _volume = max(0.0, min(1.0, level))  # Clamp to [0.0, 1.0]
    print(f"[OggJackPlayer] Volume set to {int(_volume * 100)}%")


def get_volume() -> float:
    """
    Get the current playback volume level.

    Returns:
        Current volume level from 0.0 to 1.0
    """
    return _volume


def adjust_volume(delta: float):
    """
    Adjust the playback volume by a relative amount.

    Args:
        delta: Amount to change volume by (e.g., 0.1 for +10%, -0.1 for -10%)
    """
    global _volume
    _volume = max(0.0, min(1.0, _volume + delta))
    print(f"[OggJackPlayer] Volume adjusted to {int(_volume * 100)}%")


def pause_playback():
    """
    Pause the current music playback.
    
    The music will stop playing but maintain its position.
    Call resume_playback() to continue from where it paused.
    """
    global _paused
    if not _paused.is_set():
        _paused.set()
        print("[OggJackPlayer] Playback paused")


def resume_playback():
    """
    Resume paused music playback.
    
    Continues playback from where it was paused.
    """
    global _paused
    if _paused.is_set():
        _paused.clear()
        print("[OggJackPlayer] Playback resumed")


def is_paused() -> bool:
    """
    Check if playback is currently paused.
    
    Returns:
        True if paused, False otherwise
    """
    return _paused.is_set()


def _play_music_loop(root: str):
    """
    Internal function that runs in a background thread to play music.
    Continuously plays random tracks until stop is requested.
    """
    global _current_music_dir, _current_playlist
    _current_music_dir = root
    
    # Use custom playlist if set, otherwise scan directory
    if _current_playlist:
        oggs = _current_playlist
        print(f"[OggJackPlayer] Playing from custom playlist ({len(oggs)} tracks)")
    else:
        root_dir = Path(root).expanduser()
        if not root_dir.exists():
            print(f"[OggJackPlayer] Directory does not exist: {root_dir}")
            return

        oggs = _collect_ogg_files(root_dir)
        if not oggs:
            print(f"[OggJackPlayer] No .ogg files found under: {root_dir}")
            return

    while True:
        # Clear skip flag before playing next track
        _skip_requested.clear()

        # If stop was requested, halt completely
        if _stop_requested.is_set():
            print("[OggJackPlayer] Stopping playback.")
            _current_playlist = None  # Clear playlist on stop
            break

        choice = random.choice(oggs)
        print(f"[OggJackPlayer] Selected random OGG: {choice}")
        player = OggJackPlayer(client_name="OggPlayer")
        player.play_blocking(choice)

        # If stop was requested during playback, halt
        if _stop_requested.is_set():
            print("[OggJackPlayer] Stopping playback.")
            _current_playlist = None  # Clear playlist on stop
            break

        # Whether skipped or naturally finished, play next track
        print("[OggJackPlayer] Auto-playing next track...")


def play_random_ogg_in_directory(root: str):
    """
    Traverse a directory recursively, pick a random .ogg, and play it
    over JACK via a new client. Runs in a background thread so voice
    recognition continues to work.

    This is the function you can call from your voice command parser.

    Example voice handler in voice_command_client.py:

        def cmd_play_random_ogg():
            play_random_ogg_in_directory("/path/to/your/ogg/library")

        client.register_command("play random track", cmd_play_random_ogg)
    """
    global _current_playlist, _stop_requested
    _current_playlist = None  # Clear any custom playlist
    _stop_requested.clear()  # Clear stop flag for new playback
    
    # Start playback in a background thread
    thread = threading.Thread(target=_play_music_loop, args=(root,), daemon=True)
    thread.start()


def play_playlist(file_paths: List[str], library_root: str = "/"):
    """
    Play tracks from a custom playlist (list of file paths).
    Continuously plays random tracks from the playlist until stopped.
    
    Args:
        file_paths: List of absolute file paths to OGG files
        library_root: Root directory for relative path construction (default: "/")
    
    Example:
        from music_query import search_by_artist
        tracks = search_by_artist("Pink Floyd")
        play_playlist(tracks)
    """
    global _current_playlist, _stop_requested
    
    if not file_paths:
        print("[OggJackPlayer] Empty playlist provided")
        return
    
    # Convert strings to Path objects
    _current_playlist = [Path(p) for p in file_paths]
    _stop_requested.clear()  # Clear stop flag for new playback
    
    print(f"[OggJackPlayer] Starting playlist with {len(_current_playlist)} tracks")
    
    # Start playback in a background thread (use library_root as placeholder)
    thread = threading.Thread(target=_play_music_loop, args=(library_root,), daemon=True)
    thread.start()