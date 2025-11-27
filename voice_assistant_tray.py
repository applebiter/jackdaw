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
    QVBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
)
from PySide6.QtCore import QTimer, Signal, QObject, Qt
from PySide6.QtGui import QIcon, QAction, QPixmap

from plugin_loader import PluginLoader


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
        
        # Voice assistant processes
        self.voice_process: Optional[subprocess.Popen] = None
        self.llm_process: Optional[subprocess.Popen] = None
        self.tts_process: Optional[subprocess.Popen] = None
        self.processes_running = False
        
        # Load plugins
        self.plugin_loader = PluginLoader(self.config)
        self.plugins = self.plugin_loader.load_all_plugins()
        self.llm_recorder_plugin = None  # Will be set during menu setup
        
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
        
        # Music submenu
        music_menu = menu.addMenu("🎵 Music")
        
        # Music browser action
        music_browser_action = QAction("📂 Library Browser", music_menu)
        music_browser_action.triggered.connect(self.launch_music_browser)
        music_menu.addAction(music_browser_action)
        
        music_menu.addSeparator()
        
        # Music playback controls
        next_track_action = QAction("⏭ Next Track", music_menu)
        next_track_action.triggered.connect(self.music_next_track)
        music_menu.addAction(next_track_action)
        
        stop_music_action = QAction("⏹ Stop Playback", music_menu)
        stop_music_action.triggered.connect(self.music_stop)
        music_menu.addAction(stop_music_action)
        
        music_menu.addSeparator()
        
        volume_up_action = QAction("🔊 Volume Up", music_menu)
        volume_up_action.triggered.connect(self.music_volume_up)
        music_menu.addAction(volume_up_action)
        
        volume_down_action = QAction("🔉 Volume Down", music_menu)
        volume_down_action.triggered.connect(self.music_volume_down)
        music_menu.addAction(volume_down_action)
        
        menu.addSeparator()
        
        # AI Chat submenu - open the widget instead of inline controls
        chat_action = QAction("🤖 AI Chat", menu)
        chat_action.triggered.connect(self.show_chat_widget)
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        # Plugin GUI forms (excluding llm_recorder since we added it above)
        self.plugin_menu_items = {}
        for plugin in self.plugins:
            # Skip llm_recorder plugin since we integrated it as AI Chat menu item
            if plugin.get_name() == 'llm_recorder':
                self.llm_recorder_plugin = plugin  # Store reference for widget
                continue
                
            if hasattr(plugin, 'create_gui_widget') and callable(getattr(plugin, 'create_gui_widget')):
                plugin_name = plugin.get_name()
                action = QAction(f"🔧 {plugin.get_description()}", menu)
                action.triggered.connect(lambda checked=False, p=plugin: self.show_plugin_gui(p))
                menu.addAction(action)
                self.plugin_menu_items[plugin_name] = action
        
        if self.plugin_menu_items:
            menu.addSeparator()
        
        # Tools submenu
        tools_menu = menu.addMenu("🔧 Tools")
        
        # Remember JACK routing action
        remember_routing_action = QAction("💾 Save JACK Connections", tools_menu)
        remember_routing_action.triggered.connect(self.remember_jack_routing)
        tools_menu.addAction(remember_routing_action)
        
        # View logs action
        view_logs_action = QAction("📋 View Logs", menu)
        view_logs_action.triggered.connect(self.show_logs_viewer)
        menu.addAction(view_logs_action)
        
        menu.addSeparator()
        
        # About action
        about_action = QAction("ℹ About", menu)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
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
    
    def create_icon(self, is_active: bool = False) -> QIcon:
        """Create a microphone icon for the tray."""
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
            
            # Start voice command client
            self.voice_process = subprocess.Popen(
                [str(venv_python), "voice_command_client.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(script_dir),
                env=env
            )
            
            # Start LLM processor
            self.llm_process = subprocess.Popen(
                [str(venv_python), "-u", "llm_query_processor.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(script_dir),
                env=env
            )
            
            # Start TTS client
            self.tts_process = subprocess.Popen(
                [str(venv_python), "-u", "tts_jack_client.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
        except Exception as e:
            print(f"Error in update_status: {e}")
            import traceback
            traceback.print_exc()
    
    def update_now_playing(self):
        """Update the currently playing track information."""
        try:
            status_file = Path(".now_playing.json")
            if not status_file.exists():
                self.track_changed.emit({})
                return
                
            with open(status_file, 'r') as f:
                status = json.load(f)
                self.track_changed.emit(status)
        except Exception as e:
            # Silently ignore read errors (file might be mid-write)
            pass
    
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
                # Create a dialog to host the widget
                dialog = QDialog()
                dialog.setWindowTitle(plugin.get_description())
                dialog.setModal(False)
                
                layout = QVBoxLayout()
                layout.addWidget(widget)
                dialog.setLayout(layout)
                
                dialog.show()
                dialog.exec()
        except Exception as e:
            print(f"Error showing plugin GUI for {plugin.get_name()}: {e}")
    
    def show_logs_viewer(self):
        """Show a simple log viewer dialog."""
        dialog = QDialog()
        dialog.setWindowTitle("Jackdaw Logs")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create tabs or combo for different logs
        log_viewer = QTextEdit()
        log_viewer.setReadOnly(True)
        
        # Load and display voice command log
        try:
            log_file = Path("logs/voice_command.log")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Show last 500 lines
                    log_viewer.setPlainText(''.join(lines[-500:]))
        except Exception as e:
            log_viewer.setPlainText(f"Error loading logs: {e}")
        
        layout.addWidget(log_viewer)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
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
                dialog.exec()
                return
            
            # Launch the browser in a separate process
            import os
            env = os.environ.copy()
            env['VIRTUAL_ENV'] = str(script_dir / ".venv")
            env['PATH'] = f"{script_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
            
            subprocess.Popen(
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
            
            layout = QVBoxLayout()
            
            output_text = QTextEdit()
            output_text.setReadOnly(True)
            output_text.setPlainText(result.stdout if result.returncode == 0 else result.stderr)
            layout.addWidget(output_text)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            # Show error dialog
            dialog = QDialog()
            dialog.setWindowTitle("Error")
            layout = QVBoxLayout()
            
            error_label = QLabel(f"Failed to save JACK routing:\n{str(e)}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
    
    def show_about(self):
        """Show about dialog."""
        dialog = QDialog()
        dialog.setWindowTitle("About Jackdaw")
        
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
        dialog.exec()
    
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
    
    def quit_application(self):
        """Quit the application."""
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
