#!/usr/bin/env python3
"""
Standalone Audio Player

A separate process for playing audio that persists independently of the music browser.
This allows music to continue playing even when the browser is closed.

Usage:
    python standalone_player.py [file_paths...]
"""

import sys
import signal
import json
from pathlib import Path

# Import the audio player
import audio_jack_player


def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print("\n[StandalonePlayer] Received signal, stopping playback...")
    audio_jack_player.stop_playback()
    sys.exit(0)


def main():
    """Main entry point for standalone player"""
    if len(sys.argv) < 2:
        print("Usage: python standalone_player.py [file_paths...]")
        sys.exit(1)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get file paths from arguments
    file_paths = sys.argv[1:]
    
    # Check for shuffle mode signal file
    shuffle_file = Path(".shuffle_mode")
    if shuffle_file.exists():
        try:
            data = json.loads(shuffle_file.read_text())
            shuffle_mode = data.get("shuffle", False)
            audio_jack_player.set_shuffle_mode(shuffle_mode)
            print(f"[StandalonePlayer] Shuffle mode: {shuffle_mode}")
            shuffle_file.unlink()  # Clean up signal file
        except Exception as e:
            print(f"[StandalonePlayer] Warning: Could not read shuffle mode: {e}")
    
    print(f"[StandalonePlayer] Starting playback of {len(file_paths)} track(s)")
    
    # Stop any existing playback first
    audio_jack_player.stop_playback()
    
    # Start playback
    audio_jack_player.play_playlist(file_paths)
    
    # Keep process alive while playback thread runs
    try:
        import time
        while True:
            time.sleep(1)
            # Check if playback thread is still alive
            if audio_jack_player._playback_thread is None or not audio_jack_player._playback_thread.is_alive():
                print("[StandalonePlayer] Playback finished")
                break
    except KeyboardInterrupt:
        print("\n[StandalonePlayer] Interrupted, stopping playback...")
        audio_jack_player.stop_playback()


if __name__ == "__main__":
    main()
