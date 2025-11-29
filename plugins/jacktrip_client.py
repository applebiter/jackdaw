"""
JackTrip Client Plugin

Enables anonymous, real-time audio jamming with other Jackdaw users through a
central JackTrip hub. Users can create rooms, join sessions, and collaborate
without exposing their IP addresses to each other.

Voice commands:
- "create jam room [name]"
- "list jam rooms"
- "join jam room [name]"
- "leave jam room"
- "who's in the room"
"""

import json
import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
import requests
from plugin_base import VoiceAssistantPlugin

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox
    from PySide6.QtCore import QTimer, Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


class JackTripClient(VoiceAssistantPlugin):
    """Plugin for connecting to JackTrip hub and managing jam sessions"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        # Get hub config from main config
        self.hub_config = self._load_hub_config()
        # Get channel configuration
        self.send_channels = config.get('send_channels', 2)
        self.receive_channels = config.get('receive_channels', 2)
        self.jack_client_name = config.get('jack_client_name', 'jacktrip_client')
        self.auto_connect = config.get('auto_connect', True)
        
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.current_room: Optional[Dict[str, Any]] = None
        self.jacktrip_process: Optional[subprocess.Popen] = None
        # Use the same response file as LLM for TTS
        self.tts_response_file = Path("llm_response.txt")
        self.status_widgets: List[QWidget] = []
    
    def get_name(self) -> str:
        """Return plugin name"""
        return "jacktrip_client"
    
    
    def get_description(self) -> str:
        """Return plugin description"""
        return "JackTrip Client"
    
    def get_command_examples(self) -> list:
        """Return user-friendly command examples"""
        return [
            "create jam room [name]",
            "list jam rooms",
            "join jam room [name]",
            "leave jam room",
            "who's in the room",
            "jam room status",
            "open patchbay"
        ]
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register voice commands for JackTrip functionality"""
        return {
            "create jam room": self._create_room_command,
            "list jam rooms": self._list_rooms_command,
            "join jam room": self._join_room_command,
            "leave jam room": self._leave_room_command,
            "who's in the room": self._get_room_info_command,
            "jam room status": self._get_status_command,
            "open patchbay": self._open_patchbay_command,
        }
        
    def _load_hub_config(self) -> Dict[str, Any]:
        """Load JackTrip hub configuration"""
        config_file = "voice_assistant_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                full_config = json.load(f)
                return full_config.get('jacktrip_hub', {
                    'hub_url': 'https://localhost:8000',
                    'username': 'demo',
                    'password': 'demo',
                    'verify_ssl': False  # For self-signed certificates
                })
        return {
            'hub_url': 'https://localhost:8000',
            'username': 'demo',
            'password': 'demo',
            'verify_ssl': False
        }
            'hub_url': 'http://localhost:8000',
            'username': 'demo',
            'password': 'demo'
        }
    
    def _speak_response(self, text: str):
        """Write response to file for TTS system to pick up and also print it"""
        print(f"[JackTrip] {text}")
        try:
            with open(self.tts_response_file, 'w') as f:
                f.write(text)
        except Exception as e:
            self.logger.error(f"Failed to write TTS response: {e}")
        
        # Trigger widget updates
        self._update_status_widgets()
    
    def _update_status_widgets(self):
        """Update all status widgets"""
        if not PYSIDE6_AVAILABLE:
            return
        for update_func in self.status_widgets:
            try:
                if callable(update_func):
                    update_func()
            except Exception as e:
                self.logger.error(f"Error updating status widget: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API calls"""
        if not self._authenticate():
            raise RuntimeError("Unable to authenticate with JackTrip hub")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an HTTP request with proper SSL verification settings"""
        url = f"{self.hub_config['hub_url']}{endpoint}"
        verify_ssl = self.hub_config.get('verify_ssl', False)
        
        # Add verify parameter if not already in kwargs
        if 'verify' not in kwargs:
            kwargs['verify'] = verify_ssl
        
        if method.lower() == 'get':
            return requests.get(url, **kwargs)
        elif method.lower() == 'post':
            return requests.post(url, **kwargs)
        elif method.lower() == 'put':
            return requests.put(url, **kwargs)
        elif method.lower() == 'delete':
            return requests.delete(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    def _authenticate(self) -> bool:
        """Authenticate with the hub server"""
        try:
            verify_ssl = self.hub_config.get('verify_ssl', False)
            response = requests.post(
                f"{self.hub_config['hub_url']}/auth/login",
                json={
                    "username": self.hub_config['username'],
                    "password": self.hub_config['password']
                },
                timeout=5,
                verify=verify_ssl
            )
            response.raise_for_status()
            data = response.json()
            self.auth_token = data['token']
            self.user_id = data['user_id']
            self.logger.info(f"Authenticated with JackTrip hub as {self.hub_config['username']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to authenticate with hub: {e}")
            return False
    
    def _stop_jacktrip_client(self):
        """Stop the local JackTrip client process"""
        if self.jacktrip_process:
            try:
                self.jacktrip_process.terminate()
                self.jacktrip_process.wait(timeout=5)
            except:
                try:
                    self.jacktrip_process.kill()
                except:
                    pass
            finally:
                self.jacktrip_process = None
    
    def _start_jacktrip_client(self, join_info: Dict[str, Any]) -> bool:
        """Start local JackTrip client and connect to hub"""
        # Stop any existing connection first
        self._stop_jacktrip_client()
        
        host = join_info['hub_host']
        port = join_info['jacktrip_port']
        flags = join_info.get('jacktrip_flags', [])
        
        # Build JackTrip client command
        # -C = client mode, -P = peer port (JackTrip 2.x)
        # -n = number of channels, -J = jack client name
        cmd = ['jacktrip', '-C', host, '-P', str(port)]
        
        # Add channel configuration if not default (2)
        if self.send_channels != 2 or self.receive_channels != 2:
            # JackTrip uses -n for total channels (send+receive are same)
            # Use the max of send/receive
            channels = max(self.send_channels, self.receive_channels)
            cmd.extend(['-n', str(channels)])
        
        # Add JACK client name
        if self.jack_client_name:
            cmd.extend(['-J', self.jack_client_name])
        
        # Add server-provided flags
        cmd.extend(flags)
        
        self.logger.info(f"Starting JackTrip with command: {' '.join(cmd)}")
        print(f"[JackTrip] Command: {' '.join(cmd)}")
        
        try:
            self.jacktrip_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Read initial output to catch startup errors
            import threading
            def log_output():
                for line in self.jacktrip_process.stdout:
                    print(f"[JackTrip Process] {line.strip()}")
                    if "ERROR" in line:
                        self.logger.error(f"JackTrip error: {line.strip()}")
            
            output_thread = threading.Thread(target=log_output, daemon=True)
            output_thread.start()
            self.logger.info(f"Started JackTrip client connecting to {host}:{port}")
            
            # Wait a moment for JACK ports to appear
            import time
            time.sleep(2)
            
            # Auto-connect if configured
            if self.auto_connect:
                self._setup_jack_connections()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to start JackTrip client: {e}")
            return False
    
    def _setup_jack_connections(self):
        """Set up JACK audio routing for JackTrip client"""
        try:
            import subprocess as sp
            client_name = self.jack_client_name
            
            # Connect system capture to JackTrip send ports
            for i in range(1, self.send_channels + 1):
                # Try to connect system:capture_X to client:send_X
                sp.run([
                    'jack_connect',
                    f'system:capture_{i}',
                    f'{client_name}:send_{i}'
                ], capture_output=True)
            
            # Connect JackTrip receive ports to system playback
            for i in range(1, self.receive_channels + 1):
                sp.run([
                    'jack_connect',
                    f'{client_name}:receive_{i}',
                    f'system:playback_{i}'
                ], capture_output=True)
            
            self.logger.info(f"Auto-connected JACK ports for {client_name}")
            print(f"[JackTrip] Auto-connected {self.send_channels} send and {self.receive_channels} receive channels")
        except Exception as e:
            self.logger.warning(f"Could not auto-connect JACK ports: {e}")
            print(f"[JackTrip] Warning: Auto-connect failed, you may need to route manually")
    
    # Command wrapper methods that match the registered patterns
    def _create_room_command(self, command_text: str) -> str:
        """Wrapper for create room command"""
        # Extract room name after "create jam room"
        room_name = command_text.replace("create jam room", "").strip()
        if not room_name:
            result = "Please specify a room name"
            self._speak_response(result)
            return result
        
        # Validate room name contains only letters and spaces
        if not re.match(r'^[a-zA-Z\s]+$', room_name):
            result = "Room names can only contain letters and spaces. Please try again."
            self._speak_response(result)
            return result
        
        self.logger.info(f"[JackTrip] CREATE ROOM command called with name: {room_name}")
        print(f"[JackTrip] Creating room: {room_name}")
        return self._create_room(room_name)
    
    def _list_rooms_command(self, command_text: str = "") -> str:
        """Wrapper for list rooms command"""
        self.logger.info("[JackTrip] LIST ROOMS command called")
        print("[JackTrip] Listing rooms...")
        return self._list_rooms()
    
    def _join_room_command(self, command_text: str) -> str:
        """Wrapper for join room command"""
        # Extract room name after "join jam room"
        room_name = command_text.replace("join jam room", "").replace("join room", "").strip()
        if not room_name:
            result = "Please specify a room name"
            self._speak_response(result)
            return result
        self.logger.info(f"[JackTrip] JOIN ROOM command called with name: {room_name}")
        print(f"[JackTrip] Joining room: {room_name}")
        return self._join_room_by_name(room_name)
    
    def _leave_room_command(self, command_text: str = "") -> str:
        """Wrapper for leave room command"""
        self.logger.info("[JackTrip] LEAVE ROOM command called")
        print("[JackTrip] Leaving room...")
        return self._leave_room()
    
    def _get_room_info_command(self, command_text: str = "") -> str:
        """Wrapper for room info command"""
        self.logger.info("[JackTrip] ROOM INFO command called")
        print("[JackTrip] Getting room info...")
        return self._get_room_info()
    
    def _get_status_command(self, command_text: str = "") -> str:
        """Wrapper for status command"""
        self.logger.info("[JackTrip] STATUS command called")
        print("[JackTrip] Getting status...")
        return self._get_status()
    
    def _create_room(self, room_name: str) -> str:
        """Create a new jam room"""
        try:
            response = self._make_request(
                'post',
                '/rooms',
                json={
                    "name": room_name,
                    "max_participants": 8,
                    "description": "Jackdaw jam session"
                },
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            room = response.json()
            
            # Automatically join the room we just created
            join_response = self._make_request(
                'post',
                f'/rooms/{room["id"]}/join',
                headers=self._get_headers(),
                timeout=10
            )
            join_response.raise_for_status()
            join_info = join_response.json()
            
            # Start JackTrip client
            if self._start_jacktrip_client(join_info):
                self.current_room = room
                result = f"Created and joined jam room {room_name}. JackTrip is connecting."
                self._speak_response(result)
                return result
            else:
                result = f"Created room {room_name} but failed to start JackTrip client."
                self._speak_response(result)
                return result
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to leave room: {e}")
            result = "Unable to leave jam room. Check hub connection."
            self._speak_response(result)
            return result
    
    def _list_rooms(self) -> str:
        """List all available jam rooms"""
        try:
            response = self._make_request(
                'get',
                '/rooms',
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            rooms = response.json()
            
            if not rooms:
                result = "No active jam rooms found."
                self._speak_response(result)
                return result
            
            room_list = []
            for room in rooms:
                participants = room['participant_count']
                max_participants = room['max_participants']
                status = "full" if participants >= max_participants else "open"
                room_list.append(
                    f"{room['name']}: {participants} of {max_participants} people ({status})"
                )
            
            result = "Active jam rooms: " + ", ".join(room_list)
            self._speak_response(result)
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to list rooms: {e}")
            result = "Unable to list jam rooms. Check hub connection."
            self._speak_response(result)
            return result
    
    def _join_room_by_name(self, room_name: str) -> str:
        """Join a room by name"""
        try:
            # First get list of rooms to find matching name
            response = self._make_request(
                'get',
                '/rooms',
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            rooms = response.json()
            
            # Find room by name: prefer exact match (case-insensitive), then partial match
            matching_room = None
            room_name_lower = room_name.lower()
            
            # First try exact match (case-insensitive)
            for room in rooms:
                if room['name'].lower() == room_name_lower:
                    matching_room = room
                    break
            
            # If no exact match, try partial match
            if not matching_room:
                for room in rooms:
                    if room_name_lower in room['name'].lower():
                        matching_room = room
                        break
            
            if not matching_room:
                result = f"No jam room found matching '{room_name}'."
                self._speak_response(result)
                return result
            
            # Join the room
            join_response = self._make_request(
                'post',
                f'/rooms/{matching_room["id"]}/join',
                headers=self._get_headers(),
                timeout=10
            )
            join_response.raise_for_status()
            join_info = join_response.json()
            
            # Start JackTrip client
            if self._start_jacktrip_client(join_info):
                self.current_room = matching_room
                result = f"Joined jam room {matching_room['name']}. JackTrip is connecting."
                self._speak_response(result)
                return result
            else:
                result = "Joined room but failed to start JackTrip client."
                self._speak_response(result)
                return result
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to join room by name: {e}")
            result = "Unable to join jam room. Check hub connection."
            self._speak_response(result)
            return result
    
    def _leave_room(self) -> str:
        """Leave the current room"""
        if not self.current_room:
            result = "You're not in any jam room."
            self._speak_response(result)
            return result
        
        try:
            # Stop JackTrip client
            self._stop_jacktrip_client()
            
            # Tell server we're leaving
            response = self._make_request(
                'post',
                f'/rooms/{self.current_room["id"]}/leave',
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            
            room_name = self.current_room['name']
            self.current_room = None
            result = f"Left jam room {room_name}."
            self._speak_response(result)
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to leave room: {e}")
            # Still clean up locally
            self._stop_jacktrip_client()
            self.current_room = None
            result = "Left jam room (connection error with server)."
            self._speak_response(result)
            return result
    
    def _get_room_info(self) -> str:
        """Get information about current room"""
        if not self.current_room:
            result = "You're not in any jam room."
            self._speak_response(result)
            return result
        
        try:
            response = self._make_request(
                'get',
                f'/rooms/{self.current_room["id"]}',
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            room = response.json()
            
            participant_count = len(room['participants'])
            result = (f"You're in room {room['name']} with "
                     f"{participant_count} total participant(s).")
            self._speak_response(result)
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get room info: {e}")
            result = "Unable to get room information. Check hub connection."
            self._speak_response(result)
            return result
    
    def _get_status(self) -> str:
        """Get current JackTrip status"""
        if not self.current_room:
            result = "Not connected to any jam room."
            self._speak_response(result)
            return result
        
        jacktrip_status = "connected" if (
            self.jacktrip_process and 
            self.jacktrip_process.poll() is None
        ) else "disconnected"
        
        result = (f"In room {self.current_room['name']}, "
                 f"JackTrip client is {jacktrip_status}.")
        self._speak_response(result)
        return result
    
    def create_gui_widget(self) -> Optional[QWidget]:
        """Create a widget showing JackTrip client status for the tray menu"""
        if not PYSIDE6_AVAILABLE:
            self.logger.warning("PySide6 not available, GUI widget disabled")
            return None
        
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Status group
        status_group = QGroupBox("JackTrip Client Status")
        status_layout = QVBoxLayout()
        
        # Hub connection status
        hub_label = QLabel()
        hub_label.setObjectName("hub_label")
        hub_label.setTextFormat(Qt.TextFormat.PlainText)
        status_layout.addWidget(hub_label)
        
        # Current room info
        room_label = QLabel()
        room_label.setObjectName("room_label")
        room_label.setTextFormat(Qt.TextFormat.PlainText)
        status_layout.addWidget(room_label)
        
        # JackTrip process status
        jacktrip_label = QLabel()
        jacktrip_label.setObjectName("jacktrip_label")
        jacktrip_label.setTextFormat(Qt.TextFormat.PlainText)
        status_layout.addWidget(jacktrip_label)
        
        # Participant count
        participant_label = QLabel()
        participant_label.setObjectName("participant_label")
        participant_label.setTextFormat(Qt.TextFormat.PlainText)
        status_layout.addWidget(participant_label)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Action buttons
        button_layout = QVBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Status")
        button_layout.addWidget(refresh_btn)
        
        # Leave room button (enabled only when in a room)
        leave_btn = QPushButton("Leave Room")
        leave_btn.setObjectName("leave_btn")
        leave_btn.clicked.connect(lambda: self._leave_room())
        button_layout.addWidget(leave_btn)
        
        main_layout.addLayout(button_layout)
        
        widget.setLayout(main_layout)
        
        # Update function
        def update_status():
            # Hub connection status
            if self.auth_token:
                hub_status = "🟢 Connected"
                hub_url = self.hub_config.get('hub_url', 'Unknown')
                hub_label.setText(f"Hub: {hub_status} ({hub_url})")
            else:
                hub_label.setText("Hub: 🔴 Not connected")
            
            # Room information
            if self.current_room:
                room_label.setText(f"Room: {self.current_room['name']}")
                leave_btn.setEnabled(True)
                
                # Get room info to update participant count
                try:
                    response = self._make_request(
                        'get',
                        f'/rooms/{self.current_room["id"]}',
                        headers=self._get_headers(),
                        timeout=5
                    )
                    if response.status_code == 200:
                        room = response.json()
                        participant_count = len(room['participants'])
                        participant_label.setText(f"Participants: {participant_count}")
                    else:
                        participant_label.setText("Participants: Unknown")
                except Exception:
                    participant_label.setText("Participants: Error fetching")
            else:
                room_label.setText("Room: Not in any room")
                leave_btn.setEnabled(False)
                participant_label.setText("")
            
            # JackTrip process status
            if self.jacktrip_process and self.jacktrip_process.poll() is None:
                jacktrip_label.setText("JackTrip: 🟢 Connected")
            elif self.current_room:
                jacktrip_label.setText("JackTrip: 🔴 Disconnected")
            else:
                jacktrip_label.setText("JackTrip: Inactive")
        
        # Connect refresh button
        refresh_btn.clicked.connect(update_status)
        
        # Auto-refresh timer
        timer = QTimer(widget)
        timer.timeout.connect(update_status)
        timer.start(5000)  # Update every 5 seconds
        
        # Initial update
        update_status()
        
        # Track the update function for triggering updates from command methods
        self.status_widgets.append(update_status)
        
        return widget
    
    def _open_patchbay_command(self, command_text: str) -> str:
        """Open JACK patchbay in browser"""
        try:
            if not self.current_room:
                result = "No active jam room. Join a room first."
                self._speak_response(result)
                return result
            
            room_id = self.current_room
            hub_url = self.hub_config.get('hub_url', 'http://localhost:8000')
            patchbay_url = f"{hub_url}/patchbay/{room_id}"
            
            # Open in default browser
            import webbrowser
            webbrowser.open(patchbay_url)
            
            result = f"Opening patchbay for room {room_id}"
            self._speak_response(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to open patchbay: {e}", exc_info=True)
            result = "Unable to open patchbay."
            self._speak_response(result)
            return result
    
    def shutdown(self):
        """Clean up resources on plugin shutdown"""
        if self.current_room:
            try:
                self._leave_room()
            except:
                pass
        self._stop_jacktrip_client()
