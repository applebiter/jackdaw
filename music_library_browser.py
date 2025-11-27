#!/usr/bin/env python3
"""
Music Library Browser

A GUI application for browsing, searching, and playing music from the
music_library.sqlite3 database. Supports playing locally via JACK or
streaming to Icecast2 server.

Features:
- Paginated table view with sorting
- Search by artist, album, title, genre
- Play locally on JACK system
- Stream to Icecast2 server
- Playlist management
- Track information display
"""

import sys
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit, QLabel,
    QComboBox, QSpinBox, QGroupBox, QSplitter, QTextEdit, QCheckBox,
    QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Import playback functions
import ogg_jack_player
from plugins.icecast_streamer import IcecastStreamerPlugin


class ConfigManager:
    """Simple config manager for the streaming plugin"""
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = json.load(f)
    
    def get(self, *keys, **kwargs):
        """Get nested config value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, {})
            else:
                return kwargs.get('default', None)
        return value if value != {} else kwargs.get('default', None)


class MusicLibraryBrowser(QMainWindow):
    """Main window for music library browser"""
    
    def __init__(self):
        super().__init__()
        
        # Paths
        self.base_path = Path(__file__).parent
        self.db_path = self.base_path / "music_library.sqlite3"
        self.config_path = self.base_path / "voice_assistant_config.json"
        
        # Database connection
        self.db_conn: Optional[sqlite3.Connection] = None
        
        # Streaming plugin
        self.config_manager = ConfigManager(self.config_path)
        self.streamer: Optional[IcecastStreamerPlugin] = None
        
        # Current state
        self.current_page = 0
        self.page_size = 100
        self.total_tracks = 0
        self.current_sort_column = "artist"
        self.current_sort_order = "ASC"
        self.search_text = ""
        self.search_field = "artist"
        
        # Selected tracks for playlist
        self.playlist: List[Dict[str, Any]] = []
        
        self.init_ui()
        self.connect_database()
        self.load_tracks()
        
        # Update streaming status periodically
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_streaming_status)
        self.status_timer.start(2000)  # Every 2 seconds
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Jackdaw Music Library Browser")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Search and filter controls
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.setToolTip("Search for tracks by the selected field (press Enter to search)")
        self.search_input.returnPressed.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        
        search_layout.addWidget(QLabel("Field:"))
        self.search_field_combo = QComboBox()
        self.search_field_combo.addItems(["artist", "album", "title", "genre", "year"])
        self.search_field_combo.setToolTip("Choose which field to search in")
        search_layout.addWidget(self.search_field_combo)
        
        self.search_btn = QPushButton("🔎 Search")
        self.search_btn.setToolTip("Filter tracks by search term")
        self.search_btn.clicked.connect(self.on_search)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✖ Clear")
        self.clear_search_btn.setToolTip("Clear search and show all tracks")
        self.clear_search_btn.clicked.connect(self.on_clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addLayout(search_layout)
        
        # Main splitter for table and details
        splitter = QSplitter(Qt.Vertical)
        
        # Track table
        self.track_table = QTableWidget()
        self.track_table.setColumnCount(8)
        self.track_table.setHorizontalHeaderLabels([
            "Title", "Artist", "Album", "Genre", "Year", "Duration", "BPM", "Path"
        ])
        self.track_table.setToolTip("Click column headers to sort • Ctrl+Click to select multiple • Shift+Click for ranges")
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.track_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.track_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.track_table.setSelectionMode(QTableWidget.MultiSelection)
        self.track_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.track_table.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.track_table)
        
        # Track details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        self.track_details = QTextEdit()
        self.track_details.setReadOnly(True)
        self.track_details.setMaximumHeight(150)
        details_layout.addWidget(QLabel("Track Details:"))
        details_layout.addWidget(self.track_details)
        
        splitter.addWidget(details_widget)
        splitter.setSizes([600, 200])
        
        layout.addWidget(splitter)
        
        # Pagination controls
        page_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.setToolTip("Go to previous page")
        self.prev_btn.clicked.connect(self.on_previous_page)
        page_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1 of 1")
        page_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setToolTip("Go to next page")
        self.next_btn.clicked.connect(self.on_next_page)
        page_layout.addWidget(self.next_btn)
        
        page_layout.addStretch()
        
        page_layout.addWidget(QLabel("Page Size:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(10, 500)
        self.page_size_spin.setValue(100)
        self.page_size_spin.setToolTip("Number of tracks to show per page (10-500)")
        self.page_size_spin.valueChanged.connect(self.on_page_size_changed)
        page_layout.addWidget(self.page_size_spin)
        
        layout.addLayout(page_layout)
        
        # Playback controls
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QVBoxLayout()
        
        # Local JACK playback
        local_layout = QHBoxLayout()
        self.play_local_btn = QPushButton("▶ Play Selected on JACK")
        self.play_local_btn.setToolTip("Play selected tracks through JACK audio system\nTracks play in table order (or shuffled if enabled)")
        self.play_local_btn.clicked.connect(self.on_play_local)
        local_layout.addWidget(self.play_local_btn)
        
        self.stop_local_btn = QPushButton("⏹ Stop Local Playback")
        self.stop_local_btn.setToolTip("Stop currently playing music")
        self.stop_local_btn.clicked.connect(self.on_stop_local)
        local_layout.addWidget(self.stop_local_btn)
        
        self.shuffle_checkbox = QCheckBox("🔀 Shuffle Playback")
        self.shuffle_checkbox.setToolTip("When enabled: play selected tracks in random order\nWhen disabled: play in table order (use column headers to sort)")
        local_layout.addWidget(self.shuffle_checkbox)
        
        playback_layout.addLayout(local_layout)
        
        # Icecast streaming
        stream_layout = QHBoxLayout()
        self.stream_selected_btn = QPushButton("📡 Stream Selected to Icecast")
        self.stream_selected_btn.setToolTip("Start streaming selected tracks to Icecast2 server\nRequires Icecast configuration in voice_assistant_config.json")
        self.stream_selected_btn.clicked.connect(self.on_stream_selected)
        stream_layout.addWidget(self.stream_selected_btn)
        
        self.stop_stream_btn = QPushButton("⏹ Stop Streaming")
        self.stop_stream_btn.setToolTip("Stop broadcasting to Icecast2")
        self.stop_stream_btn.clicked.connect(self.on_stop_stream)
        stream_layout.addWidget(self.stop_stream_btn)
        
        self.stream_status_label = QLabel("Stream: Inactive")
        stream_layout.addWidget(self.stream_status_label)
        
        playback_layout.addLayout(stream_layout)
        
        # Dual mode
        dual_layout = QHBoxLayout()
        self.dual_play_btn = QPushButton("🔊 Play Local + Stream")
        self.dual_play_btn.setToolTip("Play locally AND stream to Icecast simultaneously\nRequires JACK routing: connect ogg_player to both system:playback and IcecastStreamer")
        self.dual_play_btn.clicked.connect(self.on_dual_play)
        dual_layout.addWidget(self.dual_play_btn)
        
        help_label = QLabel("💡 Tip: Use Ctrl+Click to select multiple tracks, Shift+Click for ranges, Click column headers to sort")
        help_label.setWordWrap(True)
        dual_layout.addWidget(help_label)
        dual_layout.addStretch()
        
        playback_layout.addLayout(dual_layout)
        
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    def connect_database(self):
        """Connect to the music library database"""
        if not self.db_path.exists():
            QMessageBox.critical(
                self,
                "Database Not Found",
                f"Music library database not found at:\n{self.db_path}\n\n"
                "Please run the music scanner first:\n"
                "python tools/scan_music_library.py /path/to/music"
            )
            sys.exit(1)
        
        self.db_conn = sqlite3.connect(self.db_path)
        self.db_conn.row_factory = sqlite3.Row
    
    def load_tracks(self):
        """Load tracks from database with current filters and pagination"""
        if not self.db_conn:
            return
        
        cursor = self.db_conn.cursor()
        
        # Build query
        where_clause = ""
        params = []
        
        if self.search_text:
            where_clause = f"WHERE {self.search_field} LIKE ?"
            params.append(f"%{self.search_text}%")
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM sounds {where_clause}"
        cursor.execute(count_query, params)
        self.total_tracks = cursor.fetchone()[0]
        
        # Get paginated results
        offset = self.current_page * self.page_size
        query = f"""
            SELECT id, title, artist, album, genre, year, duration_timecode, 
                   beats_per_minute, location || '/' || filename as file_path
            FROM sounds
            {where_clause}
            ORDER BY {self.current_sort_column} {self.current_sort_order}
            LIMIT ? OFFSET ?
        """
        params.extend([self.page_size, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Update table
        self.track_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.track_table.setItem(i, 0, QTableWidgetItem(row['title'] or ''))
            self.track_table.setItem(i, 1, QTableWidgetItem(row['artist'] or ''))
            self.track_table.setItem(i, 2, QTableWidgetItem(row['album'] or ''))
            self.track_table.setItem(i, 3, QTableWidgetItem(row['genre'] or ''))
            self.track_table.setItem(i, 4, QTableWidgetItem(str(row['year'] or '')))
            self.track_table.setItem(i, 5, QTableWidgetItem(row['duration_timecode'] or ''))
            self.track_table.setItem(i, 6, QTableWidgetItem(str(row['beats_per_minute'] or '')))
            self.track_table.setItem(i, 7, QTableWidgetItem(row['file_path'] or ''))
            
            # Store row ID in first column
            self.track_table.item(i, 0).setData(Qt.UserRole, row['id'])
        
        # Update pagination
        total_pages = (self.total_tracks + self.page_size - 1) // self.page_size
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages} ({self.total_tracks} tracks)")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled((self.current_page + 1) * self.page_size < self.total_tracks)
        
        self.status_label.setText(f"Loaded {len(rows)} tracks")
    
    def on_header_clicked(self, logical_index: int):
        """Handle column header click for sorting"""
        columns = ["title", "artist", "album", "genre", "year", "duration_timecode", "beats_per_minute", "file_path"]
        clicked_column = columns[logical_index]
        
        # Toggle sort order if same column
        if clicked_column == self.current_sort_column:
            self.current_sort_order = "DESC" if self.current_sort_order == "ASC" else "ASC"
        else:
            self.current_sort_column = clicked_column
            self.current_sort_order = "ASC"
        
        self.load_tracks()
    
    def on_search(self):
        """Handle search button click"""
        self.search_text = self.search_input.text().strip()
        self.search_field = self.search_field_combo.currentText()
        self.current_page = 0
        self.load_tracks()
    
    def on_clear_search(self):
        """Clear search and show all tracks"""
        self.search_input.clear()
        self.search_text = ""
        self.current_page = 0
        self.load_tracks()
    
    def on_previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_tracks()
    
    def on_next_page(self):
        """Go to next page"""
        if (self.current_page + 1) * self.page_size < self.total_tracks:
            self.current_page += 1
            self.load_tracks()
    
    def on_page_size_changed(self, value: int):
        """Handle page size change"""
        self.page_size = value
        self.current_page = 0
        self.load_tracks()
    
    def on_selection_changed(self):
        """Handle track selection change"""
        selected_rows = self.track_table.selectionModel().selectedRows()
        
        if len(selected_rows) == 1:
            # Show details for single selection
            row = selected_rows[0].row()
            track_id = self.track_table.item(row, 0).data(Qt.UserRole)
            self.show_track_details(track_id)
        elif len(selected_rows) > 1:
            self.track_details.setPlainText(f"{len(selected_rows)} tracks selected")
        else:
            self.track_details.clear()
    
    def show_track_details(self, track_id: int):
        """Display detailed information for a track"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT * FROM sounds WHERE id = ?", (track_id,))
        row = cursor.fetchone()
        
        if row:
            details = f"""
Title: {row['title'] or 'Unknown'}
Artist: {row['artist'] or 'Unknown'}
Album Artist: {row['albumartist'] or 'N/A'}
Album: {row['album'] or 'Unknown'}
Genre: {row['genre'] or 'N/A'}
Year: {row['year'] or 'N/A'}
Track: {row['tracknumber'] or 'N/A'} / Disc: {row['discnumber'] or 'N/A'}

Duration: {row['duration_timecode']} ({row['duration_milliseconds']} ms)
BPM: {row['beats_per_minute'] or 'N/A'}

Audio Format:
  Sample Rate: {row['samplerate']} Hz
  Channels: {row['channels']}
  Bits per Sample: {row['bits_per_sample']}
  Bitrate: {row['bitrate']} kbps

Composer: {row['composer'] or 'N/A'}
Producer: {row['producer'] or 'N/A'}
Engineer: {row['engineer'] or 'N/A'}
Label: {row['label'] or 'N/A'}

File: {row['location']}/{row['filename']}
Size: {row['size'] or 'N/A'}
            """.strip()
            self.track_details.setPlainText(details)
    
    def get_selected_file_paths(self) -> List[str]:
        """Get file paths of selected tracks"""
        selected_rows = self.track_table.selectionModel().selectedRows()
        file_paths = []
        
        for row in selected_rows:
            path = self.track_table.item(row.row(), 7).text()
            if path and Path(path).exists():
                file_paths.append(path)
        
        return file_paths
    
    def on_play_local(self):
        """Play selected tracks on local JACK system"""
        file_paths = self.get_selected_file_paths()
        
        if not file_paths:
            QMessageBox.warning(self, "No Selection", "Please select one or more tracks to play")
            return
        
        # Convert to Path objects
        playlist = [Path(p) for p in file_paths]
        
        # Set shuffle mode
        ogg_jack_player.set_shuffle_mode(self.shuffle_checkbox.isChecked())
        
        # Play playlist
        ogg_jack_player.play_playlist(playlist)
        
        self.status_label.setText(f"Playing {len(file_paths)} tracks on JACK")
    
    def on_stop_local(self):
        """Stop local playback"""
        ogg_jack_player.stop_playback()
        self.status_label.setText("Local playback stopped")
    
    def on_stream_selected(self):
        """Stream selected tracks to Icecast2"""
        file_paths = self.get_selected_file_paths()
        
        if not file_paths:
            QMessageBox.warning(self, "No Selection", "Please select one or more tracks to stream")
            return
        
        # Initialize streamer if needed
        if not self.streamer:
            self.streamer = IcecastStreamerPlugin(self.config_manager)
        
        # Start streaming
        if not self.streamer.is_streaming:
            result = self.streamer._start_stream()
            if "started" in result.lower():
                # Now play the tracks (they'll be routed to the stream)
                playlist = [Path(p) for p in file_paths]
                ogg_jack_player.set_shuffle_mode(self.shuffle_checkbox.isChecked())
                ogg_jack_player.play_playlist(playlist)
                
                self.status_label.setText(f"Streaming {len(file_paths)} tracks to Icecast")
            else:
                QMessageBox.critical(self, "Stream Error", f"Failed to start stream: {result}")
        else:
            # Already streaming, just update playlist
            playlist = [Path(p) for p in file_paths]
            ogg_jack_player.play_playlist(playlist)
            self.status_label.setText(f"Updated stream playlist with {len(file_paths)} tracks")
    
    def on_stop_stream(self):
        """Stop Icecast streaming"""
        if self.streamer and self.streamer.is_streaming:
            self.streamer._stop_stream()
            self.status_label.setText("Streaming stopped")
    
    def on_dual_play(self):
        """Play locally and stream simultaneously"""
        file_paths = self.get_selected_file_paths()
        
        if not file_paths:
            QMessageBox.warning(self, "No Selection", "Please select one or more tracks to play")
            return
        
        # Start streaming
        if not self.streamer:
            self.streamer = IcecastStreamerPlugin(self.config_manager)
        
        if not self.streamer.is_streaming:
            result = self.streamer._start_stream()
            if "started" not in result.lower():
                QMessageBox.critical(self, "Stream Error", f"Failed to start stream: {result}")
                return
        
        # Play tracks (will output to JACK, which can be routed to both speakers and stream)
        playlist = [Path(p) for p in file_paths]
        ogg_jack_player.set_shuffle_mode(self.shuffle_checkbox.isChecked())
        ogg_jack_player.play_playlist(playlist)
        
        self.status_label.setText(f"Playing {len(file_paths)} tracks locally and streaming")
        QMessageBox.information(
            self,
            "Dual Playback Active",
            "Music is now playing on JACK and streaming to Icecast.\n\n"
            "Use qjackctl to route the audio:\n"
            "• Connect ogg_player outputs to system playback for local audio\n"
            "• Connect ogg_player outputs to IcecastStreamer for streaming\n"
            "• Or connect to both for simultaneous local + stream"
        )
    
    def update_streaming_status(self):
        """Update streaming status label"""
        if self.streamer and self.streamer.is_streaming:
            status = self.streamer._stream_status()
            self.stream_status_label.setText(f"Stream: {status}")
        else:
            self.stream_status_label.setText("Stream: Inactive")
    
    def closeEvent(self, event):
        """Clean up on window close"""
        if self.streamer and self.streamer.is_streaming:
            self.streamer._stop_stream()
        
        if self.db_conn:
            self.db_conn.close()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    browser = MusicLibraryBrowser()
    browser.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
