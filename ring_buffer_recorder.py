#!/usr/bin/env python3
"""
Ring Buffer Recorder - A Python-based retroactive audio recorder for JACK.

This replaces the timemachine utility with a pure Python solution that:
- Continuously records audio into a ring buffer
- Saves the last N seconds when triggered
- No GUI required - fully headless operation
- Voice command integration
"""

import jack
import numpy as np
import soundfile as sf
import threading
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List


class RingBufferRecorder:
    """
    A JACK-based ring buffer recorder that continuously captures audio
    and can save the last N seconds on demand.
    """
    
    def __init__(
        self,
        client_name: str = "RingBufferRecorder",
        buffer_seconds: float = 30.0,
        num_channels: int = 2,
        output_dir: str = "~/recordings",
        file_prefix: str = "recording-",
        file_format: str = "WAV"
    ):
        """
        Initialize the ring buffer recorder.
        
        Args:
            client_name: Name for the JACK client
            buffer_seconds: How many seconds of audio to keep in the buffer
            num_channels: Number of input channels to record
            output_dir: Directory where recordings will be saved
            file_prefix: Prefix for saved file names
            file_format: Audio format (WAV, FLAC, OGG, etc.)
        """
        self.client_name = client_name
        self.buffer_seconds = buffer_seconds
        self.num_channels = num_channels
        self.output_dir = Path(output_dir).expanduser()
        self.file_prefix = file_prefix
        self.file_format = file_format.upper()
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # JACK client and ports
        self.client: Optional[jack.Client] = None
        self.input_ports: List[jack.Port] = []
        
        # Ring buffer storage
        self.ring_buffer: Optional[np.ndarray] = None
        self.buffer_frames: int = 0
        self.write_position: int = 0
        self.sample_rate: int = 0
        
        # Thread safety
        self.lock = threading.Lock()
        self.running = False
        
        # Save queue for async file writing
        self.save_queue: queue.Queue = queue.Queue()
        self.save_thread: Optional[threading.Thread] = None
        
    def start(self) -> bool:
        """
        Start the JACK client and begin recording to the ring buffer.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Create JACK client
            self.client = jack.Client(self.client_name)
            self.sample_rate = self.client.samplerate
            
            # Calculate buffer size in frames
            self.buffer_frames = int(self.buffer_seconds * self.sample_rate)
            
            # Allocate ring buffer (frames x channels)
            self.ring_buffer = np.zeros((self.buffer_frames, self.num_channels), dtype=np.float32)
            
            # Create input ports
            self.input_ports = []
            for i in range(self.num_channels):
                port = self.client.inports.register(f'in_{i+1}')
                self.input_ports.append(port)
            
            # Set process callback
            self.client.set_process_callback(self._process_callback)
            
            # Start save thread
            self.running = True
            self.save_thread = threading.Thread(target=self._save_worker, daemon=True)
            self.save_thread.start()
            
            # Activate client
            self.client.activate()
            
            print(f"[RingBuffer] Started recording")
            print(f"[RingBuffer] Client: {self.client_name}")
            print(f"[RingBuffer] Buffer: {self.buffer_seconds} seconds ({self.buffer_frames} frames)")
            print(f"[RingBuffer] Channels: {self.num_channels}")
            print(f"[RingBuffer] Sample rate: {self.sample_rate} Hz")
            print(f"[RingBuffer] Output: {self.output_dir}")
            
            return True
            
        except Exception as e:
            print(f"[RingBuffer] Error starting: {e}")
            return False
    
    def stop(self):
        """Stop the recorder and clean up resources."""
        self.running = False
        
        if self.client:
            try:
                self.client.deactivate()
                self.client.close()
            except:
                pass
            self.client = None
        
        if self.save_thread:
            self.save_thread.join(timeout=2.0)
        
        print("[RingBuffer] Stopped")
    
    def _process_callback(self, frames: int) -> None:
        """
        JACK process callback - called for each audio block.
        
        Args:
            frames: Number of frames to process
        """
        if not self.running or self.ring_buffer is None:
            return
        
        with self.lock:
            # Read from input ports
            for ch_idx, port in enumerate(self.input_ports):
                audio_data = port.get_array()
                
                # Write to ring buffer with wraparound
                space_to_end = self.buffer_frames - self.write_position
                
                if frames <= space_to_end:
                    # Simple case: all data fits before wraparound
                    self.ring_buffer[self.write_position:self.write_position + frames, ch_idx] = audio_data
                else:
                    # Wraparound case: split the write
                    self.ring_buffer[self.write_position:, ch_idx] = audio_data[:space_to_end]
                    remainder = frames - space_to_end
                    self.ring_buffer[:remainder, ch_idx] = audio_data[space_to_end:]
            
            # Update write position with wraparound
            self.write_position = (self.write_position + frames) % self.buffer_frames
    
    def save_buffer(self) -> Optional[str]:
        """
        Save the current ring buffer contents to a file.
        
        Returns:
            Path to the saved file, or None if save failed
        """
        if not self.running or self.ring_buffer is None:
            print("[RingBuffer] Cannot save: not recording")
            return None
        
        # Copy buffer data under lock
        with self.lock:
            # Read buffer in correct order (from write_position onwards, then wraparound)
            audio_data = np.vstack([
                self.ring_buffer[self.write_position:],
                self.ring_buffer[:self.write_position]
            ])
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.file_prefix}{timestamp}.{self.file_format.lower()}"
        filepath = self.output_dir / filename
        
        # Queue the save operation
        self.save_queue.put((filepath, audio_data.copy(), self.sample_rate))
        
        print(f"[RingBuffer] Queued save: {filename}")
        return str(filepath)
    
    def _save_worker(self):
        """Background thread that writes audio files asynchronously."""
        while self.running:
            try:
                # Wait for save requests with timeout
                try:
                    filepath, audio_data, sample_rate = self.save_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Write the file
                try:
                    sf.write(filepath, audio_data, sample_rate, format=self.file_format)
                    print(f"[RingBuffer] Saved: {filepath}")
                except Exception as e:
                    print(f"[RingBuffer] Error saving {filepath}: {e}")
                
                self.save_queue.task_done()
                
            except Exception as e:
                print(f"[RingBuffer] Save worker error: {e}")
    
    def get_status(self) -> dict:
        """
        Get current status information.
        
        Returns:
            Dictionary with status information
        """
        return {
            'running': self.running,
            'buffer_seconds': self.buffer_seconds,
            'channels': self.num_channels,
            'sample_rate': self.sample_rate,
            'output_dir': str(self.output_dir),
            'write_position': self.write_position,
            'buffer_frames': self.buffer_frames,
            'pending_saves': self.save_queue.qsize()
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Example standalone usage
if __name__ == "__main__":
    import sys
    
    print("Ring Buffer Recorder Test")
    print("Press Enter to save the buffer, Ctrl+C to quit")
    
    recorder = RingBufferRecorder(
        client_name="TestRecorder",
        buffer_seconds=10.0,
        num_channels=2
    )
    
    if not recorder.start():
        print("Failed to start recorder")
        sys.exit(1)
    
    try:
        while True:
            input()  # Wait for Enter key
            filepath = recorder.save_buffer()
            if filepath:
                print(f"Saved to: {filepath}")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop()
