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
        
        # Main horizontal splitter for table and playlist
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: table and details in vertical splitter
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        left_layout.addWidget(splitter)
        main_splitter.addWidget(left_widget)
        
        # Right side: Playlist panel
        playlist_widget = QWidget()
        playlist_layout = QVBoxLayout(playlist_widget)
        
        playlist_header = QLabel("📋 Current Playlist")
        playlist_header_font = QFont()
        playlist_header_font.setBold(True)
        playlist_header_font.setPointSize(12)
        playlist_header.setFont(playlist_header_font)
        playlist_layout.addWidget(playlist_header)
        
        # Playlist controls
        playlist_btn_layout = QHBoxLayout()
        
        self.add_to_playlist_btn = QPushButton("➕ Add Selected")
        self.add_to_playlist_btn.setToolTip("Add selected tracks from library to playlist")
        self.add_to_playlist_btn.clicked.connect(self.on_add_to_playlist)
        playlist_btn_layout.addWidget(self.add_to_playlist_btn)
        
        self.clear_playlist_btn = QPushButton("🗑 Clear")
        self.clear_playlist_btn.setToolTip("Clear all tracks from playlist")
        self.clear_playlist_btn.clicked.connect(self.on_clear_playlist)
        playlist_btn_layout.addWidget(self.clear_playlist_btn)
        
        playlist_layout.addLayout(playlist_btn_layout)
        
        # Playlist table
        self.playlist_table = QTableWidget()
        self.playlist_table.setColumnCount(4)
        self.playlist_table.setHorizontalHeaderLabels(["#", "Title", "Artist", "Duration"])
        self.playlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.playlist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.playlist_table.setToolTip("Tracks will play in this order (unless shuffle is enabled)")
        playlist_layout.addWidget(self.playlist_table)
        
        # Playlist reorder controls
        reorder_layout = QHBoxLayout()
        
        self.move_up_btn = QPushButton("⬆ Move Up")
        self.move_up_btn.setToolTip("Move selected track up in playlist")
        self.move_up_btn.clicked.connect(self.on_move_up)
        reorder_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("⬇ Move Down")
        self.move_down_btn.setToolTip("Move selected track down in playlist")
        self.move_down_btn.clicked.connect(self.on_move_down)
        reorder_layout.addWidget(self.move_down_btn)
        
        self.remove_from_playlist_btn = QPushButton("➖ Remove")
        self.remove_from_playlist_btn.setToolTip("Remove selected track from playlist")
        self.remove_from_playlist_btn.clicked.connect(self.on_remove_from_playlist)
        reorder_layout.addWidget(self.remove_from_playlist_btn)
        
        playlist_layout.addLayout(reorder_layout)
        
        # Save/Load playlist
        save_load_layout = QHBoxLayout()
        
        self.save_playlist_btn = QPushButton("💾 Save Playlist")
        self.save_playlist_btn.setToolTip("Save current playlist to file")
        self.save_playlist_btn.clicked.connect(self.on_save_playlist)
        save_load_layout.addWidget(self.save_playlist_btn)
        
        self.load_playlist_btn = QPushButton("📂 Load Playlist")
        self.load_playlist_btn.setToolTip("Load playlist from file")
        self.load_playlist_btn.clicked.connect(self.on_load_playlist)
        save_load_layout.addWidget(self.load_playlist_btn)
        
        playlist_layout.addLayout(save_load_layout)
        
        # Playlist count
        self.playlist_count_label = QLabel("0 tracks in playlist")
        playlist_layout.addWidget(self.playlist_count_label)
        
        main_splitter.addWidget(playlist_widget)
        main_splitter.setSizes([900, 400])
        
        layout.addWidget(main_splitter)
        
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
    
    def get_playlist_file_paths(self) -> List[str]:
        """Get file paths from playlist in order"""
        file_paths = []
        for i in range(self.playlist_table.rowCount()):
            item = self.playlist_table.item(i, 1)
            if item and hasattr(item, 'file_path'):
                file_paths.append(item.file_path)
        return file_paths
    
    def update_playlist_display(self):
        """Refresh the playlist table display"""
        self.playlist_table.setRowCount(len(self.playlist))
        
        for i, track in enumerate(self.playlist):
            # Track number
            self.playlist_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # Title (store file path in item data)
            title_item = QTableWidgetItem(track.get('title', 'Unknown'))
            title_item.file_path = track['file_path']
            self.playlist_table.setItem(i, 1, title_item)
            
            # Artist
            self.playlist_table.setItem(i, 2, QTableWidgetItem(track.get('artist', 'Unknown')))
            
            # Duration
            self.playlist_table.setItem(i, 3, QTableWidgetItem(track.get('duration', '')))
        
        self.playlist_count_label.setText(f"{len(self.playlist)} tracks in playlist")
    
    def on_add_to_playlist(self):
        """Add selected tracks to playlist"""
        selected_rows = self.track_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select one or more tracks to add to playlist")
            return
        
        added = 0
        for row in selected_rows:
            title = self.track_table.item(row.row(), 0).text()
            artist = self.track_table.item(row.row(), 1).text()
            duration = self.track_table.item(row.row(), 5).text()
            file_path = self.track_table.item(row.row(), 7).text()
            
            if file_path and Path(file_path).exists():
                self.playlist.append({
                    'title': title,
                    'artist': artist,
                    'duration': duration,
                    'file_path': file_path
                })
                added += 1
        
        self.update_playlist_display()
        self.status_label.setText(f"Added {added} tracks to playlist")
    
    def on_clear_playlist(self):
        """Clear all tracks from playlist"""
        if self.playlist:
            reply = QMessageBox.question(
                self,
                "Clear Playlist",
                f"Remove all {len(self.playlist)} tracks from playlist?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.playlist.clear()
                self.update_playlist_display()
                self.status_label.setText("Playlist cleared")
    
    def on_remove_from_playlist(self):
        """Remove selected track from playlist"""
        selected_rows = self.playlist_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Remove in reverse order to maintain indices
        for row in sorted([r.row() for r in selected_rows], reverse=True):
            if 0 <= row < len(self.playlist):
                del self.playlist[row]
        
        self.update_playlist_display()
    
    def on_move_up(self):
        """Move selected track up in playlist"""
        selected_rows = self.playlist_table.selectionModel().selectedRows()
        if not selected_rows or selected_rows[0].row() == 0:
            return
        
        row = selected_rows[0].row()
        self.playlist[row], self.playlist[row - 1] = self.playlist[row - 1], self.playlist[row]
        self.update_playlist_display()
        self.playlist_table.selectRow(row - 1)
    
    def on_move_down(self):
        """Move selected track down in playlist"""
        selected_rows = self.playlist_table.selectionModel().selectedRows()
        if not selected_rows or selected_rows[0].row() >= len(self.playlist) - 1:
            return
        
        row = selected_rows[0].row()
        self.playlist[row], self.playlist[row + 1] = self.playlist[row + 1], self.playlist[row]
        self.update_playlist_display()
        self.playlist_table.selectRow(row + 1)
    
    def on_save_playlist(self):
        """Save playlist to JSON file"""
        if not self.playlist:
            QMessageBox.information(self, "Empty Playlist", "Playlist is empty, nothing to save")
            return
        
        from PySide6.QtWidgets import QFileDialog
        
        # Create playlists directory if it doesn't exist
        playlists_dir = Path.cwd() / "playlists"
        playlists_dir.mkdir(exist_ok=True)
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Playlist",
            str(playlists_dir / "jackdaw_playlist.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(self.playlist, f, indent=2)
                self.status_label.setText(f"Playlist saved to {Path(filename).name}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save playlist: {e}")
    
    def on_load_playlist(self):
        """Load playlist from JSON file"""
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Playlist",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    loaded_playlist = json.load(f)
                
                # Verify tracks still exist
                valid_tracks = []
                missing = 0
                for track in loaded_playlist:
                    if Path(track['file_path']).exists():
                        valid_tracks.append(track)
                    else:
                        missing += 1
                
                self.playlist = valid_tracks
                self.update_playlist_display()
                
                msg = f"Loaded {len(valid_tracks)} tracks from {Path(filename).name}"
                if missing:
                    msg += f"\n({missing} tracks not found and skipped)"
                self.status_label.setText(msg)
                QMessageBox.information(self, "Playlist Loaded", msg)
                
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load playlist: {e}")
    
    def on_play_local(self):
        """Play playlist or selected tracks on local JACK system"""
        # Use playlist if it exists, otherwise use selected tracks
        if self.playlist:
            file_paths = self.get_playlist_file_paths()
            source = "playlist"
        else:
            file_paths = self.get_selected_file_paths()
            source = "selected tracks"
        
        if not file_paths:
            QMessageBox.warning(
                self, 
                "Nothing to Play", 
                "Please add tracks to playlist or select tracks from library"
            )
            return
        
        # Convert to Path objects
        playlist = [Path(p) for p in file_paths]
        
        # Set shuffle mode
        ogg_jack_player.set_shuffle_mode(self.shuffle_checkbox.isChecked())
        
        # Play playlist
        ogg_jack_player.play_playlist(playlist)
        
        shuffle_text = " (shuffled)" if self.shuffle_checkbox.isChecked() else ""
        self.status_label.setText(f"Playing {len(file_paths)} tracks from {source}{shuffle_text}")
    
    def on_stop_local(self):
        """Stop local playback"""
        ogg_jack_player.stop_playback()
        self.status_label.setText("Local playback stopped")
    
    def on_stream_selected(self):
        """Stream playlist or selected tracks to Icecast2"""
        # Use playlist if it exists, otherwise use selected tracks
        if self.playlist:
            file_paths = self.get_playlist_file_paths()
            source = "playlist"
        else:
            file_paths = self.get_selected_file_paths()
            source = "selected tracks"
        
        if not file_paths:
            QMessageBox.warning(
                self,
                "Nothing to Stream",
                "Please add tracks to playlist or select tracks from library"
            )
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
                
                shuffle_text = " (shuffled)" if self.shuffle_checkbox.isChecked() else ""
                self.status_label.setText(f"Streaming {len(file_paths)} tracks from {source}{shuffle_text}")
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
