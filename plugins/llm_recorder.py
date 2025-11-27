#!/usr/bin/env python3
"""
LLM Recorder Plugin

Provides voice commands for capturing extended speech and sending it to the LLM
for processing through file-based IPC.
"""

from typing import Dict, Callable, Any
from pathlib import Path
import sqlite3
import json
from plugin_base import VoiceAssistantPlugin


class LLMRecorderPlugin(VoiceAssistantPlugin):
    """
    Plugin for recording voice input and sending to LLM.
    
    Allows users to start/stop text capture for longer form queries
    to the language model.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.voice_client = None  # Will be set by plugin loader
    
    def get_name(self) -> str:
        return "llm_recorder"
    
    def get_description(self) -> str:
        return "Record extended speech and send to LLM for processing"
    
    def set_voice_client(self, client):
        """
        Set reference to the VoiceCommandClient for text capture.
        Called by the plugin loader after initialization.
        """
        self.voice_client = client
    
    def get_commands(self) -> Dict[str, Callable]:
        """Register LLM recording commands."""
        return {
            "start chat": self._cmd_start_recording,
            "stop chat": self._cmd_stop_recording,
        }
    
    # Command handlers
    def _cmd_start_recording(self):
        """Start capturing text for LLM query."""
        if self.voice_client:
            self.voice_client.start_text_capture()
        else:
            print(f"[{self.get_name()}] Error: No voice client available")
    
    def _cmd_stop_recording(self):
        """Stop capturing and send to LLM."""
        if self.voice_client:
            self.voice_client.stop_text_capture()
        else:
            print(f"[{self.get_name()}] Error: No voice client available")
    
    def create_gui_widget(self):
        """Create a GUI widget for LLM chat interface."""
        try:
            from PySide6.QtWidgets import (
                QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                QTextEdit, QLabel, QLineEdit, QScrollArea, QFrame
            )
            from PySide6.QtCore import QTimer, Qt
            from PySide6.QtGui import QFont
            
            widget = QWidget()
            main_layout = QVBoxLayout()
            
            # Session info header
            session_header = QLabel("Current Session")
            session_header_font = QFont()
            session_header_font.setBold(True)
            session_header_font.setPointSize(11)
            session_header.setFont(session_header_font)
            main_layout.addWidget(session_header)
            
            self.session_id_label = QLabel("Session: Loading...")
            self.session_id_label.setWordWrap(True)
            main_layout.addWidget(self.session_id_label)
            
            # Conversation history display
            history_label = QLabel("Conversation History:")
            main_layout.addWidget(history_label)
            
            self.history_display = QTextEdit()
            self.history_display.setReadOnly(True)
            self.history_display.setMinimumHeight(300)
            main_layout.addWidget(self.history_display)
            
            # Manual prompt entry section
            prompt_label = QLabel("Manual Prompt Entry:")
            main_layout.addWidget(prompt_label)
            
            self.manual_prompt = QTextEdit()
            self.manual_prompt.setPlaceholderText("Type your prompt here (optional - you can also use voice recording)")
            self.manual_prompt.setMaximumHeight(80)
            main_layout.addWidget(self.manual_prompt)
            
            # Control buttons
            button_layout = QHBoxLayout()
            
            self.start_recording_btn = QPushButton("🎙 Start Voice Recording")
            self.start_recording_btn.clicked.connect(self._gui_start_recording)
            button_layout.addWidget(self.start_recording_btn)
            
            self.stop_recording_btn = QPushButton("⏹ Stop & Send")
            self.stop_recording_btn.clicked.connect(self._gui_stop_recording)
            self.stop_recording_btn.setEnabled(False)
            button_layout.addWidget(self.stop_recording_btn)
            
            self.send_manual_btn = QPushButton("📤 Send Manual Prompt")
            self.send_manual_btn.clicked.connect(self._gui_send_manual)
            button_layout.addWidget(self.send_manual_btn)
            
            main_layout.addLayout(button_layout)
            
            # Recording status indicator
            self.status_label = QLabel("Status: Ready")
            main_layout.addWidget(self.status_label)
            
            # Refresh button
            refresh_btn = QPushButton("🔄 Refresh History")
            refresh_btn.clicked.connect(self._update_history)
            main_layout.addWidget(refresh_btn)
            
            widget.setLayout(main_layout)
            
            # Timer to update conversation history
            self.history_timer = QTimer(widget)
            self.history_timer.timeout.connect(self._update_history)
            self.history_timer.start(3000)  # Update every 3 seconds
            
            # Initial update
            self._update_history()
            
            return widget
            
        except ImportError:
            print(f"[{self.get_name()}] PySide6 not available, GUI disabled")
            return None
        except Exception as e:
            print(f"[{self.get_name()}] Error creating GUI widget: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _update_history(self):
        """Update the conversation history display."""
        try:
            db_path = Path("conversations.sqlite3")
            if not db_path.exists():
                self.history_display.setHtml("<i>No conversation database found</i>")
                return
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Get current session
            import socket
            hostname = socket.gethostname()
            
            cur.execute(
                """
                SELECT session_id, created_at, last_activity 
                FROM conversation_sessions
                WHERE hostname = ? AND is_active = 1
                ORDER BY last_activity DESC
                LIMIT 1
                """,
                (hostname,)
            )
            session_row = cur.fetchone()
            
            if not session_row:
                self.session_id_label.setText("Session: No active session")
                self.history_display.setHtml("<i>No active session. Start a conversation to begin.</i>")
                conn.close()
                return
            
            session_id = session_row['session_id']
            self.session_id_label.setText(f"Session: {session_id[:8]}... (since {session_row['created_at']})")
            
            # Get messages for this session
            cur.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE hostname = ? AND session_id = ?
                ORDER BY created_at ASC
                """,
                (hostname, session_id)
            )
            
            messages = cur.fetchall()
            conn.close()
            
            if not messages:
                self.history_display.setHtml("<i>No messages in this session yet.</i>")
                return
            
            # Format conversation as HTML
            html = "<div style='font-family: monospace;'>"
            for msg in messages:
                role = msg['role']
                content = msg['content'].replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                timestamp = msg['created_at'].split('.')[0]  # Remove microseconds
                
                if role == 'user':
                    html += f"<p style='margin: 10px 0; padding: 8px; background-color: #e3f2fd; border-left: 4px solid #2196f3;'>"
                    html += f"<b>👤 You</b> <span style='color: #666; font-size: 0.9em;'>({timestamp})</span><br>{content}</p>"
                elif role == 'assistant':
                    html += f"<p style='margin: 10px 0; padding: 8px; background-color: #f1f8e9; border-left: 4px solid #8bc34a;'>"
                    html += f"<b>🤖 Assistant</b> <span style='color: #666; font-size: 0.9em;'>({timestamp})</span><br>{content}</p>"
                else:
                    html += f"<p style='margin: 10px 0; padding: 8px; background-color: #fafafa; border-left: 4px solid #999;'>"
                    html += f"<b>{role}</b> <span style='color: #666; font-size: 0.9em;'>({timestamp})</span><br>{content}</p>"
            
            html += "</div>"
            self.history_display.setHtml(html)
            
            # Auto-scroll to bottom
            scrollbar = self.history_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            print(f"[{self.get_name()}] Error updating history: {e}")
            import traceback
            traceback.print_exc()
    
    def _gui_start_recording(self):
        """Start voice recording from GUI."""
        self._cmd_start_recording()
        self.start_recording_btn.setEnabled(False)
        self.stop_recording_btn.setEnabled(True)
        self.status_label.setText("Status: 🎙 Recording... (say your prompt)")
    
    def _gui_stop_recording(self):
        """Stop voice recording from GUI."""
        self._cmd_stop_recording()
        self.start_recording_btn.setEnabled(True)
        self.stop_recording_btn.setEnabled(False)
        self.status_label.setText("Status: Sent to LLM, waiting for response...")
        # Update history shortly after sending
        QTimer.singleShot(2000, self._update_history)
    
    def _gui_send_manual(self):
        """Send manually typed prompt."""
        try:
            prompt_text = self.manual_prompt.toPlainText().strip()
            if not prompt_text:
                self.status_label.setText("Status: ⚠ No text to send")
                return
            
            # Write to query file (same mechanism as voice recording)
            query_file = Path(".llm_query")
            query_file.write_text(prompt_text, encoding='utf-8')
            
            self.manual_prompt.clear()
            self.status_label.setText("Status: ✅ Manual prompt sent to LLM")
            
            # Update history shortly after sending
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self._update_history)
            
        except Exception as e:
            print(f"[{self.get_name()}] Error sending manual prompt: {e}")
            self.status_label.setText(f"Status: ❌ Error sending prompt")
