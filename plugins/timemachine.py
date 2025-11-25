#!/usr/bin/env python3
"""
Timemachine Plugin

Controls JACK Timemachine for retroactive audio recording.
Timemachine maintains a rolling buffer of recent audio, allowing you
to "go back in time" and save what was just played/recorded.

Voice commands start/stop the timemachine daemon and trigger saves.
"""

import subprocess
import signal
import os
from typing import Dict, Callable, Any, Optional
from pathlib import Path
from plugin_base import VoiceAssistantPlugin


class TimemachinePlugin(VoiceAssistantPlugin):
    """
    Plugin for controlling JACK Timemachine.
    
    Timemachine records a continuous buffer of audio. When you say
    "save that", it writes the buffer to disk, capturing what was
    just played/recorded moments ago.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Configuration
        self.buffer_length = config.get('buffer_seconds', 30)  # Default 30 seconds
        self.output_dir = config.get('output_dir', str(Path.home() / 'recordings'))
        self.file_prefix = config.get('file_prefix', 'recording-')
        self.channels = config.get('channels', 2)
        self.format = config.get('format', 'wav')  # 'wav' or 'w64'
        self.jack_name = config.get('jack_name', 'TimeMachine')
        self.auto_connect = config.get('auto_connect', True)
        
        # Runtime state
        self.timemachine_process: Optional[subprocess.Popen] = None
        self.is_running = False
        
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
        return True
    
    def cleanup(self):
        """Stop timemachine if running."""
        if self.is_running:
            self._stop_timemachine()
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register timemachine commands."""
        return {
            "start recording buffer": self._cmd_start,
            "stop recording buffer": self._cmd_stop,
            "save that": self._cmd_save,
            "save the last 30 seconds": self._cmd_save,
            "save what i just played": self._cmd_save,
            "timemachine status": self._cmd_status,
        }
    
    def _start_timemachine(self) -> bool:
        """
        Start the timemachine process.
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_running:
            print(f"[{self.get_name()}] Already running")
            return True
        
        output_path = Path(self.output_dir).expanduser()
        
        # Build command
        cmd = [
            'timemachine',
            '-i',  # Interactive mode (console, no X11)
            '-c', str(self.channels),
            '-n', self.jack_name,
            '-t', str(self.buffer_length),
            '-p', str(output_path / self.file_prefix),
            '-f', self.format,
        ]
        
        # Optionally add auto-connect ports
        if self.auto_connect:
            # Connect to system capture ports for recording
            for i in range(1, self.channels + 1):
                cmd.append(f'system:capture_{i}')
        
        try:
            print(f"[{self.get_name()}] Starting timemachine...")
            print(f"[{self.get_name()}] Command: {' '.join(cmd)}")
            
            # Start timemachine in background
            self.timemachine_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            
            self.is_running = True
            print(f"[{self.get_name()}] Timemachine started (PID: {self.timemachine_process.pid})")
            print(f"[{self.get_name()}] Buffer: {self.buffer_length} seconds")
            print(f"[{self.get_name()}] Output: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"[{self.get_name()}] Error starting timemachine: {e}")
            self.is_running = False
            return False
    
    def _stop_timemachine(self) -> bool:
        """
        Stop the timemachine process.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_running or not self.timemachine_process:
            print(f"[{self.get_name()}] Not running")
            return True
        
        try:
            print(f"[{self.get_name()}] Stopping timemachine...")
            
            # Send SIGTERM for graceful shutdown
            self.timemachine_process.terminate()
            
            # Wait for process to end (timeout 5 seconds)
            try:
                self.timemachine_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't respond
                print(f"[{self.get_name()}] Force killing timemachine...")
                self.timemachine_process.kill()
                self.timemachine_process.wait()
            
            self.is_running = False
            self.timemachine_process = None
            print(f"[{self.get_name()}] Timemachine stopped")
            
            return True
            
        except Exception as e:
            print(f"[{self.get_name()}] Error stopping timemachine: {e}")
            return False
    
    def _trigger_save(self) -> bool:
        """
        Trigger timemachine to save the buffer.
        
        Sends SIGUSR1 to timemachine process, which causes it to
        write the buffer to a file.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_running or not self.timemachine_process:
            print(f"[{self.get_name()}] Timemachine not running - starting it first...")
            if not self._start_timemachine():
                return False
            # Give it a moment to initialize
            import time
            time.sleep(1)
        
        try:
            print(f"[{self.get_name()}] Triggering save...")
            
            # Send SIGUSR1 to trigger save
            os.kill(self.timemachine_process.pid, signal.SIGUSR1)
            
            print(f"[{self.get_name()}] Buffer saved to {self.output_dir}")
            return True
            
        except Exception as e:
            print(f"[{self.get_name()}] Error triggering save: {e}")
            return False
    
    # Command handlers
    
    def _cmd_start(self):
        """Start the timemachine recording buffer."""
        if self._start_timemachine():
            return f"Recording buffer started. Say 'save that' to capture the last {self.buffer_length} seconds."
        else:
            return "Failed to start recording buffer."
    
    def _cmd_stop(self):
        """Stop the timemachine recording buffer."""
        if self._stop_timemachine():
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
        """Report timemachine status."""
        if self.is_running:
            return (f"Recording buffer is running. "
                   f"Buffer length: {self.buffer_length} seconds. "
                   f"Say 'save that' to capture what you just played.")
        else:
            return "Recording buffer is not running. Say 'start recording buffer' to enable it."
