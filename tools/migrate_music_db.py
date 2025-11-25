#!/usr/bin/env python3
"""
Migrate music database from MySQL to SQLite.

This script connects to the MySQL xiphsound database and exports
all records from the sounds table into a local SQLite database.
"""

import sqlite3
import mysql.connector
from pathlib import Path

# MySQL connection details
MYSQL_CONFIG = {
    'user': 'sysadmin',
    'password': 'nx8J33aY',
    'host': 'localhost',
    'database': 'xiphsound'
}

# SQLite database path
SQLITE_DB = Path(__file__).parent.parent / 'music_library.sqlite3'

def migrate():
    """Perform the migration from MySQL to SQLite."""
    print(f"[Migrate] Connecting to MySQL database...")
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor(dictionary=True)
    
    print(f"[Migrate] Connecting to SQLite database: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Fetch all records from MySQL
    print(f"[Migrate] Fetching records from MySQL...")
    mysql_cursor.execute("SELECT * FROM sounds")
    rows = mysql_cursor.fetchall()
    print(f"[Migrate] Found {len(rows)} records")
    
    # Insert into SQLite
    print(f"[Migrate] Inserting records into SQLite...")
    inserted = 0
    skipped = 0
    
    for row in rows:
        try:
            sqlite_cursor.execute("""
                INSERT INTO sounds (
                    id, uuid, location, filename, mimetype, extension,
                    size, duration_timecode, duration_milliseconds,
                    bits_per_sample, bitrate, channels, samplerate,
                    beats_per_minute, genre, title, albumartist, album,
                    tracknumber, discnumber, artist, year, label,
                    copyright, composer, producer, engineer, comment,
                    created, modified
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                row['id'], row['uuid'], row['location'], row['filename'],
                row['mimetype'], row['extension'], row['size'],
                row['duration_timecode'], row['duration_milliseconds'],
                row['bits_per_sample'], row['bitrate'], row['channels'],
                row['samplerate'], row['beats_per_minute'], row['genre'],
                row['title'], row['albumartist'], row['album'],
                row['tracknumber'], row['discnumber'], row['artist'],
                row['year'], row['label'], row['copyright'], row['composer'],
                row['producer'], row['engineer'], row['comment'],
                str(row['created']), str(row['modified'])
            ))
            inserted += 1
            if inserted % 1000 == 0:
                print(f"[Migrate] Inserted {inserted} records...")
        except sqlite3.IntegrityError as e:
            skipped += 1
            if skipped <= 5:  # Show first few errors
                print(f"[Migrate] Skipping duplicate: {row.get('filename', 'unknown')} - {e}")
    
    sqlite_conn.commit()
    
    print(f"\n[Migrate] Migration complete!")
    print(f"  - Inserted: {inserted} records")
    print(f"  - Skipped: {skipped} duplicates")
    
    # Verify the import
    sqlite_cursor.execute("SELECT COUNT(*) FROM sounds")
    count = sqlite_cursor.fetchone()[0]
    print(f"  - Total in SQLite: {count} records")
    
    # Close connections
    mysql_cursor.close()
    mysql_conn.close()
    sqlite_conn.close()
    
    print(f"\n[Migrate] Database ready at: {SQLITE_DB}")

if __name__ == '__main__':
    migrate()
