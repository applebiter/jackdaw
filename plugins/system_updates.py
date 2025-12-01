#!/usr/bin/env python3
"""
System Updates Plugin

Provides voice commands for checking and installing Jackdaw updates.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Callable, Any

from plugin_base import VoiceAssistantPlugin


class SystemUpdatesPlugin(VoiceAssistantPlugin):
    """Plugin for managing Jackdaw software updates"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tts_response_file = Path("llm_response.txt")
    
    def get_name(self) -> str:
        return "system_updates"
    
    def get_description(self) -> str:
        return "Jackdaw System Updates"
    
    def initialize(self) -> bool:
        """Check for updates on startup (non-blocking)"""
        try:
            # Run update check in background, don't block startup
            subprocess.Popen(
                ['python', 'check_updates.py'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            self.logger.warning(f"Could not start update check: {e}")
        return True
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register update-related voice commands"""
        return {
            "check for updates": self._check_updates_command,
            "install updates": self._install_updates_command,
            "update jackdaw": self._install_updates_command,
        }
    
    def _speak_response(self, text: str):
        """Write response for TTS system"""
        print(f"[Updates] {text}")
        try:
            with open(self.tts_response_file, 'w') as f:
                f.write(text)
        except Exception as e:
            self.logger.error(f"Failed to write TTS response: {e}")
    
    def _check_updates_command(self) -> str:
        """Check for available updates"""
        try:
            result = subprocess.run(
                ['python', 'check_updates.py'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            # Read the result message from the check
            notification_file = Path(".update_available")
            if notification_file.exists():
                message = notification_file.read_text().strip()
                response = f"Updates are available. {message}. Say 'install updates' to update now."
            else:
                response = "Jackdaw is up to date."
            
            self._speak_response(response)
            return response
            
        except subprocess.TimeoutExpired:
            response = "Update check timed out. Check your network connection."
            self._speak_response(response)
            return response
        except Exception as e:
            self.logger.error(f"Update check failed: {e}")
            response = "Update check failed."
            self._speak_response(response)
            return response
    
    def _install_updates_command(self) -> str:
        """Install available updates"""
        try:
            # First check if updates are available
            notification_file = Path(".update_available")
            if not notification_file.exists():
                response = "No updates available. Jackdaw is already up to date."
                self._speak_response(response)
                return response
            
            # Warn user
            response = "Installing updates. The voice assistant will restart automatically."
            self._speak_response(response)
            
            # Create update script that will run after we exit
            update_script = Path("perform_update.sh")
            update_script.write_text("""#!/bin/bash
# Wait for voice assistant to stop
sleep 3

# Pull updates
git pull origin main

# Reinstall dependencies in case requirements changed
source .venv/bin/activate
pip install -r requirements.txt

# Restart voice assistant
./start_voice_assistant.sh

# Clean up
rm -f perform_update.sh
""")
            update_script.chmod(0o755)
            
            # Start the update script in background
            subprocess.Popen(
                ['bash', str(update_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Trigger voice assistant shutdown
            import signal
            import os
            # This will cause the main process to exit cleanly
            os.kill(os.getppid(), signal.SIGTERM)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Update installation failed: {e}")
            response = "Update installation failed."
            self._speak_response(response)
            return response
