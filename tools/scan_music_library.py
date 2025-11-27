#!/usr/bin/env python3
"""
Music Library Scanner

Recursively scans a directory for audio files (OGG, FLAC, MP3, Opus), extracts metadata,
analyzes audio properties (including BPM), and populates the music database.

This script replicates the functionality of:
- sox: Audio format info (sample rate, channels, bits per sample)
- mediainfo: Duration, bitrate, file properties
- bpm-tools: Beats per minute analysis
"""

import os
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# Audio metadata and analysis
from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp3 import MP3
from mutagen.oggopus import OggOpus
import soundfile as sf
import librosa


# Database path
DB_PATH = Path(__file__).parent.parent / 'music_library.sqlite3'
SCHEMA_PATH = Path(__file__).parent.parent / 'music_library_schema.sql'


def init_database():
    """Initialize the database with the schema if it doesn't exist."""
    # Create database file if it doesn't exist
    if not DB_PATH.exists():
        print(f"Creating database at {DB_PATH}")
        DB_PATH.touch()
    
    # Load and execute schema
    if SCHEMA_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, 'r') as f:
            schema = f.read()
        conn.executescript(schema)
        conn.commit()
        conn.close()
        print("Database initialized with schema")
    else:
        print(f"Warning: Schema file not found at {SCHEMA_PATH}")


def get_db_connection():
    """Get a connection to the music library database."""
    if not DB_PATH.exists():
        init_database()
    return sqlite3.connect(DB_PATH)


def extract_audio_properties(filepath: Path) -> Dict[str, Any]:
    """
    Extract audio properties using soundfile (replaces sox functionality).
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Dictionary with audio properties
    """
    try:
        with sf.SoundFile(str(filepath)) as audio:
            duration_seconds = len(audio) / audio.samplerate
            duration_ms = int(duration_seconds * 1000)
            
            # Format duration as HH:MM:SS
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            seconds = int(duration_seconds % 60)
            duration_timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Extract bit depth from subtype (e.g., PCM_16, PCM_24, PCM_32, FLOAT, DOUBLE)
            bits_per_sample = None
            subtype = audio.subtype
            if '_' in subtype:
                # Format like PCM_16, PCM_24, etc.
                try:
                    bits_per_sample = subtype.split('_')[1]
                    if bits_per_sample.isdigit():
                        bits_per_sample = str(bits_per_sample)
                    else:
                        bits_per_sample = None
                except:
                    pass
            elif subtype == 'FLOAT':
                bits_per_sample = '32'
            elif subtype == 'DOUBLE':
                bits_per_sample = '64'
            # Compressed formats (VORBIS, OPUS, etc.) don't have bit depth
            
            return {
                'duration_timecode': duration_timecode,
                'duration_milliseconds': str(duration_ms),
                'samplerate': str(audio.samplerate),
                'channels': str(audio.channels),
                'bits_per_sample': bits_per_sample,
            }
    except Exception as e:
        print(f"[Scanner] Error extracting audio properties from {filepath}: {e}")
        return {}


def extract_metadata(filepath: Path) -> Dict[str, Any]:
    """
    Extract metadata tags using mutagen (replaces mediainfo for tags).
    
    Args:
        filepath: Path to audio file
        
    Returns:
        Dictionary with metadata tags
    """
    try:
        audio = MutagenFile(str(filepath))
        if audio is None:
            return {}
        
        # Map common tag names to our schema
        metadata = {}
        
        # Helper to get first value from possibly list-valued tags
        def get_tag(tags, *keys):
            for key in keys:
                value = tags.get(key)
                if value:
                    return value[0] if isinstance(value, list) else str(value)
            return None
        
        if isinstance(audio, OggVorbis):
            # OGG Vorbis tags
            metadata['title'] = get_tag(audio, 'title', 'TITLE')
            metadata['artist'] = get_tag(audio, 'artist', 'ARTIST')
            metadata['albumartist'] = get_tag(audio, 'albumartist', 'ALBUMARTIST', 'album artist')
            metadata['album'] = get_tag(audio, 'album', 'ALBUM')
            metadata['genre'] = get_tag(audio, 'genre', 'GENRE')
            metadata['year'] = get_tag(audio, 'date', 'DATE', 'year', 'YEAR')
            metadata['tracknumber'] = get_tag(audio, 'tracknumber', 'TRACKNUMBER')
            metadata['discnumber'] = get_tag(audio, 'discnumber', 'DISCNUMBER')
            metadata['label'] = get_tag(audio, 'label', 'LABEL', 'organization', 'ORGANIZATION')
            metadata['copyright'] = get_tag(audio, 'copyright', 'COPYRIGHT')
            metadata['composer'] = get_tag(audio, 'composer', 'COMPOSER')
            metadata['producer'] = get_tag(audio, 'producer', 'PRODUCER')
            metadata['engineer'] = get_tag(audio, 'engineer', 'ENGINEER')
            metadata['comment'] = get_tag(audio, 'comment', 'COMMENT', 'description', 'DESCRIPTION')
            
        elif isinstance(audio, FLAC):
            # FLAC tags (similar to OGG)
            metadata['title'] = get_tag(audio, 'title', 'TITLE')
            metadata['artist'] = get_tag(audio, 'artist', 'ARTIST')
            metadata['albumartist'] = get_tag(audio, 'albumartist', 'ALBUMARTIST', 'album artist')
            metadata['album'] = get_tag(audio, 'album', 'ALBUM')
            metadata['genre'] = get_tag(audio, 'genre', 'GENRE')
            metadata['year'] = get_tag(audio, 'date', 'DATE', 'year', 'YEAR')
            metadata['tracknumber'] = get_tag(audio, 'tracknumber', 'TRACKNUMBER')
            metadata['discnumber'] = get_tag(audio, 'discnumber', 'DISCNUMBER')
            metadata['label'] = get_tag(audio, 'label', 'LABEL', 'organization', 'ORGANIZATION')
            metadata['copyright'] = get_tag(audio, 'copyright', 'COPYRIGHT')
            metadata['composer'] = get_tag(audio, 'composer', 'COMPOSER')
            metadata['producer'] = get_tag(audio, 'producer', 'PRODUCER')
            metadata['engineer'] = get_tag(audio, 'engineer', 'ENGINEER')
            metadata['comment'] = get_tag(audio, 'comment', 'COMMENT', 'description', 'DESCRIPTION')
        
        # Calculate bitrate if available
        if hasattr(audio.info, 'bitrate'):
            metadata['bitrate'] = str(audio.info.bitrate)
        
        # Clean up year field (extract just the year if date format)
        if metadata.get('year'):
            year = metadata['year']
            if '-' in year:  # ISO date format
                metadata['year'] = year.split('-')[0]
        
        return metadata
        
    except Exception as e:
        print(f"[Scanner] Error extracting metadata from {filepath}: {e}")
        return {}


def analyze_bpm(filepath: Path) -> Optional[str]:
    """
    Analyze beats per minute using librosa (replaces bpm-tools).
    
    Args:
        filepath: Path to audio file
        
    Returns:
        BPM as string, or None if analysis fails
    """
    try:
        # Load audio file
        y, sr = librosa.load(str(filepath), sr=None, duration=120)  # Analyze first 2 minutes
        
        # Estimate tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        
        # Convert numpy array to Python float if needed (fixes deprecation warning)
        if hasattr(tempo, 'item'):
            tempo = tempo.item()
        
        return str(int(tempo))
        
    except Exception as e:
        print(f"[Scanner] Error analyzing BPM for {filepath}: {e}")
        return None


def process_audio_file(filepath: Path, root_dir: Path, analyze_bpm_flag: bool = False) -> Optional[Dict[str, Any]]:
    """
    Process a single audio file and extract all metadata.
    
    Args:
        filepath: Path to audio file
        root_dir: Root directory being scanned (for relative path)
        analyze_bpm_flag: Whether to perform BPM analysis (slow)
        
    Returns:
        Dictionary with all file data ready for database insertion
    """
    try:
        # Basic file info
        file_stat = filepath.stat()
        file_size = str(file_stat.st_size)
        
        # Determine location (parent directory) and filename
        location = str(filepath.parent)
        filename = filepath.name
        
        # Extension and mimetype
        extension = filepath.suffix.lower().lstrip('.')
        if extension == 'ogg':
            mimetype = 'audio/ogg'
        elif extension == 'flac':
            mimetype = 'audio/flac'
        else:
            mimetype = f'audio/{extension}'
        
        # Extract audio properties
        audio_props = extract_audio_properties(filepath)
        
        # Extract metadata tags
        metadata = extract_metadata(filepath)
        
        # BPM analysis (optional, slow)
        bpm = None
        if analyze_bpm_flag:
            print(f"[Scanner] Analyzing BPM for {filename}...")
            bpm = analyze_bpm(filepath)
        
        # Timestamps
        created_time = datetime.fromtimestamp(file_stat.st_ctime)
        modified_time = datetime.fromtimestamp(file_stat.st_mtime)
        
        # Combine all data
        data = {
            'uuid': str(uuid.uuid4()),
            'location': location,
            'filename': filename,
            'mimetype': mimetype,
            'extension': extension,
            'size': file_size,
            'duration_timecode': audio_props.get('duration_timecode'),
            'duration_milliseconds': audio_props.get('duration_milliseconds'),
            'bits_per_sample': audio_props.get('bits_per_sample'),
            'bitrate': metadata.get('bitrate'),
            'channels': audio_props.get('channels'),
            'samplerate': audio_props.get('samplerate'),
            'beats_per_minute': bpm,
            'genre': metadata.get('genre'),
            'title': metadata.get('title'),
            'albumartist': metadata.get('albumartist'),
            'album': metadata.get('album'),
            'tracknumber': metadata.get('tracknumber'),
            'discnumber': metadata.get('discnumber'),
            'artist': metadata.get('artist'),
            'year': metadata.get('year'),
            'label': metadata.get('label'),
            'copyright': metadata.get('copyright'),
            'composer': metadata.get('composer'),
            'producer': metadata.get('producer'),
            'engineer': metadata.get('engineer'),
            'comment': metadata.get('comment'),
            'created': created_time.isoformat(sep=' ', timespec='seconds'),
            'modified': modified_time.isoformat(sep=' ', timespec='seconds'),
        }
        
        return data
        
    except Exception as e:
        print(f"[Scanner] Error processing {filepath}: {e}")
        return None


def insert_track(conn: sqlite3.Connection, data: Dict[str, Any]) -> bool:
    """
    Insert track data into database.
    
    Args:
        conn: Database connection
        data: Track data dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sounds (
                uuid, location, filename, mimetype, extension,
                size, duration_timecode, duration_milliseconds,
                bits_per_sample, bitrate, channels, samplerate,
                beats_per_minute, genre, title, albumartist, album,
                tracknumber, discnumber, artist, year, label,
                copyright, composer, producer, engineer, comment,
                created, modified
            ) VALUES (
                :uuid, :location, :filename, :mimetype, :extension,
                :size, :duration_timecode, :duration_milliseconds,
                :bits_per_sample, :bitrate, :channels, :samplerate,
                :beats_per_minute, :genre, :title, :albumartist, :album,
                :tracknumber, :discnumber, :artist, :year, :label,
                :copyright, :composer, :producer, :engineer, :comment,
                :created, :modified
            )
        """, data)
        return True
    except sqlite3.IntegrityError as e:
        # File already exists in database
        print(f"[Scanner] Skipping duplicate: {data['filename']} - {e}")
        return False
    except Exception as e:
        print(f"[Scanner] Error inserting {data['filename']}: {e}")
        return False


def scan_directory(root_dir: str, analyze_bpm: bool = False, update_existing: bool = False):
    """
    Recursively scan directory for audio files and populate database.
    
    Args:
        root_dir: Root directory to scan
        analyze_bpm: Whether to perform BPM analysis (slow)
        update_existing: Whether to update existing entries (by location+filename)
    """
    root_path = Path(root_dir).expanduser().resolve()
    
    if not root_path.exists():
        print(f"[Scanner] Directory does not exist: {root_path}")
        return
    
    # Initialize database if needed
    init_database()
    
    print(f"[Scanner] Scanning directory: {root_path}")
    print(f"[Scanner] BPM analysis: {'enabled' if analyze_bpm else 'disabled'}")
    print(f"[Scanner] Update existing: {'yes' if update_existing else 'no'}")
    print()
    
    # Collect all audio files (Xiph.org formats + MP3)
    audio_files = []
    extensions = [
        '*.ogg', '*.OGG',      # Ogg Vorbis
        '*.opus', '*.OPUS',    # Opus
        '*.flac', '*.FLAC',    # FLAC
        '*.mp3', '*.MP3'       # MP3
    ]
    for ext in extensions:
        audio_files.extend(root_path.rglob(ext))
    
    total_files = len(audio_files)
    print(f"[Scanner] Found {total_files} audio files")
    print()
    
    if total_files == 0:
        return
    
    # Connect to database
    conn = get_db_connection()
    
    # Process files
    processed = 0
    inserted = 0
    skipped = 0
    errors = 0
    
    for i, filepath in enumerate(audio_files, 1):
        print(f"[Scanner] Processing ({i}/{total_files}): {filepath.name}")
        
        data = process_audio_file(filepath, root_path, analyze_bpm_flag=analyze_bpm)
        
        if data:
            if insert_track(conn, data):
                inserted += 1
            else:
                skipped += 1
        else:
            errors += 1
        
        processed += 1
        
        # Commit every 100 files
        if processed % 100 == 0:
            conn.commit()
            print(f"[Scanner] Progress: {processed}/{total_files} processed, {inserted} inserted, {skipped} skipped, {errors} errors")
            print()
    
    # Final commit
    conn.commit()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"[Scanner] Scan complete!")
    print(f"  Total files found: {total_files}")
    print(f"  Processed: {processed}")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"  Errors: {errors}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Scan music directory and populate database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scan (no BPM analysis)
  python tools/scan_music_library.py /path/to/music
  
  # Scan with BPM analysis (slow!)
  python tools/scan_music_library.py /path/to/music --bpm
  
  # Update existing entries
  python tools/scan_music_library.py /path/to/music --update
        """
    )
    
    parser.add_argument(
        'directory',
        help='Root directory to scan for music files'
    )
    
    parser.add_argument(
        '--bpm',
        action='store_true',
        help='Analyze beats per minute (slow, adds ~2-5 seconds per track)'
    )
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update existing database entries (not yet implemented)'
    )
    
    args = parser.parse_args()
    
    scan_directory(args.directory, analyze_bpm=args.bpm, update_existing=args.update)


if __name__ == '__main__':
    main()
