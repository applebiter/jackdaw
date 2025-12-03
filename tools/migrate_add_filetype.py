#!/usr/bin/env python3
"""
Database Migration: Add filetype column

Adds the filetype column to existing music_library.sqlite3 databases
and populates it based on existing extension data.
"""

import sqlite3
from pathlib import Path

# Format mapping for human-readable file types
FORMAT_MAP = {
    'ogg': 'Ogg Vorbis',
    'flac': 'FLAC',
    'mp3': 'MP3',
    'opus': 'Opus',
    'm4a': 'AAC/M4A',
    'mp4': 'AAC/MP4',
    'm4b': 'AAC/M4B',
    'm4p': 'AAC/M4P',
}

DB_PATH = Path(__file__).parent.parent / 'music_library.sqlite3'


def migrate_database():
    """Add filetype column and populate it."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if filetype column already exists
    cursor.execute("PRAGMA table_info(sounds)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'filetype' in columns:
        print("Column 'filetype' already exists. Updating values...")
    else:
        print("Adding 'filetype' column to sounds table...")
        cursor.execute("ALTER TABLE sounds ADD COLUMN filetype TEXT")
        conn.commit()
    
    # Populate filetype based on extension
    print("Populating filetype values...")
    cursor.execute("SELECT id, extension FROM sounds WHERE filetype IS NULL OR filetype = ''")
    rows = cursor.fetchall()
    
    updated = 0
    for track_id, extension in rows:
        if extension:
            filetype = FORMAT_MAP.get(extension.lower(), extension.upper())
            cursor.execute("UPDATE sounds SET filetype = ? WHERE id = ?", (filetype, track_id))
            updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"Migration complete! Updated {updated} tracks.")
    print("\nFormat mapping:")
    for ext, fmt in FORMAT_MAP.items():
        print(f"  .{ext} → {fmt}")


if __name__ == '__main__':
    print("Music Library Database Migration")
    print("=" * 50)
    migrate_database()
