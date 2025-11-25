#!/usr/bin/env python3
"""
Timemachine Plugin

Provides retroactive audio recording using a Python-based ring buffer.
Maintains a rolling buffer of recent audio, allowing you to "go back in time"
and save what was just played/recorded.

Voice commands start/stop the recorder and trigger saves.
"""

from typing import Dict, Callable, Any, Optional
from pathlib import Path
from plugin_base import VoiceAssistantPlugin
from ring_buffer_recorder import RingBufferRecorder


class TimemachinePlugin(VoiceAssistantPlugin):
    """
    Plugin for retroactive audio recording.
    
    Records a continuous buffer of audio. When you say "save that",
    it writes the buffer to disk, capturing what was just
    played/recorded moments ago.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Configuration
        self.buffer_length = config.get('buffer_seconds', 30)  # Default 30 seconds
        self.output_dir = config.get('output_dir', str(Path.home() / 'recordings'))
        self.file_prefix = config.get('file_prefix', 'recording-')
        self.channels = config.get('channels', 2)
        self.format = config.get('format', 'WAV').upper()
        self.jack_name = config.get('jack_name', 'RingBufferRecorder')
        self.auto_connect = config.get('auto_connect', True)
        
        # Runtime state
        self.recorder: Optional[RingBufferRecorder] = None
        self.is_running = False
        self.routing_config_path = Path('jack_routing.json')
        self.remembered_connections = []  # Store [(source, dest)] tuples
        
    def get_name(self) -> str:
        return "timemachine"
    
    def get_description(self) -> str:
        return "Retroactive audio recording - save what was just played/recorded"
    
    def initialize(self) -> bool:
        """Initialize the plugin and create output directory."""
        output_path = Path(self.output_dir).expanduser()
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"[{self.get_name()}] Output directory: {output_path}")
        print(f"[{self.get_name()}] Buffer length: {self.buffer_length} seconds")
        self._load_routing_config()
        return True
    
    def cleanup(self):
        """Stop recorder if running."""
        if self.is_running:
            self._stop_recorder()
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register timemachine commands."""
        return {
            "start the buffer": self._cmd_start,
            "stop the buffer": self._cmd_stop,
            "save that": self._cmd_save,
            "save the last 30 seconds": self._cmd_save,
            "save what i just played": self._cmd_save,
            "buffer status": self._cmd_status,
        }
    
    def _load_routing_config(self) -> None:
        """Load remembered JACK routing for recorder inputs."""
        try:
            if self.routing_config_path.exists():
                import json
                with open(self.routing_config_path, 'r') as f:
                    data = json.load(f)
                connections = data.get('timemachine_inputs', [])
                if isinstance(connections, list):
                    self.remembered_connections = connections
                    if connections:
                        print(f"[{self.get_name()}] Remembered {len(connections)} JACK connection(s)")
        except Exception as e:
            print(f"[{self.get_name()}] Warning: could not load JACK routing config: {e}")
    
    def _apply_remembered_routing(self) -> None:
        """Apply remembered JACK connections to recorder after it starts."""
        print(f"[{self.get_name()}] Checking for remembered connections...")
        
        if not self.remembered_connections:
            print(f"[{self.get_name()}] No connections to restore")
            return
        
        print(f"[{self.get_name()}] Restoring {len(self.remembered_connections)} connection(s)...")
        
        import time
        import subprocess
        
        # Give recorder a moment to register ports
        time.sleep(0.5)
        
        for source, dest in self.remembered_connections:
            try:
                # Update destination port name if it references old TimeMachine client
                if ':' in dest and dest.split(':')[0] in ['TimeMachine', 'timemachine']:
                    # Map old port names to new ones
                    port_num = dest.split('_')[-1] if '_' in dest else '1'
                    dest = f"{self.jack_name}:in_{port_num}"
                
                print(f"[{self.get_name()}] Connecting {source} -> {dest}...")
                
                # Use jack_connect command
                result = subprocess.run(
                    ['jack_connect', source, dest],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print(f"[{self.get_name()}] ✅ Auto-connected {source} -> {dest}")
                else:
                    # Connection might already exist or ports not ready
                    if 'already' not in result.stderr.lower():
                        print(f"[{self.get_name()}] Could not connect {source} -> {dest}: {result.stderr.strip()}")
                    else:
                        print(f"[{self.get_name()}] ✅ {source} -> {dest} (already connected)")
            except Exception as e:
                print(f"[{self.get_name()}] Auto-connect failed for {source} -> {dest}: {e}")
    
    def _start_recorder(self) -> bool:
        """
        Start the ring buffer recorder.
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_running and self.recorder:
            print(f"[{self.get_name()}] Already running")
            return True
        
        try:
            # Create and start recorder
            self.recorder = RingBufferRecorder(
                client_name=self.jack_name,
                buffer_seconds=self.buffer_length,
                num_channels=self.channels,
                output_dir=self.output_dir,
                file_prefix=self.file_prefix,
                file_format=self.format
            )
            
            if self.recorder.start():
                self.is_running = True
                
                # Apply remembered JACK routing
                self._apply_remembered_routing()
                
                return True
            else:
                self.recorder = None
                return False
            
        except Exception as e:
            print(f"[{self.get_name()}] Error starting recorder: {e}")
            self.recorder = None
            self.is_running = False
            return False
    
    def _stop_recorder(self) -> bool:
        """
        Stop the ring buffer recorder.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_running or not self.recorder:
            print(f"[{self.get_name()}] Not running")
            return True
        
        try:
            print(f"[{self.get_name()}] Stopping recorder...")
            self.recorder.stop()
            self.recorder = None
            self.is_running = False
            print(f"[{self.get_name()}] Recorder stopped")
            return True
            
        except Exception as e:
            print(f"[{self.get_name()}] Error stopping recorder: {e}")
            return False
    
    def _trigger_save(self) -> bool:
        """
        Save the ring buffer to a file.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_running or not self.recorder:
            print(f"[{self.get_name()}] Recorder not running - starting it first...")
            if not self._start_recorder():
                return False
            # Give it a moment to initialize
            import time
            time.sleep(1)
        
        try:
            filepath = self.recorder.save_buffer()
            if filepath:
                print(f"[{self.get_name()}] Saved to {filepath}")
                return True
            else:
                print(f"[{self.get_name()}] Failed to save buffer")
                return False
            
        except Exception as e:
            print(f"[{self.get_name()}] Error saving buffer: {e}")
            return False
    
    # Command handlers
    
    def _cmd_start(self):
        """Start the recording buffer."""
        if self._start_recorder():
            return f"Recording buffer started. Say 'save that' to capture the last {self.buffer_length} seconds."
        else:
            return "Failed to start recording buffer."
    
    def _cmd_stop(self):
        """Stop the recording buffer."""
        if self._stop_recorder():
            return "Recording buffer stopped."
        else:
            return "Failed to stop recording buffer."
    
    def _cmd_save(self):
        """Save the current buffer to disk."""
        if self._trigger_save():
            return f"Saved the last {self.buffer_length} seconds."
        else:
            return "Failed to save buffer."
    
    def _cmd_status(self):
        """Report recorder status."""
        if self.is_running and self.recorder:
            status = self.recorder.get_status()
            return (f"Recording buffer is running. "
                   f"Buffer: {status['buffer_seconds']} seconds, "
                   f"Channels: {status['channels']}, "
                   f"Sample rate: {status['sample_rate']} Hz. "
                   f"Say 'save that' to capture what you just played.")
        else:
            return "Recording buffer is not running. Say 'start the buffer' to enable it."
