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
        # Create icon (you can replace this with an actual icon file)
        icon = self.create_default_icon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Voice Assistant (Stopped)")
        
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
        self.start_action = QAction("▶ Start Voice Assistant", menu)
        self.start_action.triggered.connect(self.start_voice_assistant)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("⏹ Stop Voice Assistant", menu)
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
                action.triggered.connect(lambda checked, p=plugin: self.show_plugin_gui(p))
                menu.addAction(action)
                self.plugin_menu_items[plugin_name] = action
        
        if self.plugin_menu_items:
            menu.addSeparator()
        
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
    
    def create_default_icon(self) -> QIcon:
        """Create a simple default icon."""
        # Create a simple colored square as default icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.blue)
        return QIcon(pixmap)
    
    def start_voice_assistant(self):
        """Start all voice assistant components."""
        if self.processes_running:
            return
        
        print("Starting voice assistant components...")
        
        try:
            # Start voice command client
            self.voice_process = subprocess.Popen(
                [sys.executable, "voice_command_client.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            # Start LLM processor
            self.llm_process = subprocess.Popen(
                [sys.executable, "-u", "llm_query_processor.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            # Start TTS client
            self.tts_process = subprocess.Popen(
                [sys.executable, "-u", "tts_jack_client.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd()
            )
            
            self.processes_running = True
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_changed.emit("Running")
            
            print("✓ Voice assistant started")
            
        except Exception as e:
            print(f"Error starting voice assistant: {e}")
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
        
        if status == "Running":
            self.tray_icon.setToolTip(f"Voice Assistant - {status}\nWake word: {self.config['voice']['recognition'].get('wake_word', 'N/A')}")
        else:
            self.tray_icon.setToolTip(f"Voice Assistant - {status}")
    
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
        dialog.setWindowTitle("Voice Assistant Logs")
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
    
    def show_about(self):
        """Show about dialog."""
        dialog = QDialog()
        dialog.setWindowTitle("About Voice Assistant")
        
        layout = QVBoxLayout()
        
        about_text = QLabel(
            "<h2>Voice Assistant</h2>"
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
