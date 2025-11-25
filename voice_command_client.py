#!/usr/bin/env python3
"""
JACK Voice Command Client using Vosk
Continuously listens to JACK audio and processes voice commands

Plugins can be added to the plugins/ directory to extend functionality.
"""

import jack
import numpy as np
import vosk
import json
import queue
import sys
from typing import Callable, Dict, Optional
import threading
from pathlib import Path
import time
import subprocess

from plugin_loader import PluginLoader

# Reduce Vosk logging verbosity to prevent log file growth
vosk.SetLogLevel(-1)  # -1 = only errors, 0 = warnings+errors


class VoiceCommandClient:
    """JACK client that performs continuous speech recognition using Vosk"""
    
    def __init__(self, config_file: str = "voice_assistant_config.json"):
        """
        Initialize the voice command client
        
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.sample_rate = config['voice']['recognition']['sample_rate']
        model_path = config['voice']['recognition']['model_path']
        self.query_file = Path(config['files']['query_file'])
        self.wake_word = config['voice']['recognition'].get('wake_word', '').lower()
        self.log_level = config.get('logging', {}).get('log_level', 'INFO').upper()
        self.audio_queue = queue.Queue()

        # Optional music library path for playback commands
        self.music_library_path = config.get('music', {}).get('library_path')
        
        # Voice Activity Detection (VAD) settings
        self.vad_enabled = config['voice']['recognition'].get('vad_enabled', True)
        self.vad_energy_threshold = config['voice']['recognition'].get('vad_energy_threshold', 0.01)
        self.vad_speech_timeout = config['voice']['recognition'].get('vad_speech_timeout', 1.5)
        self.vad_is_speech = False
        self.vad_last_speech_time = 0
        self.vad_energy_history = []
        
        # Initialize Vosk model and recognizer
        try:
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            print(f"Please download a model from https://alphacephei.com/vosk/models")
            print(f"and extract it to '{model_path}' directory")
            sys.exit(1)
        
        # Command registry
        self.commands: Dict[str, Callable] = {}
        
        # Text capture state
        self.capturing = False
        self.captured_text = []
        self.capture_lock = threading.Lock()
        
        # Initialize JACK client
        self.client = jack.Client("VoiceCommandClient")
        self.client.set_process_callback(self.process_callback)
        self.client.set_shutdown_callback(self.shutdown_callback)
        
        # Register input port
        self.input_port = self.client.inports.register("input")

        # Remembered JACK routing (optional)
        self.routing_config_path = Path("jack_routing.json")
        self.voice_input_source: Optional[str] = None
        
        # Get JACK sample rate and setup resampling if needed
        self.jack_sample_rate = self.client.samplerate
        self.buffer = np.array([], dtype=np.float32)
        
        # Calculate resampling ratio
        self.resample_ratio = self.sample_rate / self.jack_sample_rate
        
        print(f"JACK sample rate: {self.jack_sample_rate} Hz")
        print(f"Vosk sample rate: {self.sample_rate} Hz")
        print(f"Resampling ratio: {self.resample_ratio}")
        
        if self.vad_enabled:
            print(f"VAD enabled - energy threshold: {self.vad_energy_threshold}")
        else:
            print("VAD disabled - continuous processing")
        
        # Recognition thread
        self.running = False
        self.recognition_thread = None

        # Load any remembered routing
        self.load_routing_config()
        
    def register_command(self, phrase: str, callback: Callable):
        """
        Register a voice command with its callback function
        
        Args:
            phrase: The phrase to listen for (case-insensitive)
            callback: Function to call when phrase is detected
        """
        self.commands[phrase.lower()] = callback
        print(f"Registered command: '{phrase}'")

    def load_routing_config(self) -> None:
        """Load remembered JACK routing from jack_routing.json if it exists."""
        try:
            if self.routing_config_path.exists():
                with open(self.routing_config_path, "r") as f:
                    data = json.load(f)
                src = data.get("voice_input_source")
                if isinstance(src, str) and src.strip():
                    self.voice_input_source = src.strip()
                    print(f"Remembered JACK source for input: {self.voice_input_source}")
        except Exception as e:
            print(f"Warning: could not load JACK routing config: {e}")

    def save_routing_config(self, source_port: str) -> None:
        """Save the JACK source connected to VoiceCommandClient:input."""
        try:
            data = {"voice_input_source": source_port}
            with open(self.routing_config_path, "w") as f:
                json.dump(data, f, indent=2)
            self.voice_input_source = source_port
            print(f"Saved JACK routing: {source_port} -> VoiceCommandClient:input")
        except Exception as e:
            print(f"Warning: could not save JACK routing config: {e}")

    def auto_connect_input(self) -> None:
        """Attempt to auto-connect the remembered JACK source to our input port."""
        if not self.voice_input_source:
            return
        try:
            ports = self.client.get_ports(self.voice_input_source)
            if not ports:
                print(f"Auto-connect: source port not found: {self.voice_input_source}")
                return
            self.client.connect(self.voice_input_source, self.input_port)
            print(f"✅ Auto-connected {self.voice_input_source} -> {self.input_port.name}")
        except jack.JackError as e:
            print(f"Auto-connect failed: {e}")
        
    def process_callback(self, frames):
        """JACK process callback - captures audio data"""
        try:
            # Get audio from input port
            audio = self.input_port.get_array()
            
            # Queue audio for processing
            self.audio_queue.put(audio.copy())
            
        except Exception as e:
            print(f"Error in process callback: {e}")
        
    def shutdown_callback(self, status, reason):
        """JACK shutdown callback"""
        print(f"JACK shutdown: {status} - {reason}")
        self.running = False
        
    def resample_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Simple resampling using linear interpolation
        
        Args:
            audio: Input audio at JACK sample rate
            
        Returns:
            Resampled audio at Vosk sample rate
        """
        if self.jack_sample_rate == self.sample_rate:
            return audio
            
        # Concatenate with buffer from previous call
        audio = np.concatenate([self.buffer, audio])
        
        # Calculate output length
        output_length = int(len(audio) * self.resample_ratio)
        
        # Create interpolation indices
        indices = np.linspace(0, len(audio) - 1, output_length)
        
        # Interpolate
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        
        # Keep remainder for next iteration
        samples_used = int(output_length / self.resample_ratio)
        self.buffer = audio[samples_used:]
        
        return resampled.astype(np.float32)
    
    def calculate_energy(self, audio: np.ndarray) -> float:
        """Calculate RMS energy of audio signal"""
        return np.sqrt(np.mean(audio ** 2))
    
    def check_voice_activity(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech using energy-based VAD"""
        if not self.vad_enabled:
            return True  # Always process if VAD is disabled
        
        energy = self.calculate_energy(audio)
        current_time = time.time()
        
        # Update energy history (keep last 10 frames for smoothing)
        self.vad_energy_history.append(energy)
        if len(self.vad_energy_history) > 10:
            self.vad_energy_history.pop(0)
        
        # Use average energy for more stable detection
        avg_energy = np.mean(self.vad_energy_history)
        
        # Check if energy exceeds threshold
        if avg_energy > self.vad_energy_threshold:
            self.vad_is_speech = True
            self.vad_last_speech_time = current_time
            return True
        
        # Continue processing for a timeout period after speech stops
        if current_time - self.vad_last_speech_time < self.vad_speech_timeout:
            return True
        
        # No speech detected
        if self.vad_is_speech:
            # Transition from speech to silence
            self.vad_is_speech = False
            print("[VAD: Silence detected]", end='\r')
        
        return False
        
    def process_recognition(self):
        """Recognition thread - processes audio and detects commands"""
        print("Recognition thread started")
        
        while self.running:
            try:
                # Get audio from queue (with timeout to allow checking self.running)
                audio = self.audio_queue.get(timeout=0.1)
                
                # Resample if needed
                audio_resampled = self.resample_audio(audio)
                
                # Check for voice activity
                if not self.check_voice_activity(audio_resampled):
                    # Skip processing if no speech detected
                    continue

                # Convert to 16-bit PCM for Vosk
                audio_clipped = np.clip(audio_resampled, -1.0, 1.0)
                audio_int16 = (audio_clipped * 32767).astype(np.int16)

                # Feed to recognizer
                if self.recognizer.AcceptWaveform(audio_int16.tobytes()):
                    # Final result (end of utterance)
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '')
                    
                    if text:
                        print(f"Recognized: {text}")
                        self.check_commands(text)
                else:
                    # Partial result
                    result = json.loads(self.recognizer.PartialResult())
                    partial = result.get('partial', '')
                    
                    if partial:
                        # Show partial results only in DEBUG mode
                        if self.log_level == 'DEBUG':
                            print(f"Partial: {partial}", end='\r')
                        
                        # Check if "stop recording" is in partial results
                        if self.capturing and 'stop recording' in partial.lower():
                            # Trigger stop recording immediately
                            self.check_commands('stop recording')
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in recognition thread: {e}")
                
        print("Recognition thread stopped")
        
    def check_commands(self, text: str):
        """
        Check if recognized text matches any registered commands
        
        Args:
            text: Recognized text
        """
        text_lower = text.lower()
        
        # If wake word is configured, check if text starts with it
        if self.wake_word:
            if not text_lower.startswith(self.wake_word):
                # No wake word detected - ignore this text
                # But still capture it if we're already capturing
                with self.capture_lock:
                    if self.capturing and text.strip():
                        self.captured_text.append(text)
                        print(f"[Captured: {text}]")
                return
            
            # Remove wake word from text for command matching
            text_lower = text_lower[len(self.wake_word):].strip()
        
        # Check for command matches - sort by length descending to match longer phrases first
        sorted_commands = sorted(self.commands.items(), key=lambda x: len(x[0]), reverse=True)
        for phrase, callback in sorted_commands:
            if phrase in text_lower:
                print(f"\n>>> Command detected: '{phrase}'")
                try:
                    # Pass the full text (after wake word) to callback
                    callback(text_lower)
                except TypeError:
                    # Fallback for callbacks that don't accept parameters
                    callback()
                except Exception as e:
                    print(f"Error executing command callback: {e}")
        
        # If capturing, add text to buffer (unless it's a command)
        with self.capture_lock:
            if self.capturing and text.strip():
                # Don't capture the command phrases themselves
                is_command = any(phrase in text_lower for phrase in self.commands.keys())
                if not is_command:
                    self.captured_text.append(text)
                    print(f"[Captured: {text}]")
                    
    def start(self):
        """Start the JACK client and recognition"""
        print("Starting voice command client...")
        
        # Activate JACK client
        self.client.activate()

        # Try to auto-connect previously remembered input source
        self.auto_connect_input()
        
        # Start recognition thread
        self.running = True
        self.recognition_thread = threading.Thread(target=self.process_recognition)
        self.recognition_thread.start()
        
        print("Voice command client is running")
        if self.wake_word:
            print(f"Wake word: '{self.wake_word}'")
            print(f"Available commands (say '{self.wake_word}' first):")
        else:
            print("Available commands:")
        for phrase in self.commands.keys():
            print(f"  - {phrase}")
        print("\nConnect an audio source to the 'VoiceCommandClient:input' port")
        print("Press Ctrl+C to stop")
        
    def stop(self):
        """Stop the client"""
        print("\nStopping voice command client...")
        
        self.running = False
        
        if self.recognition_thread:
            self.recognition_thread.join(timeout=2.0)
            
        if self.client:
            self.client.deactivate()
            self.client.close()
            
        print("Voice command client stopped")
        
    def start_text_capture(self):
        """Start capturing recognized text"""
        with self.capture_lock:
            self.capturing = True
            self.captured_text = []
        print("\n📝 Text capture started - speak your query")
        
    def stop_text_capture(self, output_file: str = None):
        """Stop capturing text and write to file"""
        with self.capture_lock:
            self.capturing = False
            
            if not self.captured_text:
                print("\n⚠️  No text was captured")
                return
            
            # Join all captured text
            full_text = " ".join(self.captured_text)
            
            # Use configured query file if not specified
            if output_file is None:
                output_path = self.query_file
            else:
                output_path = Path(output_file)
            try:
                with open(output_path, 'w') as f:
                    f.write(f"# Query captured at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(full_text + "\n")
                
                print(f"\n✅ Captured text saved to: {output_path.absolute()}")
                print(f"Query: {full_text}")
                
                # Clear buffer
                self.captured_text = []
                
            except Exception as e:
                print(f"\n❌ Error writing to file: {e}")
    
    def run(self):
        """Run the client (blocking)"""
        self.start()
        
        try:
            # Keep main thread alive
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.stop()


def main():
    """Main entry point for the voice command client with plugin support"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Voice Command Client - Listens for voice commands on JACK"
    )
    parser.add_argument(
        '--config',
        default='voice_assistant_config.json',
        help='Path to configuration file (default: voice_assistant_config.json)'
    )
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Create client
    client = VoiceCommandClient(config_file=args.config)
    
    # Load plugins
    print("\n=== Loading Plugins ===")
    plugin_loader = PluginLoader(config)
    plugins = plugin_loader.load_all_plugins()
    
    # Give plugins access to voice client if they need it
    plugin_loader.set_voice_client_for_plugins(client)
    
    # Register all commands from plugins
    print("\n=== Registering Commands ===")
    plugin_loader.register_all_commands(client.register_command)
    print()
    
    # Run the client
    try:
        client.run()
    finally:
        # Clean up plugins on shutdown
        print("\n=== Cleaning Up Plugins ===")
        plugin_loader.cleanup_all_plugins()


if __name__ == "__main__":
    main()
