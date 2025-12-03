#!/usr/bin/env python3
"""
Track Editor Widget

A dialog for editing track metadata with two-way sync:
- Updates the database (music_library.sqlite3)
- Updates the audio file tags directly

Supports common audio formats: MP3, FLAC, OGG, M4A, etc.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QMessageBox, QGroupBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Signal, Qt


class TrackEditorWidget(QDialog):
    """
    Widget for editing track metadata with database and file tag updates
    """
    
    # Signal emitted when track is successfully updated
    track_updated = Signal(int)  # track_id
    
    def __init__(self, track_id: int, db_conn: sqlite3.Connection, db_path: Path, parent=None):
        super().__init__(parent)
        
        self.track_id = track_id
        self.db_conn = db_conn
        self.db_path = db_path
        self.track_data = None
        self.file_path = None
        
        # Make dialog non-modal and keep on top
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle(f"Edit Track #{track_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        self.load_track_data()
        self.init_ui()
        self.populate_fields()
    
    def load_track_data(self):
        """Load track data from database"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT * FROM sounds WHERE id = ?", (self.track_id,))
        row = cursor.fetchone()
        
        if row:
            self.track_data = dict(row)
            self.file_path = Path(self.track_data['location']) / self.track_data['filename']
            
            if not self.file_path.exists():
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Audio file not found:\n{self.file_path}\n\nYou can still edit database values."
                )
        else:
            QMessageBox.critical(self, "Error", f"Track {self.track_id} not found in database")
            self.reject()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # File info header
        header_label = QLabel(f"<b>Editing:</b> {self.file_path.name if self.file_path else 'Unknown'}")
        header_label.setWordWrap(True)
        layout.addWidget(header_label)
        
        path_label = QLabel(f"<i>{self.file_path.parent if self.file_path else 'Unknown'}</i>")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        layout.addSpacing(10)
        
        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        
        # Basic metadata group
        basic_group = QGroupBox("Basic Information")
        basic_form = QFormLayout()
        
        self.title_edit = QLineEdit()
        basic_form.addRow("Title:", self.title_edit)
        
        self.artist_edit = QLineEdit()
        basic_form.addRow("Artist:", self.artist_edit)
        
        self.albumartist_edit = QLineEdit()
        basic_form.addRow("Album Artist:", self.albumartist_edit)
        
        self.album_edit = QLineEdit()
        basic_form.addRow("Album:", self.album_edit)
        
        self.genre_edit = QLineEdit()
        basic_form.addRow("Genre:", self.genre_edit)
        
        self.year_edit = QLineEdit()
        self.year_edit.setMaximumWidth(100)
        basic_form.addRow("Year:", self.year_edit)
        
        basic_group.setLayout(basic_form)
        form_layout.addWidget(basic_group)
        
        # Track/Disc numbers group
        numbers_group = QGroupBox("Track Numbers")
        numbers_form = QFormLayout()
        
        self.tracknumber_edit = QLineEdit()
        self.tracknumber_edit.setMaximumWidth(100)
        numbers_form.addRow("Track Number:", self.tracknumber_edit)
        
        self.discnumber_edit = QLineEdit()
        self.discnumber_edit.setMaximumWidth(100)
        numbers_form.addRow("Disc Number:", self.discnumber_edit)
        
        self.bpm_edit = QLineEdit()
        self.bpm_edit.setMaximumWidth(100)
        numbers_form.addRow("BPM:", self.bpm_edit)
        
        numbers_group.setLayout(numbers_form)
        form_layout.addWidget(numbers_group)
        
        # Credits group
        credits_group = QGroupBox("Credits")
        credits_form = QFormLayout()
        
        self.composer_edit = QLineEdit()
        credits_form.addRow("Composer:", self.composer_edit)
        
        self.producer_edit = QLineEdit()
        credits_form.addRow("Producer:", self.producer_edit)
        
        self.engineer_edit = QLineEdit()
        credits_form.addRow("Engineer:", self.engineer_edit)
        
        self.label_edit = QLineEdit()
        credits_form.addRow("Label:", self.label_edit)
        
        credits_group.setLayout(credits_form)
        form_layout.addWidget(credits_group)
        
        # Comments group
        comments_group = QGroupBox("Comments")
        comments_layout = QVBoxLayout()
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setMaximumHeight(100)
        comments_layout.addWidget(self.comment_edit)
        
        comments_group.setLayout(comments_layout)
        form_layout.addWidget(comments_group)
        
        # Read-only metadata info
        readonly_group = QGroupBox("File Information (Read-Only)")
        readonly_form = QFormLayout()
        
        self.duration_label = QLabel()
        readonly_form.addRow("Duration:", self.duration_label)
        
        self.format_label = QLabel()
        readonly_form.addRow("Format:", self.format_label)
        
        self.samplerate_label = QLabel()
        readonly_form.addRow("Sample Rate:", self.samplerate_label)
        
        self.channels_label = QLabel()
        readonly_form.addRow("Channels:", self.channels_label)
        
        self.bitrate_label = QLabel()
        readonly_form.addRow("Bitrate:", self.bitrate_label)
        
        self.filesize_label = QLabel()
        readonly_form.addRow("File Size:", self.filesize_label)
        
        readonly_group.setLayout(readonly_form)
        form_layout.addWidget(readonly_group)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setToolTip("Save changes to database and audio file tags")
        self.save_btn.clicked.connect(self.on_save)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.setToolTip("Close without saving")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
    
    def populate_fields(self):
        """Populate form fields with track data"""
        if not self.track_data:
            return
        
        # Editable fields
        self.title_edit.setText(self.track_data.get('title') or '')
        self.artist_edit.setText(self.track_data.get('artist') or '')
        self.albumartist_edit.setText(self.track_data.get('albumartist') or '')
        self.album_edit.setText(self.track_data.get('album') or '')
        self.genre_edit.setText(self.track_data.get('genre') or '')
        self.year_edit.setText(str(self.track_data.get('year') or ''))
        self.tracknumber_edit.setText(str(self.track_data.get('tracknumber') or ''))
        self.discnumber_edit.setText(str(self.track_data.get('discnumber') or ''))
        self.bpm_edit.setText(str(self.track_data.get('beats_per_minute') or ''))
        self.composer_edit.setText(self.track_data.get('composer') or '')
        self.producer_edit.setText(self.track_data.get('producer') or '')
        self.engineer_edit.setText(self.track_data.get('engineer') or '')
        self.label_edit.setText(self.track_data.get('label') or '')
        self.comment_edit.setPlainText(self.track_data.get('comment') or '')
        
        # Read-only info
        self.duration_label.setText(f"{self.track_data.get('duration_timecode')} ({self.track_data.get('duration_milliseconds')} ms)")
        self.format_label.setText(self.track_data.get('filetype') or 'Unknown')
        self.samplerate_label.setText(f"{self.track_data.get('samplerate')} Hz")
        self.channels_label.setText(str(self.track_data.get('channels')))
        self.bitrate_label.setText(f"{self.track_data.get('bitrate')} kbps")
        self.filesize_label.setText(self.track_data.get('size') or 'Unknown')
    
    def on_save(self):
        """Save changes to database and file"""
        try:
            # Collect updated values
            updated_data = {
                'title': self.title_edit.text().strip() or None,
                'artist': self.artist_edit.text().strip() or None,
                'albumartist': self.albumartist_edit.text().strip() or None,
                'album': self.album_edit.text().strip() or None,
                'genre': self.genre_edit.text().strip() or None,
                'year': int(self.year_edit.text()) if self.year_edit.text().strip() else None,
                'tracknumber': int(self.tracknumber_edit.text()) if self.tracknumber_edit.text().strip() else None,
                'discnumber': int(self.discnumber_edit.text()) if self.discnumber_edit.text().strip() else None,
                'beats_per_minute': int(self.bpm_edit.text()) if self.bpm_edit.text().strip() else None,
                'composer': self.composer_edit.text().strip() or None,
                'producer': self.producer_edit.text().strip() or None,
                'engineer': self.engineer_edit.text().strip() or None,
                'label': self.label_edit.text().strip() or None,
                'comment': self.comment_edit.toPlainText().strip() or None,
            }
            
            # Update database
            self.update_database(updated_data)
            
            # Update file tags (if file exists)
            if self.file_path and self.file_path.exists():
                self.update_file_tags(updated_data)
            
            self.status_label.setText("✓ Changes saved successfully!")
            self.status_label.setStyleSheet("color: green;")
            
            # Emit signal to refresh parent
            self.track_updated.emit(self.track_id)
            
            # Close dialog after short delay
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self.accept)
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", f"Please check your input:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save changes:\n{e}")
            import traceback
            traceback.print_exc()
    
    def update_database(self, data: dict):
        """Update track metadata in database"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
            UPDATE sounds SET
                title = ?,
                artist = ?,
                albumartist = ?,
                album = ?,
                genre = ?,
                year = ?,
                tracknumber = ?,
                discnumber = ?,
                beats_per_minute = ?,
                composer = ?,
                producer = ?,
                engineer = ?,
                label = ?,
                comment = ?
            WHERE id = ?
        """, (
            data['title'],
            data['artist'],
            data['albumartist'],
            data['album'],
            data['genre'],
            data['year'],
            data['tracknumber'],
            data['discnumber'],
            data['beats_per_minute'],
            data['composer'],
            data['producer'],
            data['engineer'],
            data['label'],
            data['comment'],
            self.track_id
        ))
        
        self.db_conn.commit()
        print(f"[TrackEditor] Updated database for track {self.track_id}")
    
    def update_file_tags(self, data: dict):
        """Update audio file tags using mutagen"""
        try:
            from mutagen import File
            from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TCON, TDRC, TRCK, TPOS, TBPM, TCOM, TPUB, COMM
            from mutagen.flac import FLAC
            from mutagen.oggvorbis import OggVorbis
            from mutagen.mp4 import MP4
            
            audio = File(str(self.file_path))
            
            if audio is None:
                raise Exception("Could not open audio file")
            
            # Determine file type and update accordingly
            file_ext = self.file_path.suffix.lower()
            
            if file_ext == '.mp3':
                self._update_mp3_tags(audio, data)
            elif file_ext == '.flac':
                self._update_flac_tags(audio, data)
            elif file_ext in ['.ogg', '.oga']:
                self._update_ogg_tags(audio, data)
            elif file_ext in ['.m4a', '.mp4', '.m4b', '.m4p']:
                self._update_mp4_tags(audio, data)
            else:
                raise Exception(f"Unsupported file format: {file_ext}")
            
            audio.save()
            print(f"[TrackEditor] Updated file tags for {self.file_path.name}")
            
        except ImportError:
            QMessageBox.warning(
                self,
                "Missing Dependency",
                "mutagen library not installed. File tags not updated.\n\n"
                "Install with: pip install mutagen"
            )
        except Exception as e:
            raise Exception(f"Failed to update file tags: {e}")
    
    def _update_mp3_tags(self, audio, data: dict):
        """Update ID3 tags for MP3 files"""
        from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TCON, TDRC, TRCK, TPOS, TBPM, TCOM, TPUB, COMM
        
        # Ensure ID3 tag exists
        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        
        # Update tags
        if data['title']:
            tags['TIT2'] = TIT2(encoding=3, text=data['title'])
        if data['artist']:
            tags['TPE1'] = TPE1(encoding=3, text=data['artist'])
        if data['albumartist']:
            tags['TPE2'] = TPE2(encoding=3, text=data['albumartist'])
        if data['album']:
            tags['TALB'] = TALB(encoding=3, text=data['album'])
        if data['genre']:
            tags['TCON'] = TCON(encoding=3, text=data['genre'])
        if data['year']:
            tags['TDRC'] = TDRC(encoding=3, text=str(data['year']))
        if data['tracknumber']:
            tags['TRCK'] = TRCK(encoding=3, text=str(data['tracknumber']))
        if data['discnumber']:
            tags['TPOS'] = TPOS(encoding=3, text=str(data['discnumber']))
        if data['beats_per_minute']:
            tags['TBPM'] = TBPM(encoding=3, text=str(data['beats_per_minute']))
        if data['composer']:
            tags['TCOM'] = TCOM(encoding=3, text=data['composer'])
        if data['label']:
            tags['TPUB'] = TPUB(encoding=3, text=data['label'])
        if data['comment']:
            tags['COMM'] = COMM(encoding=3, lang='eng', desc='', text=data['comment'])
    
    def _update_flac_tags(self, audio, data: dict):
        """Update Vorbis comments for FLAC files"""
        # FLAC uses Vorbis comments (key-value pairs)
        tag_map = {
            'title': 'TITLE',
            'artist': 'ARTIST',
            'albumartist': 'ALBUMARTIST',
            'album': 'ALBUM',
            'genre': 'GENRE',
            'year': 'DATE',
            'tracknumber': 'TRACKNUMBER',
            'discnumber': 'DISCNUMBER',
            'beats_per_minute': 'BPM',
            'composer': 'COMPOSER',
            'producer': 'PRODUCER',
            'engineer': 'ENGINEER',
            'label': 'LABEL',
            'comment': 'COMMENT',
        }
        
        for key, tag in tag_map.items():
            if data[key] is not None:
                audio[tag] = str(data[key])
    
    def _update_ogg_tags(self, audio, data: dict):
        """Update Vorbis comments for OGG files"""
        # Same as FLAC
        self._update_flac_tags(audio, data)
    
    def _update_mp4_tags(self, audio, data: dict):
        """Update tags for MP4/M4A files"""
        # MP4 uses different tag names
        tag_map = {
            'title': '\xa9nam',
            'artist': '\xa9ART',
            'albumartist': 'aART',
            'album': '\xa9alb',
            'genre': '\xa9gen',
            'year': '\xa9day',
            'composer': '\xa9wrt',
            'comment': '\xa9cmt',
        }
        
        for key, tag in tag_map.items():
            if data[key] is not None:
                audio[tag] = str(data[key])
        
        # Track/disc numbers use tuples
        if data['tracknumber']:
            audio['trkn'] = [(data['tracknumber'], 0)]
        if data['discnumber']:
            audio['disk'] = [(data['discnumber'], 0)]
        
        # BPM is integer
        if data['beats_per_minute']:
            audio['tmpo'] = [data['beats_per_minute']]
