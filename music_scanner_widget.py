#!/usr/bin/env python3
"""
Music Library Scanner GUI Widget

Provides a graphical interface for scanning the music library and populating the database.
Reads the music library path from voice_assistant_config.json.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTextEdit, QProgressBar, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal


class ScannerThread(QThread):
    """Background thread for running the music scanner"""
    
    # Signals for progress updates
    output_received = Signal(str)
    scan_finished = Signal(int)  # Exit code
    
    def __init__(self, directory: str, analyze_bpm: bool = False):
        super().__init__()
        self.directory = directory
        self.analyze_bpm = analyze_bpm
        self.process = None
    
    def run(self):
        """Run the scanner script"""
        cmd = ['python', 'tools/scan_music_library.py', self.directory]
        if self.analyze_bpm:
            cmd.append('--bpm')
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output line by line
            for line in self.process.stdout:
                self.output_received.emit(line.rstrip())
            
            # Wait for completion
            exit_code = self.process.wait()
            self.scan_finished.emit(exit_code)
            
        except Exception as e:
            self.output_received.emit(f"Error: {str(e)}")
            self.scan_finished.emit(1)
    
    def stop(self):
        """Stop the scanning process"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


class MusicScannerWidget(QDialog):
    """GUI widget for scanning music library"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Music Library Scanner")
        self.resize(700, 500)
        
        # Load config to get music library path
        self.library_path = self._load_library_path()
        
        # Scanner thread
        self.scanner_thread: Optional[ScannerThread] = None
        
        self._setup_ui()
    
    def _load_library_path(self) -> str:
        """Load music library path from config"""
        try:
            config_file = Path("voice_assistant_config.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return config.get('music', {}).get('library_path', '')
        except Exception as e:
            print(f"Error loading config: {e}")
        return ''
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Music Library Scanner")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Library path info
        path_label = QLabel(f"<b>Library Path:</b> {self.library_path or 'Not configured'}")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        if not self.library_path:
            warning = QLabel("⚠ No music library path configured in voice_assistant_config.json")
            warning.setStyleSheet("color: orange; font-weight: bold;")
            layout.addWidget(warning)
        
        # Options
        options_layout = QHBoxLayout()
        
        self.bpm_checkbox = QCheckBox("Analyze BPM (slower, adds ~2-5 seconds per track)")
        options_layout.addWidget(self.bpm_checkbox)
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # Output area
        output_label = QLabel("Scan Output:")
        layout.addWidget(output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-family: monospace; background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.output_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self._start_scan)
        self.scan_button.setEnabled(bool(self.library_path))
        button_layout.addWidget(self.scan_button)
        
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.clicked.connect(self._stop_scan)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Info text
        info = QLabel(
            "This will scan your music library and populate the database with metadata.\n"
            "BPM analysis is optional but significantly slower."
        )
        info.setStyleSheet("color: gray; font-size: 9pt;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.setLayout(layout)
    
    def _start_scan(self):
        """Start the music library scan"""
        if not self.library_path:
            QMessageBox.warning(
                self,
                "No Library Path",
                "Please configure music.library_path in voice_assistant_config.json"
            )
            return
        
        # Check if path exists
        if not Path(self.library_path).exists():
            QMessageBox.warning(
                self,
                "Path Not Found",
                f"The configured library path does not exist:\n{self.library_path}"
            )
            return
        
        # Clear output
        self.output_text.clear()
        self.output_text.append(f"Starting scan of: {self.library_path}\n")
        
        # Disable start button, enable stop button
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.bpm_checkbox.setEnabled(False)
        self.progress_bar.show()
        
        # Start scanner thread
        self.scanner_thread = ScannerThread(
            self.library_path,
            self.bpm_checkbox.isChecked()
        )
        self.scanner_thread.output_received.connect(self._on_output)
        self.scanner_thread.scan_finished.connect(self._on_finished)
        self.scanner_thread.start()
    
    def _stop_scan(self):
        """Stop the current scan"""
        if self.scanner_thread:
            self.output_text.append("\n⏹ Stopping scan...")
            self.scanner_thread.stop()
            self.scanner_thread.wait()
            self._on_finished(1)
    
    def _on_output(self, line: str):
        """Handle output from scanner"""
        self.output_text.append(line)
        # Auto-scroll to bottom
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )
    
    def _on_finished(self, exit_code: int):
        """Handle scan completion"""
        self.progress_bar.hide()
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.bpm_checkbox.setEnabled(True)
        
        if exit_code == 0:
            self.output_text.append("\n✓ Scan completed successfully!")
            self.output_text.append("You can now use voice commands to play music from your library.")
        else:
            self.output_text.append(f"\n✗ Scan finished with errors (exit code: {exit_code})")
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.scanner_thread and self.scanner_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Scan in Progress",
                "A scan is currently running. Stop it and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._stop_scan()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Standalone test of the widget"""
    app = QApplication(sys.argv)
    widget = MusicScannerWidget()
    widget.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
