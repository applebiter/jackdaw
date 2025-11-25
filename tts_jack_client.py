#!/usr/bin/env python3
"""
JACK TTS Client using Piper
Polls for LLM response files and speaks them through JACK audio
"""

import jack
import numpy as np
import time
from pathlib import Path
from typing import Optional
import threading
import sys
import json
from piper import PiperVoice


class TTSJackClient:
    """JACK client that converts text to speech and plays it"""
    
    def __init__(self, config_file: str = "voice_assistant_config.json"):
        """
        Initialize the TTS JACK client
        
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.response_file = Path(config['files']['response_file'])
        self.poll_interval = config['polling']['interval_seconds']
        self.delete_after_read = config['polling'].get('delete_query_after_read', True)
        self.model_path = Path(config['voice']['synthesis']['model_path'])
        
        # Track last modification time
        self.last_mtime: Optional[float] = None
        
        # Initialize Piper voice
        self.voice = None
        self.piper_sample_rate = None
        self.init_piper()
        
        # Initialize JACK client
        self.client = jack.Client("TTSClient")
        self.client.set_process_callback(self.process_callback)
        self.client.set_shutdown_callback(self.shutdown_callback)
        
        # Register output ports (stereo)
        self.output_left = self.client.outports.register("output_L")
        self.output_right = self.client.outports.register("output_R")
        
        # Audio playback state
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_position = 0
        self.playback_lock = threading.Lock()
        self.is_playing = False
        
        # Get JACK sample rate
        self.sample_rate = self.client.samplerate
        
        print(f"TTS JACK Client initialized")
        print(f"JACK sample rate: {self.sample_rate} Hz")
        print(f"Buffer size: {self.client.blocksize} frames")
        print(f"Monitoring: {self.response_file}")
        
        # Running state
        self.running = False
        self.poll_thread = None
        
    def init_piper(self):
        """Initialize Piper voice model"""
        try:
            if not self.model_path.exists():
                print(f"❌ Error: Model file not found: {self.model_path}")
                print(f"   Download with: python -m piper.download_voices en_US-lessac-medium")
                sys.exit(1)
            
            # Load model config
            config_path = self.model_path.with_suffix('.onnx.json')
            if not config_path.exists():
                print(f"❌ Error: Model config not found: {config_path}")
                sys.exit(1)
            
            # Initialize voice
            self.voice = PiperVoice.load(str(self.model_path))
            
            # Get sample rate from config
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.piper_sample_rate = config.get('audio', {}).get('sample_rate', 22050)
            
            print(f"✅ Loaded Piper model: {self.model_path.name}")
            print(f"   Piper sample rate: {self.piper_sample_rate} Hz")
            
        except Exception as e:
            print(f"❌ Error loading Piper model: {e}")
            sys.exit(1)
            
    def process_callback(self, frames):
        """JACK process callback - outputs audio data"""
        try:
            with self.playback_lock:
                if not self.is_playing or len(self.audio_buffer) == 0:
                    # Output silence
                    self.output_left.get_array()[:] = 0
                    self.output_right.get_array()[:] = 0
                    return
                
                # Audio buffer is interleaved stereo [L, R, L, R, ...]
                # Calculate how many frames we can output
                remaining_samples = len(self.audio_buffer) - self.buffer_position
                remaining_frames = remaining_samples // 2  # 2 samples per frame (stereo)
                to_output = min(frames, remaining_frames)
                
                # Get stereo audio chunk (interleaved)
                start_sample = self.buffer_position
                end_sample = start_sample + (to_output * 2)
                chunk = self.audio_buffer[start_sample:end_sample]
                
                # De-interleave: separate left and right channels
                left_out = self.output_left.get_array()
                right_out = self.output_right.get_array()
                
                left_out[:to_output] = chunk[0::2]  # Even indices are left
                right_out[:to_output] = chunk[1::2]  # Odd indices are right
                
                # Silence the rest if we ran out of audio
                if to_output < frames:
                    left_out[to_output:] = 0
                    right_out[to_output:] = 0
                    self.is_playing = False
                    print("✅ Playback finished")
                
                self.buffer_position = end_sample
                
        except Exception as e:
            print(f"Error in process callback: {e}")
            
    def shutdown_callback(self, status, reason):
        """JACK shutdown callback"""
        print(f"JACK shutdown: {status} - {reason}")
        self.running = False
        
    def read_response_file(self) -> Optional[str]:
        """
        Read and parse the response file, extracting non-commented text
        
        Returns:
            Response text or None if file doesn't exist or is empty
        """
        if not self.response_file.exists():
            return None
            
        # Check if file has been modified since last read
        current_mtime = self.response_file.stat().st_mtime
        if self.last_mtime is not None and current_mtime <= self.last_mtime:
            return None  # File hasn't changed
            
        self.last_mtime = current_mtime
        
        try:
            with open(self.response_file, 'r') as f:
                lines = f.readlines()
            
            # Filter out commented lines (lines starting with #)
            text_lines = [line.rstrip() for line in lines 
                         if line.strip() and not line.strip().startswith('#')]
            
            if not text_lines:
                return None
                
            text = '\n'.join(text_lines)
            return text
            
        except Exception as e:
            print(f"❌ Error reading response file: {e}")
            return None
            
    def text_to_speech(self, text: str) -> Optional[np.ndarray]:
        """
        Convert text to speech using Piper TTS
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Stereo audio data as interleaved numpy array or None on error
        """
        try:
            import wave
            import subprocess
            import tempfile
            import os
            
            print(f"🎤 Generating speech...")
            print(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # Generate audio using Piper
            audio_chunks = []
            for audio_chunk in self.voice.synthesize(text):
                audio_chunks.append(audio_chunk.audio_float_array)
            
            if not audio_chunks:
                print(f"❌ No audio generated")
                return None
            
            # Concatenate all chunks (already float32)
            audio = np.concatenate(audio_chunks)
            
            print(f"   Generated: {len(audio)} samples at {self.piper_sample_rate} Hz ({len(audio)/self.piper_sample_rate:.2f}s)")
            print(f"   Audio range: [{audio.min():.3f}, {audio.max():.3f}]")
            
            # Save as mono WAV at Piper's native sample rate
            with tempfile.NamedTemporaryFile(suffix='_mono.wav', delete=False) as tmp_mono:
                mono_path = tmp_mono.name
                
            with wave.open(mono_path, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(int(self.piper_sample_rate))
                audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
                wav.writeframes(audio_int16.tobytes())
            
            print(f"   Saved mono WAV at {self.piper_sample_rate} Hz")
            
            # Use ffmpeg to convert to stereo at 44100 Hz
            with tempfile.NamedTemporaryFile(suffix='_stereo.wav', delete=False) as tmp_stereo:
                stereo_path = tmp_stereo.name
            
            print(f"   Converting to stereo @ 44100 Hz with ffmpeg...")
            result = subprocess.run(
                ['ffmpeg', '-i', mono_path, '-ac', '2', '-ar', '44100', '-y', stereo_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ ffmpeg error: {result.stderr}")
                os.unlink(mono_path)
                return None
            
            print(f"   ✅ Converted to stereo")
            
            # Read the stereo WAV file
            with wave.open(stereo_path, 'rb') as wav:
                if wav.getnchannels() != 2:
                    print(f"❌ Expected stereo, got {wav.getnchannels()} channels")
                    os.unlink(mono_path)
                    os.unlink(stereo_path)
                    return None
                if wav.getframerate() != 44100:
                    print(f"❌ Expected 44100 Hz, got {wav.getframerate()} Hz")
                    os.unlink(mono_path)
                    os.unlink(stereo_path)
                    return None
                    
                frames = wav.readframes(wav.getnframes())
                audio_stereo = np.frombuffer(frames, dtype=np.int16)
                # Convert int16 to float32 in range [-1.0, 1.0]
                audio_stereo = audio_stereo.astype(np.float32) / 32768.0
                
            # Clean up temp files
            os.unlink(mono_path)
            os.unlink(stereo_path)
            
            duration = len(audio_stereo) // 2 / 44100
            print(f"   Final audio: {len(audio_stereo)} samples ({len(audio_stereo)//2} frames), {duration:.2f}s stereo @ 44100 Hz")
            print(f"   Audio range: [{audio_stereo.min():.3f}, {audio_stereo.max():.3f}]")
            
            return audio_stereo
            
        except Exception as e:
            print(f"❌ Error in text-to-speech: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def play_audio(self, audio: np.ndarray):
        """
        Queue audio for playback
        
        Args:
            audio: Interleaved stereo audio data to play
        """
        with self.playback_lock:
            self.audio_buffer = audio
            self.buffer_position = 0
            self.is_playing = True
        
        # Audio is interleaved stereo, so divide by 2 for frame count
        num_frames = len(audio) // 2
        duration = num_frames / 44100  # Always 44100 Hz after ffmpeg conversion
        print(f"🔊 Playing audio ({duration:.1f} seconds, {num_frames} frames @ 44100Hz stereo)")
        print(f"   Audio range: min={audio.min():.3f}, max={audio.max():.3f}")
        
        # Wait for playback to finish
        while self.is_playing:
            time.sleep(0.1)
            
    def process_response(self):
        """Process a response file if available"""
        # Read response file
        text = self.read_response_file()
        
        if text is None:
            return  # No new response
            
        print(f"\n{'='*70}")
        print(f"📄 New response detected!")
        
        # Convert to speech
        audio = self.text_to_speech(text)
        
        if audio is not None:
            # Play the audio
            self.play_audio(audio)
            
            # Delete response file if configured
            if self.delete_after_read:
                try:
                    self.response_file.unlink()
                    print(f"🗑️  Response file deleted")
                except Exception as e:
                    print(f"⚠️  Could not delete response file: {e}")
        
        print(f"{'='*70}\n")
        
    def poll_loop(self):
        """Polling thread that checks for new response files"""
        print("📡 Polling thread started")
        
        while self.running:
            try:
                self.process_response()
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"❌ Error in poll loop: {e}")
                time.sleep(1)
                
        print("📡 Polling thread stopped")
        
    def start(self):
        """Start the JACK client and polling"""
        print("Starting TTS JACK client...")
        
        # Activate JACK client
        self.client.activate()
        
        # Auto-connect to system playback ports
        try:
            self.client.connect(self.output_left, "system:playback_1")
            self.client.connect(self.output_right, "system:playback_2")
            print("✅ Connected to system playback ports")
        except jack.JackError as e:
            print(f"⚠️  Could not auto-connect to system playback: {e}")
            print("   You may need to connect manually")
        
        # Start polling thread
        self.running = True
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.poll_thread.start()
        
        print("🚀 TTS JACK client is running")
        print(f"📂 Watching: {self.response_file.absolute()}")
        print(f"⏱️  Poll interval: {self.poll_interval}s")
        print("Press Ctrl+C to stop")
        
    def stop(self):
        """Stop the client"""
        print("\n🛑 Stopping TTS JACK client...")
        
        self.running = False
        
        if self.poll_thread:
            self.poll_thread.join(timeout=2.0)
            
        if self.client:
            self.client.deactivate()
            self.client.close()
            
        print("TTS JACK client stopped")
        
    def run(self):
        """Run the client (blocking)"""
        self.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted by user")
        finally:
            self.stop()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TTS JACK Client - Monitors for text files and speaks them"
    )
    parser.add_argument(
        '--config',
        default='voice_assistant_config.json',
        help='Path to configuration file (default: voice_assistant_config.json)'
    )
    
    args = parser.parse_args()
    
    client = TTSJackClient(config_file=args.config)
    client.run()


if __name__ == "__main__":
    main()
