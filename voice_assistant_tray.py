#!/usr/bin/env python3
"""
Voice Assistant System Tray Application

Provides a system tray icon with controls for the voice assistant.
Dynamically loads plugin GUI forms and integrates them into the tray menu.
"""

import sys
import json
import subprocess
import threading
import signal
import atexit
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget,
    QComboBox, QMessageBox
)
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtGui import QIcon, QAction, QPixmap

from plugin_loader import PluginLoader
from music_scanner_widget import MusicScannerWidget
from command_aliases_editor import CommandAliasesEditor


class VoiceAssistantTray(QObject):
    """
    System tray application for the voice assistant.
    Manages voice assistant processes and provides GUI access to plugins.
    """
    
    # Signals for thread-safe updates
    status_changed = Signal(str)
    track_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup_on_exit)
        
        # Load configuration
        self.config_file = Path("voice_assistant_config.json")
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
        
        # Check for and stop any already-running processes
        self._cleanup_existing_processes()
        self._check_for_duplicate_tray()
        
        # Voice assistant processes
        self.voice_process: Optional[subprocess.Popen] = None
        self.llm_process: Optional[subprocess.Popen] = None
        self.tts_process: Optional[subprocess.Popen] = None
        self.processes_running = False
        
        # Track browser process for cleanup
        self.browser_process: Optional[subprocess.Popen] = None
        
        # Load plugins
        self.plugin_loader = PluginLoader(self.config)
        self.plugins = self.plugin_loader.load_all_plugins()
        self.llm_recorder_plugin = None  # Will be set during menu setup
        self.jacktrip_plugin = None  # Will be set during menu setup
        
        # Track all opened windows for cleanup on exit
        self.opened_windows: List[QWidget] = []
        
        # Create tray icon
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
        
        # Make Ctrl+C work
        self.app.setQuitOnLastWindowClosed(False)
        
        self.tray_icon = QSystemTrayIcon()
        self.setup_tray_icon()
        
        # Status monitoring timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # Update every 2 seconds
        
        # Watchdog timer to keep app alive
        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self._watchdog_tick)
        self.watchdog_timer.start(5000)  # Check every 5 seconds
        
        # Connect signals
        self.status_changed.connect(self.on_status_changed)
        self.track_changed.connect(self.on_track_changed)
        
        # Check if processes are already running
        self.detect_running_processes()
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for clean shutdown"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.quit_application()
    
    def _cleanup_on_exit(self):
        """Cleanup handler for atexit"""
        try:
            if self.processes_running:
                self.stop_voice_assistant()
        except:
            pass
    
    def _watchdog_tick(self):
        """Periodic watchdog check to ensure tray is still functional"""
        try:
            # Write heartbeat file
            heartbeat_file = Path(".tray_heartbeat")
            from datetime import datetime
            heartbeat_file.write_text(datetime.now().isoformat())
            
            # Verify we can still interact with Qt objects
            if self.tray_icon and self.tray_icon.isVisible():
                pass  # All good
            else:
                print("Warning: Tray icon is not visible")
        except Exception as e:
            print(f"Watchdog error: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_tray_icon(self):
        """Set up the system tray icon and menu."""
        # Create icon
        icon = self.create_icon(is_active=False)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Jackdaw (Stopped)")
        
        # Create context menu
        menu = QMenu()
        
        # Status section
        self.status_action = QAction("Status: Stopped", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        self.track_action = QAction("No track playing", menu)
        self.track_action.setEnabled(False)
        menu.addAction(self.track_action)
        
        menu.addSeparator()
        
        # Control actions
        self.start_action = QAction("▶ Start Jackdaw", menu)
        self.start_action.triggered.connect(self.start_voice_assistant)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("⏹ Stop Jackdaw", menu)
        self.stop_action.triggered.connect(self.stop_voice_assistant)
        self.stop_action.setEnabled(False)
        menu.addAction(self.stop_action)
        
        menu.addSeparator()
        
        # Hub connection status (read-only, shows connection state)
        self.hub_status_action = QAction("○ Hub Connection", menu)
        self.hub_status_action.setEnabled(False)  # Not clickable, just shows status
        menu.addAction(self.hub_status_action)
        
        menu.addSeparator()
        
        # Music submenu
        music_menu = menu.addMenu("🎵 Music")
        
        # Music browser action
        music_browser_action = QAction("📂 Library Browser", music_menu)
        music_browser_action.triggered.connect(self.launch_music_browser)
        music_menu.addAction(music_browser_action)
        
        # Scan library action
        scan_library_action = QAction("🔍 Scan Library", music_menu)
        scan_library_action.triggered.connect(self.launch_music_scanner)
        music_menu.addAction(scan_library_action)
        
        menu.addSeparator()
        
        # AI Chat submenu - open the widget instead of inline controls
        chat_action = QAction("🤖 AI Chat", menu)
        chat_action.triggered.connect(self.show_chat_widget)
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        # Plugin GUI forms (excluding llm_recorder, basic_commands, music_player, and icecast_streamer)
        self.plugin_menu_items = {}
        for plugin in self.plugins:
            # Skip llm_recorder plugin since we integrated it as AI Chat menu item
            if plugin.get_name() == 'llm_recorder':
                self.llm_recorder_plugin = plugin  # Store reference for widget
                continue
            
            # Skip plugins that don't need menu items (controlled via voice or other menus)
            if plugin.get_name() in ['basic_commands', 'music_player', 'icecast_streamer', 'buffer', 'system_updates']:
                continue
            
            # Special handling for JackTrip - just show status, not a widget
            if plugin.get_name() == 'jacktrip_client':
                self.jacktrip_plugin = plugin
                # Will add status menu item below
                continue
                
            if hasattr(plugin, 'create_gui_widget') and callable(getattr(plugin, 'create_gui_widget')):
                plugin_name = plugin.get_name()
                icon = "🔧"
                action = QAction(f"{icon} {plugin.get_description()}", menu)
                action.triggered.connect(lambda checked=False, p=plugin: self.show_plugin_gui(p))
                menu.addAction(action)
                self.plugin_menu_items[plugin_name] = action
        
        if self.plugin_menu_items:
            menu.addSeparator()
        
        # Tools submenu
        tools_menu = menu.addMenu("🔧 Tools")
        
        # Command aliases editor
        aliases_action = QAction("🗣️ Edit Command Aliases", tools_menu)
        aliases_action.triggered.connect(self.show_aliases_editor)
        tools_menu.addAction(aliases_action)
        
        tools_menu.addSeparator()
        
        # Remember JACK routing action
        remember_routing_action = QAction("💾 Save JACK Connections", tools_menu)
        remember_routing_action.triggered.connect(self.remember_jack_routing)
        tools_menu.addAction(remember_routing_action)
        
        # View logs action
        view_logs_action = QAction("📋 View Logs", menu)
        view_logs_action.triggered.connect(self.show_logs_viewer)
        menu.addAction(view_logs_action)
        
        menu.addSeparator()
        
        # Reference submenu
        reference_menu = menu.addMenu("📖 Reference")
        
        # Voice commands reference
        commands_action = QAction("🎤 Voice Commands", reference_menu)
        commands_action.triggered.connect(self.show_voice_commands_reference)
        reference_menu.addAction(commands_action)
        
        menu.addSeparator()
        
        # About submenu
        about_menu = menu.addMenu("About")
        
        # Update check action
        self.check_updates_action = QAction("System Up to Date", about_menu)
        self.check_updates_action.triggered.connect(self.check_for_updates)
        about_menu.addAction(self.check_updates_action)
        
        about_menu.addSeparator()
        
        # Plugin descriptions submenu
        plugins_menu = about_menu.addMenu("🔌 Plugins")
        for plugin in self.plugins:
            description = plugin.get_description()
            if description:  # Only show if plugin has a description
                plugin_action = QAction(f"{plugin.get_name()}: {description}", plugins_menu)
                plugin_action.setEnabled(False)  # Make it non-clickable, just informational
                plugins_menu.addAction(plugin_action)
        
        about_menu.addSeparator()
        
        # Credits/Info action
        credits_action = QAction("Jackdaw Info", about_menu)
        credits_action.triggered.connect(self.show_about)
        about_menu.addAction(credits_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("✕ Quit", menu)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
    
    def _cleanup_existing_processes(self):
        """Check for and stop any already-running voice assistant processes."""
        try:
            # Check if processes are running
            result = subprocess.run(
                ["pgrep", "-f", "voice_command_client.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Found existing voice assistant processes, stopping them...")
                subprocess.run(["pkill", "-f", "voice_command_client.py"], check=False)
                subprocess.run(["pkill", "-f", "llm_query_processor.py"], check=False)
                subprocess.run(["pkill", "-f", "tts_jack_client.py"], check=False)
                import time
                time.sleep(1)  # Give processes time to stop
                print("Existing processes stopped.")
        except Exception as e:
            print(f"Error checking for existing processes: {e}")
    
    def _check_for_duplicate_tray(self):
        """Check for other tray app instances and exit if found."""
        try:
            import os
            # Get list of all voice_assistant_tray.py processes
            result = subprocess.run(
                ["pgrep", "-f", "voice_assistant_tray.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Parse PIDs
                pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
                current_pid = os.getpid()
                
                # If there are other PIDs besides our own, another instance exists
                other_pids = [pid for pid in pids if pid != current_pid]
                if other_pids:
                    print(f"Another tray app instance is already running (PID: {other_pids[0]})")
                    print("This instance will exit to prevent duplicates.")
                    sys.exit(0)
        except Exception as e:
            print(f"Error checking for duplicate tray instances: {e}")
    
    def create_icon(self, is_active: bool = False) -> QIcon:
        """Create the jackdaw icon for the tray."""
        # Try to use the installed icon first
        icon = QIcon.fromTheme("jackdaw")
        if not icon.isNull():
            return icon
        
        # Fallback: try to load from local files
        icon_paths = [
            Path.home() / ".local/share/icons/hicolor/48x48/apps/jackdaw.png",
            Path(__file__).parent / "icons/hicolor/48x48/apps/jackdaw.png",
            Path(__file__).parent / "icons/jackdaw.png",
            Path(__file__).parent / "jackdaw-icon.png"
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                return QIcon(str(icon_path))
        
        # Last resort: create a simple programmatic icon
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush
        from PySide6.QtCore import QRect, QRectF
        
        # Create a 64x64 pixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw microphone
        # Choose color based on active state
        if is_active:
            mic_color = QColor(100, 200, 100)  # Green when active
            wave_color = QColor(100, 220, 100, 200)
        else:
            mic_color = QColor(120, 120, 120)  # Gray when inactive
            wave_color = QColor(150, 150, 150, 150)
        
        painter.setPen(QPen(mic_color.darker(120), 2))
        painter.setBrush(QBrush(mic_color))
        
        # Main mic body
        painter.drawRoundedRect(QRectF(22, 12, 20, 28), 10, 10)
        
        # Mic stand/handle
        painter.setPen(QPen(QColor(90, 90, 90), 2))
        painter.drawLine(32, 40, 32, 52)  # Vertical line down
        
        # Base arc
        painter.drawArc(QRect(20, 42, 24, 16), 0, 180 * 16)
        
        # Base horizontal line
        painter.drawLine(20, 58, 44, 58)
        
        # Add sound waves (only visible when active)
        if is_active:
            painter.setPen(QPen(wave_color, 2))
            
            # Left waves
            painter.drawArc(QRect(8, 20, 12, 12), -30 * 16, 60 * 16)
            painter.drawArc(QRect(4, 16, 16, 16), -30 * 16, 60 * 16)
            
            # Right waves
            painter.drawArc(QRect(44, 20, 12, 12), 150 * 16, 60 * 16)
            painter.drawArc(QRect(44, 16, 16, 16), 150 * 16, 60 * 16)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def detect_running_processes(self):
        """Detect if voice assistant processes are already running"""
        import subprocess as sp
        try:
            # Check for running processes
            voice_running = sp.run(["pgrep", "-f", "voice_command_client.py"], 
                                  capture_output=True, text=True).returncode == 0
            llm_running = sp.run(["pgrep", "-f", "llm_query_processor.py"], 
                                capture_output=True, text=True).returncode == 0
            tts_running = sp.run(["pgrep", "-f", "tts_jack_client.py"], 
                                capture_output=True, text=True).returncode == 0
            
            if voice_running and llm_running and tts_running:
                print("Detected voice assistant already running")
                self.processes_running = True
                self.start_action.setEnabled(False)
                self.stop_action.setEnabled(True)
                self.status_changed.emit("Running (external)")
                # Update icon to active state
                icon = self.create_icon(is_active=True)
                self.tray_icon.setIcon(icon)
                self.tray_icon.setToolTip("Jackdaw (Running)")
        except Exception as e:
            print(f"Error detecting processes: {e}")
    
    def start_voice_assistant(self):
        """Start all voice assistant components."""
        if self.processes_running:
            return
        
        print("Starting voice assistant components...")
        
        try:
            # Get the directory of this script
            script_dir = Path(__file__).parent.resolve()
            
            # Find the venv Python executable
            venv_python = script_dir / ".venv" / "bin" / "python"
            if not venv_python.exists():
                raise FileNotFoundError(f"Virtual environment Python not found at {venv_python}")
            
            # Use the venv Python directly with absolute paths
            print(f"Using Python: {venv_python}")
            print(f"Working directory: {script_dir}")
            
            # Prepare environment with venv paths
            import os
            env = os.environ.copy()
            env['VIRTUAL_ENV'] = str(script_dir / ".venv")
            env['PATH'] = f"{script_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
            
            # Start voice command client with log redirection
            self.voice_log = open(script_dir / "logs" / "voice_command.log", "a", buffering=1)
            self.voice_process = subprocess.Popen(
                [str(venv_python), "-u", "voice_command_client.py"],
                stdout=self.voice_log,
                stderr=self.voice_log,
                cwd=str(script_dir),
                env=env
            )
            
            # Start LLM processor with log redirection
            self.llm_log = open(script_dir / "logs" / "llm_processor.log", "a", buffering=1)
            self.llm_process = subprocess.Popen(
                [str(venv_python), "-u", "llm_query_processor.py"],
                stdout=self.llm_log,
                stderr=self.llm_log,
                cwd=str(script_dir),
                env=env
            )
            
            # Start TTS client with log redirection
            self.tts_log = open(script_dir / "logs" / "tts_client.log", "a", buffering=1)
            self.tts_process = subprocess.Popen(
                [str(venv_python), "-u", "tts_jack_client.py"],
                stdout=self.tts_log,
                stderr=self.tts_log,
                cwd=str(script_dir),
                env=env
            )
            
            self.processes_running = True
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_changed.emit("Running")
            
            print("✓ Voice assistant started")
            
        except Exception as e:
            print(f"Error starting voice assistant: {e}")
            import traceback
            traceback.print_exc()
            self.stop_voice_assistant()
    
    def stop_voice_assistant(self):
        """Stop all voice assistant components."""
        if not self.processes_running:
            return
        
        print("Stopping voice assistant components...")
        
        # Clean up plugins first (in case they're running in this process)
        try:
            self.plugin_loader.cleanup_all_plugins()
            print("Cleaned up plugins")
        except Exception as e:
            print(f"Error cleaning up plugins: {e}")
        
        # Terminate processes
        for process in [self.voice_process, self.llm_process, self.tts_process]:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2.0)
                except Exception as e:
                    print(f"Error stopping process: {e}")
                    try:
                        process.kill()
                    except Exception:
                        pass
        
        self.voice_process = None
        self.llm_process = None
        self.tts_process = None
        self.processes_running = False
        
        # Close log file handles
        for log_attr in ['voice_log', 'llm_log', 'tts_log']:
            if hasattr(self, log_attr):
                try:
                    getattr(self, log_attr).close()
                except Exception:
                    pass
        
        # Stop any FFmpeg processes (jd_stream for Icecast)
        try:
            import subprocess
            subprocess.run(['pkill', '-f', 'ffmpeg.*jd_stream'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✓ Stopped jd_stream (Icecast streaming)")
        except Exception as e:
            print(f"Note: Could not kill FFmpeg: {e}")
        
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.status_changed.emit("Stopped")
        
        print("✓ Voice assistant stopped")
    
    def update_status(self):
        """Update status information from voice assistant."""
        try:
            # Check if processes are still running
            if self.processes_running:
                try:
                    all_alive = all(
                        p and p.poll() is None 
                        for p in [self.voice_process, self.llm_process, self.tts_process]
                    )
                    if not all_alive:
                        print("Warning: Some processes died unexpectedly")
                        self.stop_voice_assistant()
                except Exception as e:
                    print(f"Error checking process status: {e}")
            
            # Update currently playing track
            try:
                self.update_now_playing()
            except Exception as e:
                print(f"Error updating now playing: {e}")
            
            # Update hub connection status
            try:
                self.update_hub_status()
            except Exception as e:
                print(f"Error updating hub status: {e}")
            
            # Check for update notifications
            try:
                self.check_update_notification()
            except Exception as e:
                print(f"Error checking updates: {e}")
        except Exception as e:
            print(f"Error in update_status: {e}")
            import traceback
            traceback.print_exc()
    
    def update_now_playing(self):
        """Update the currently playing track information."""
        try:
            import time
            
            # Check browser playback status first (from music_library_browser)
            browser_status_file = Path(".playback_status")
            if browser_status_file.exists():
                try:
                    with open(browser_status_file, 'r') as f:
                        browser_status = json.load(f)
                    
                    # Check if browser status is fresh (less than 5 seconds old)
                    if 'timestamp' in browser_status:
                        age = time.time() - browser_status['timestamp']
                        if age < 5.0:
                            # Browser status is fresh
                            if browser_status.get('status') == 'playing':
                                # Emit track info from browser
                                track_name = browser_status.get('track', 'Unknown')
                                self.track_changed.emit({
                                    'track': track_name,
                                    'artist': '',  # Browser doesn't provide artist in status
                                    'timestamp': browser_status['timestamp']
                                })
                                return
                            elif browser_status.get('status') == 'stopped':
                                # Browser stopped playback
                                self.track_changed.emit({})
                                return
                except Exception as e:
                    # Ignore errors reading browser status
                    pass
            
            # Fall back to voice command playback status (.now_playing.json)
            status_file = Path(".now_playing.json")
            if not status_file.exists():
                self.track_changed.emit({})
                return
                
            with open(status_file, 'r') as f:
                status = json.load(f)
                
                # Check if status is stale (older than 5 seconds)
                # This handles cases where playback stopped but file wasn't deleted
                if 'timestamp' in status:
                    age = time.time() - status['timestamp']
                    if age > 5.0:
                        # Status is stale, treat as not playing
                        self.track_changed.emit({})
                        return
                
                self.track_changed.emit(status)
        except Exception as e:
            # Silently ignore read errors (file might be mid-write)
            pass
    
    def update_hub_status(self):
        """Update hub connection status icon."""
        if not hasattr(self, 'hub_status_action') or not self.hub_status_action:
            return
        
        # Check if JackTrip plugin is loaded and connected
        is_connected = False
        if self.jacktrip_plugin and hasattr(self.jacktrip_plugin, 'current_room'):
            is_connected = self.jacktrip_plugin.current_room is not None
        
        # Update icon: ● for connected, ○ for disconnected
        icon = "●" if is_connected else "○"
        self.hub_status_action.setText(f"{icon} Hub Connection")
    
    def on_status_changed(self, status: str):
        """Handle status change signal."""
        try:
            if self.status_action:
                self.status_action.setText(f"Status: {status}")
            
            # Update icon based on status
            is_active = (status == "Running")
            icon = self.create_icon(is_active=is_active)
            if self.tray_icon:
                self.tray_icon.setIcon(icon)
            
                if status == "Running":
                    self.tray_icon.setToolTip(f"Jackdaw - {status}\nWake word: {self.config['voice']['recognition'].get('wake_word', 'N/A')}")
                else:
                    self.tray_icon.setToolTip(f"Jackdaw - {status}")
        except Exception as e:
            print(f"Error updating status UI: {e}")
    
    def on_track_changed(self, status: dict):
        """Handle track change signal."""
        try:
            if status and 'tags' in status and status['tags']:
                tags = status['tags']
                title = tags.get('title', status.get('filename', 'Unknown'))
                artist = tags.get('artist', 'Unknown Artist')
                text = f"♪ {title} - {artist}"
            else:
                text = "No track playing"
            
            if self.track_action:
                self.track_action.setText(text)
        except Exception as e:
            print(f"Error updating track UI: {e}")
    
    def show_plugin_gui(self, plugin):
        """Show the GUI form for a plugin."""
        try:
            widget = plugin.create_gui_widget()
            if widget:
                # Create a non-modal dialog to host the widget
                dialog = QDialog()
                dialog.setWindowTitle(plugin.get_description())
                dialog.setModal(False)
                
                # Make dialog independent (no parent) so it can be managed separately
                dialog.setParent(None)
                
                layout = QVBoxLayout()
                layout.addWidget(widget)
                dialog.setLayout(layout)
                
                # Track for cleanup
                self.opened_windows.append(dialog)
                dialog.destroyed.connect(lambda: self._remove_window(dialog))
                
                # Show non-blocking
                dialog.show()
                # Don't call exec() - that blocks until dialog closes
        except Exception as e:
            print(f"Error showing plugin GUI for {plugin.get_name()}: {e}")
    
    def _remove_window(self, window):
        """Remove window from tracking list when destroyed"""
        try:
            if window in self.opened_windows:
                self.opened_windows.remove(window)
        except:
            pass
    
    def show_logs_viewer(self):
        """Show a simple log viewer dialog."""
        dialog = QDialog()
        dialog.setWindowTitle("Jackdaw Logs")
        dialog.setModal(False)  # Non-modal
        dialog.resize(800, 600)
        
        # Track for cleanup
        self.opened_windows.append(dialog)
        dialog.destroyed.connect(lambda: self._remove_window(dialog))
        
        layout = QVBoxLayout()
        
        # Top controls: log selector and buttons
        controls_layout = QHBoxLayout()
        
        # Log file selector
        log_selector = QComboBox()
        
        # Find all log files
        log_dir = Path("logs")
        log_files = []
        if log_dir.exists():
            log_files = sorted([f.name for f in log_dir.glob("*.log")])
        
        if log_files:
            log_selector.addItems(log_files)
        else:
            log_selector.addItem("No logs found")
        
        controls_layout.addWidget(QLabel("Log file:"))
        controls_layout.addWidget(log_selector, 1)  # Stretch factor 1
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        controls_layout.addWidget(refresh_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑 Clear Log")
        controls_layout.addWidget(clear_btn)
        
        layout.addLayout(controls_layout)
        
        # Log viewer text area
        log_viewer = QTextEdit()
        log_viewer.setReadOnly(True)
        log_viewer.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(log_viewer)
        
        # Function to load selected log
        def load_log():
            try:
                selected = log_selector.currentText()
                if selected and selected != "No logs found":
                    log_file = Path("logs") / selected
                    if log_file.exists():
                        with open(log_file, 'r') as f:
                            content = f.read()
                            if content:
                                log_viewer.setPlainText(content)
                                # Scroll to bottom
                                scrollbar = log_viewer.verticalScrollBar()
                                scrollbar.setValue(scrollbar.maximum())
                            else:
                                log_viewer.setPlainText(f"[{selected} is empty]")
                    else:
                        log_viewer.setPlainText(f"Log file not found: {selected}")
            except Exception as e:
                log_viewer.setPlainText(f"Error loading log: {e}")
        
        # Function to clear selected log
        def clear_log():
            try:
                selected = log_selector.currentText()
                if selected and selected != "No logs found":
                    reply = QMessageBox.question(
                        dialog,
                        "Clear Log",
                        f"Are you sure you want to clear {selected}?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        log_file = Path("logs") / selected
                        if log_file.exists():
                            # Clear the file by writing empty string
                            with open(log_file, 'w') as f:
                                f.write("")
                            log_viewer.setPlainText(f"[{selected} cleared]")
                        else:
                            log_viewer.setPlainText(f"Log file not found: {selected}")
            except Exception as e:
                log_viewer.setPlainText(f"Error clearing log: {e}")
        
        # Connect signals
        log_selector.currentTextChanged.connect(lambda: load_log())
        refresh_btn.clicked.connect(load_log)
        clear_btn.clicked.connect(clear_log)
        
        # Load initial log
        load_log()
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.show()  # Non-blocking
    
    def launch_music_browser(self):
        """Launch the music library browser application."""
        try:
            script_dir = Path(__file__).parent.resolve()
            venv_python = script_dir / ".venv" / "bin" / "python"
            
            # Check if database exists
            db_path = script_dir / "music_library.sqlite3"
            if not db_path.exists():
                dialog = QDialog()
                dialog.setWindowTitle("Database Not Found")
                layout = QVBoxLayout()
                
                msg = QLabel(
                    "Music library database not found.\n\n"
                    "Please run the music scanner first:\n"
                    "python tools/scan_music_library.py /path/to/music"
                )
                layout.addWidget(msg)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.close)
                layout.addWidget(close_btn)
                
                dialog.setLayout(layout)
                dialog.show()  # Non-blocking
                return
            
            # Launch the browser in a separate process
            import os
            env = os.environ.copy()
            env['VIRTUAL_ENV'] = str(script_dir / ".venv")
            env['PATH'] = f"{script_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
            
            # Store the process handle
            self.browser_process = subprocess.Popen(
                [str(venv_python), "music_library_browser.py"],
                cwd=str(script_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print("Music library browser launched")
            
        except Exception as e:
            print(f"Error launching music browser: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error dialog
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Launch Error",
                f"Failed to launch music browser:\n{e}"
            )
    
    def show_aliases_editor(self):
        """Show the command aliases editor"""
        try:
            editor = CommandAliasesEditor()
            editor.setModal(False)  # Non-modal
            
            # Track for cleanup
            self.opened_windows.append(editor)
            editor.destroyed.connect(lambda: self._remove_window(editor))
            
            editor.show()  # Non-blocking
        except Exception as e:
            print(f"Error showing aliases editor: {e}")
            QMessageBox.critical(
                None,
                "Aliases Editor Error",
                f"Failed to launch aliases editor:\n{e}"
            )
    
    def remember_jack_routing(self):
        """Run the remember_jack_routing.py script."""
        try:
            script_dir = Path(__file__).parent.resolve()
            venv_python = script_dir / ".venv" / "bin" / "python"
            
            # Prepare environment
            import os
            env = os.environ.copy()
            env['VIRTUAL_ENV'] = str(script_dir / ".venv")
            env['PATH'] = f"{script_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
            
            # Run the script
            result = subprocess.run(
                [str(venv_python), "tools/remember_jack_routing.py"],
                cwd=str(script_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Show result in a dialog
            dialog = QDialog()
            dialog.setWindowTitle("JACK Connections Saved")
            dialog.setMinimumWidth(500)
            
            # Track for cleanup
            self.opened_windows.append(dialog)
            dialog.destroyed.connect(lambda: self._remove_window(dialog))
            
            layout = QVBoxLayout()
            
            output_text = QTextEdit()
            output_text.setReadOnly(True)
            output_text.setPlainText(result.stdout if result.returncode == 0 else result.stderr)
            layout.addWidget(output_text)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.show()  # Non-blocking
            
        except Exception as e:
            # Show error dialog
            dialog = QDialog()
            dialog.setWindowTitle("Error")
            
            # Track for cleanup
            self.opened_windows.append(dialog)
            dialog.destroyed.connect(lambda: self._remove_window(dialog))
            
            layout = QVBoxLayout()
            
            error_label = QLabel(f"Failed to save JACK routing:\n{str(e)}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.show()  # Non-blocking
    
    def show_voice_commands_reference(self):
        """Show comprehensive voice commands reference grouped by plugin."""
        dialog = QDialog()
        dialog.setWindowTitle("Voice Commands Reference")
        dialog.resize(700, 600)
        
        # Track for cleanup
        self.opened_windows.append(dialog)
        dialog.destroyed.connect(lambda: self._remove_window(dialog))
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(
            "<h2>Available Voice Commands</h2>"
            f"<p>Wake word: <b>{self.config['voice']['recognition'].get('wake_word', 'N/A')}</b></p>"
            "<p>Say the wake word followed by any command below:</p>"
        )
        header.setTextFormat(Qt.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)
        
        # Scrollable area for commands
        scroll = QTextEdit()
        scroll.setReadOnly(True)
        
        # Build command reference HTML
        html = "<style>h3 { color: #2196F3; margin-top: 15px; } "
        html += "p { margin: 5px 0 5px 20px; } "
        html += ".command { color: #4CAF50; font-family: monospace; } "
        html += ".wake { color: #FF9800; font-weight: bold; }</style>"
        
        wake_word = self.config['voice']['recognition'].get('wake_word', 'indigo')
        
        # Group commands by plugin
        for plugin in sorted(self.plugins, key=lambda p: p.get_name()):
            # Try to get friendly command examples first
            examples = []
            if hasattr(plugin, 'get_command_examples'):
                examples = plugin.get_command_examples()
            
            # Fall back to raw regex patterns if no examples provided
            if not examples:
                commands = plugin.get_commands()
                if commands:
                    examples = sorted(commands.keys())
            
            if not examples:
                continue
            
            plugin_name = plugin.get_name().replace('_', ' ').title()
            plugin_desc = plugin.get_description()
            
            html += f"<h3>{plugin_name}</h3>"
            if plugin_desc:
                html += f"<p><i>{plugin_desc}</i></p>"
            
            for command in examples:
                html += f'<p><span class="wake">{wake_word}</span> <span class="command">{command}</span></p>'
        
        scroll.setHtml(html)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.show()  # Non-blocking
    
    def show_about(self):
        """Show about dialog."""
        dialog = QDialog()
        dialog.setWindowTitle("About Jackdaw")
        
        # Track for cleanup
        self.opened_windows.append(dialog)
        dialog.destroyed.connect(lambda: self._remove_window(dialog))
        
        layout = QVBoxLayout()
        
        about_text = QLabel(
            "<h2>Jackdaw Voice Assistant</h2>"
            "<p>A modular voice-controlled assistant using JACK Audio</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Vosk speech recognition</li>"
            "<li>Ollama LLM integration</li>"
            "<li>Piper TTS</li>"
            "<li>Music playback with database queries</li>"
            "<li>Plugin-based architecture</li>"
            "</ul>"
            "<p><b>Loaded Plugins:</b></p>"
        )
        about_text.setTextFormat(Qt.RichText)
        about_text.setWordWrap(True)
        layout.addWidget(about_text)
        
        # List plugins
        for plugin in self.plugins:
            plugin_label = QLabel(f"• {plugin.get_name()}: {plugin.get_description()}")
            layout.addWidget(plugin_label)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.show()  # Non-blocking
    
    def music_next_track(self):
        """Skip to next track."""
        try:
            import audio_jack_player
            audio_jack_player.skip_to_next_track()
        except Exception as e:
            print(f"Error skipping track: {e}")
    
    def music_stop(self):
        """Stop music playback."""
        try:
            import audio_jack_player
            audio_jack_player.stop_playback()
        except Exception as e:
            print(f"Error stopping music: {e}")
    
    def music_volume_up(self):
        """Increase volume by 10%."""
        try:
            import audio_jack_player
            audio_jack_player.adjust_volume(0.1)
        except Exception as e:
            print(f"Error adjusting volume: {e}")
    
    def music_volume_down(self):
        """Decrease volume by 10%."""
        try:
            import audio_jack_player
            audio_jack_player.adjust_volume(-0.1)
        except Exception as e:
            print(f"Error adjusting volume: {e}")
    
    def show_chat_widget(self):
        """Show the AI Chat interface widget."""
        try:
            if self.llm_recorder_plugin:
                self.show_plugin_gui(self.llm_recorder_plugin)
            else:
                print("LLM recorder plugin not available")
        except Exception as e:
            print(f"Error showing chat widget: {e}")
    
    def launch_music_scanner(self):
        """Launch the music library scanner widget"""
        try:
            scanner = MusicScannerWidget()
            scanner.setModal(False)  # Non-modal
            
            # Track for cleanup
            self.opened_windows.append(scanner)
            scanner.destroyed.connect(lambda: self._remove_window(scanner))
            
            scanner.show()  # Non-blocking
        except Exception as e:
            print(f"Error launching music scanner: {e}")
            QMessageBox.critical(
                None,
                "Scanner Error",
                f"Failed to launch music scanner:\n{e}"
            )
    
    def check_update_notification(self):
        """Check for update notification file and update menu accordingly"""
        notification_file = Path(".update_available")
        if notification_file.exists():
            try:
                message = notification_file.read_text().strip()
                # Update menu item to show update available
                if hasattr(self, 'check_updates_action'):
                    self.check_updates_action.setText("⚠ Update Available")
                    self.check_updates_action.setToolTip(message)
            except Exception:
                pass
        else:
            # Reset to default text
            if hasattr(self, 'check_updates_action'):
                self.check_updates_action.setText("✓ System Up to Date")
                self.check_updates_action.setToolTip("")
    
    def check_for_updates(self):
        """Manual update check triggered from menu"""
        try:
            subprocess.Popen(
                ['python', 'check_updates.py'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Give it a moment to complete
            QTimer.singleShot(2000, self.check_update_notification)
        except Exception as e:
            print(f"Error checking for updates: {e}")
    
    def quit_application(self):
        """Quit the application."""
        # Close all opened windows first
        print(f"Closing {len(self.opened_windows)} opened windows...")
        for window in self.opened_windows[:]:  # Copy list to avoid modification during iteration
            try:
                window.close()
            except:
                pass
        self.opened_windows.clear()
        
        # Terminate music browser process if running
        if self.browser_process:
            try:
                print("Terminating music library browser...")
                self.browser_process.terminate()
                self.browser_process.wait(timeout=2.0)
            except:
                try:
                    self.browser_process.kill()
                except:
                    pass
            self.browser_process = None
        
        self.stop_voice_assistant()
        self.plugin_loader.cleanup_all_plugins()
        # Exit with code 0 so launcher knows it's intentional
        QApplication.exit(0)
    
    def run(self):
        """Run the application."""
        return self.app.exec()


def main():
    """Main entry point with exception handling."""
    import traceback
    
    try:
        app = VoiceAssistantTray()
        sys.exit(app.run())
    except Exception as e:
        print(f"Fatal error in tray application: {e}")
        traceback.print_exc()
        
        # Try to log the error
        try:
            log_path = Path("logs/tray_crash.log")
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, "a") as f:
                from datetime import datetime
                f.write(f"\n\n=== Crash at {datetime.now()} ===\n")
                f.write(f"Error: {e}\n")
                f.write(traceback.format_exc())
            print(f"Error logged to {log_path}")
        except:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()
