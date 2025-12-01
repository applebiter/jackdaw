#!/usr/bin/env python3
"""
Command Aliases Editor Widget

Provides a GUI for managing voice command aliases.
Allows users to create custom phrases that map to existing commands.
"""

import sys
import json
from pathlib import Path
from typing import Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CommandAliasesEditor(QDialog):
    """GUI widget for editing command aliases"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Command Aliases")
        self.resize(800, 600)
        
        self.config_file = Path("voice_assistant_config.json")
        self.aliases: Dict[str, str] = {}
        
        self._load_aliases()
        self._setup_ui()
    
    def _load_aliases(self):
        """Load aliases from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.aliases = config.get('command_aliases', {})
            else:
                self.aliases = {}
        except Exception as e:
            print(f"Error loading aliases: {e}")
            self.aliases = {}
    
    def _save_aliases(self):
        """Save aliases back to config file"""
        try:
            # Load current config
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update aliases
            config['command_aliases'] = self.aliases
            
            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save aliases:\n{e}")
            return False
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Title and description
        title = QLabel("Voice Command Aliases")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "Create custom voice command phrases that map to existing commands.\n"
            "Example: 'hit it' → 'play random track' or 'skip' → 'next track'\n"
            "Note: You must restart the voice assistant for changes to take effect."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(description)
        
        # Aliases table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Your Phrase", "Actual Command"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Add new alias section
        add_layout = QHBoxLayout()
        
        add_layout.addWidget(QLabel("Your Phrase:"))
        self.new_alias_input = QLineEdit()
        self.new_alias_input.setPlaceholderText("e.g., 'hit it' or 'skip'")
        self.new_alias_input.returnPressed.connect(self._add_alias)
        add_layout.addWidget(self.new_alias_input)
        
        add_layout.addWidget(QLabel("→"))
        
        add_layout.addWidget(QLabel("Actual Command:"))
        self.new_command_input = QLineEdit()
        self.new_command_input.setPlaceholderText("e.g., 'play random track' or 'next track'")
        self.new_command_input.returnPressed.connect(self._add_alias)
        add_layout.addWidget(self.new_command_input)
        
        self.add_btn = QPushButton("➕ Add")
        self.add_btn.clicked.connect(self._add_alias)
        add_layout.addWidget(self.add_btn)
        
        layout.addLayout(add_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.remove_btn = QPushButton("➖ Remove Selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        button_layout.addWidget(self.remove_btn)
        
        button_layout.addStretch()
        
        self.examples_btn = QPushButton("📖 Show Examples")
        self.examples_btn.clicked.connect(self._show_examples)
        button_layout.addWidget(self.examples_btn)
        
        self.save_btn = QPushButton("💾 Save & Close")
        self.save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Info label
        info = QLabel("💡 Tip: Use simple, distinct phrases to avoid conflicts with existing commands")
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info)
        
        self.setLayout(layout)
        
        # Populate table
        self._populate_table()
    
    def _populate_table(self):
        """Populate table with current aliases"""
        self.table.setRowCount(len(self.aliases))
        
        for row, (alias, command) in enumerate(sorted(self.aliases.items())):
            alias_item = QTableWidgetItem(alias)
            command_item = QTableWidgetItem(command)
            
            self.table.setItem(row, 0, alias_item)
            self.table.setItem(row, 1, command_item)
    
    def _add_alias(self):
        """Add a new alias"""
        alias = self.new_alias_input.text().strip().lower()
        command = self.new_command_input.text().strip().lower()
        
        if not alias or not command:
            QMessageBox.warning(self, "Invalid Input", "Both fields are required")
            return
        
        if alias in self.aliases:
            reply = QMessageBox.question(
                self,
                "Alias Exists",
                f"The alias '{alias}' already exists. Overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # Add alias
        self.aliases[alias] = command
        
        # Clear inputs
        self.new_alias_input.clear()
        self.new_command_input.clear()
        
        # Refresh table
        self._populate_table()
    
    def _remove_selected(self):
        """Remove selected alias"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an alias to remove")
            return
        
        row = selected_rows[0].row()
        alias = self.table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove alias '{alias}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.aliases[alias]
            self._populate_table()
    
    def _show_examples(self):
        """Show example aliases"""
        examples = """<b>Example Command Aliases:</b><br><br>

<b>Music Commands:</b><br>
• "hit it" → "play random track"<br>
• "skip" → "next track"<br>
• "back" → "previous track"<br>
• "shut it off" → "stop playing music"<br>
• "louder" → "volume up"<br>
• "quieter" → "volume down"<br>
• "rock out" → "play genre rock"<br>
<br>

<b>AI Chat Commands:</b><br>
• "ask" → "start chat"<br>
• "done asking" → "stop chat"<br>
<br>

<b>System Commands:</b><br>
• "shut up" → "stop listening"<br>
• "bye" → "stop listening"<br>
• "what's playing" → "music library stats"<br>
<br>

<b>Recording Commands:</b><br>
• "rewind" → "save that"<br>
• "record that" → "save that"<br>
<br>

<b>Tips:</b><br>
• Keep phrases short and distinct<br>
• Use natural language you'd actually say<br>
• Avoid phrases that sound like existing commands<br>
• Test your aliases after restarting the voice assistant
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Command Alias Examples")
        msg.setTextFormat(Qt.RichText)
        msg.setText(examples)
        msg.exec()
    
    def _save_and_close(self):
        """Save aliases and close dialog"""
        if self._save_aliases():
            QMessageBox.information(
                self,
                "Aliases Saved",
                "Command aliases have been saved.\n\n"
                "Restart the voice assistant for changes to take effect."
            )
            self.accept()


def main():
    """Standalone test of the widget"""
    app = QApplication(sys.argv)
    editor = CommandAliasesEditor()
    editor.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
