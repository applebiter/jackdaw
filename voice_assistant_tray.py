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
        
        # Create tray icon
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
        
        self.tray_icon = QSystemTrayIcon()
        self.setup_tray_icon()
        
        # Status monitoring timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # Update every 2 seconds
        
        # Connect signals
        self.status_changed.connect(self.on_status_changed)
        self.track_changed.connect(self.on_track_changed)
    
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
        
        # Plugin GUI forms
        self.plugin_menu_items = {}
        for plugin in self.plugins:
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
        # Check if processes are still running
        if self.processes_running:
            all_alive = all(
                p and p.poll() is None 
                for p in [self.voice_process, self.llm_process, self.tts_process]
            )
            if not all_alive:
                print("Warning: Some processes died unexpectedly")
                self.stop_voice_assistant()
        
        # Update currently playing track
        self.update_now_playing()
    
    def update_now_playing(self):
        """Update the currently playing track information."""
        try:
            status_file = Path(".now_playing.json")
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status = json.load(f)
                self.track_changed.emit(status)
            else:
                self.track_changed.emit({})
        except Exception:
            pass
    
    def on_status_changed(self, status: str):
        """Handle status change signal."""
        self.status_action.setText(f"Status: {status}")
        
        # Update icon based on status
        is_active = (status == "Running")
        icon = self.create_icon(is_active=is_active)
        self.tray_icon.setIcon(icon)
        
        if status == "Running":
            self.tray_icon.setToolTip(f"Jackdaw - {status}\nWake word: {self.config['voice']['recognition'].get('wake_word', 'N/A')}")
        else:
            self.tray_icon.setToolTip(f"Jackdaw - {status}")
    
    def on_track_changed(self, status: dict):
        """Handle track change signal."""
        if status and 'tags' in status and status['tags']:
            tags = status['tags']
            title = tags.get('title', status.get('filename', 'Unknown'))
            artist = tags.get('artist', 'Unknown Artist')
            text = f"♪ {title} - {artist}"
        else:
            text = "No track playing"
        
        self.track_action.setText(text)
    
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
    
    def quit_application(self):
        """Quit the application."""
        self.stop_voice_assistant()
        self.plugin_loader.cleanup_all_plugins()
        QApplication.quit()
    
    def run(self):
        """Run the application."""
        return self.app.exec()


def main():
    """Main entry point."""
    app = VoiceAssistantTray()
    sys.exit(app.run())


if __name__ == '__main__':
    main()
