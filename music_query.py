#!/usr/bin/env python3
"""
Music Library Query Module

Provides functions to search the music library database by artist, album,
genre, title, and other criteria. Returns file paths for playback.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
import random


# Database path
DB_PATH = Path(__file__).parent / 'music_library.sqlite3'


def get_db_connection():
    """Get a connection to the music library database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Music library database not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def get_full_path(row: Dict[str, Any]) -> str:
    """Construct full file path from location and filename."""
    location = row.get('location', '')
    filename = row.get('filename', '')
    return f"{location}/{filename}"


def search_by_artist(artist: str, limit: int = 100) -> List[str]:
    """
    Search for tracks by artist name (case-insensitive, partial match).
    
    Args:
        artist: Artist name to search for
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE artist LIKE ? OR albumartist LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (f'%{artist}%', f'%{artist}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def search_by_album(album: str, limit: int = 100) -> List[str]:
    """
    Search for tracks by album name (case-insensitive, partial match).
    
    Args:
        album: Album name to search for
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE album LIKE ?
        ORDER BY tracknumber, filename
        LIMIT ?
    """, (f'%{album}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def search_by_genre(genre: str, limit: int = 100) -> List[str]:
    """
    Search for tracks by genre (case-insensitive, partial match).
    
    Args:
        genre: Genre to search for
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE genre LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (f'%{genre}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def search_by_title(title: str, limit: int = 100) -> List[str]:
    """
    Search for tracks by title (case-insensitive, partial match).
    
    Args:
        title: Song title to search for
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE title LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (f'%{title}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def search_by_year(year: str, limit: int = 100) -> List[str]:
    """
    Search for tracks by year (partial match, e.g., "198" for 1980s).
    
    Args:
        year: Year or year range to search for
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE year LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (f'%{year}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def get_random_tracks(limit: int = 100) -> List[str]:
    """
    Get random tracks from the entire library.
    
    Args:
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        ORDER BY RANDOM()
        LIMIT ?
    """, (limit,))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def get_track_info(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific track by file path.
    
    Args:
        filepath: Full path to the music file
    
    Returns:
        Dictionary with track metadata, or None if not found
    """
    # Split path into location and filename
    path_obj = Path(filepath)
    location = str(path_obj.parent)
    filename = path_obj.name
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    
    cursor.execute("""
        SELECT * FROM sounds
        WHERE location = ? AND filename = ?
    """, (location, filename))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def search_tracks(query: str, limit: int = 100) -> List[str]:
    """
    Search across artist, album, title, and genre (case-insensitive).
    
    Args:
        query: Search term to match
        limit: Maximum number of results
    
    Returns:
        List of file paths
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT location, filename FROM sounds
        WHERE artist LIKE ?
           OR albumartist LIKE ?
           OR album LIKE ?
           OR title LIKE ?
           OR genre LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
    
    results = [f"{row[0]}/{row[1]}" for row in cursor.fetchall()]
    conn.close()
    return results


def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the music library.
    
    Returns:
        Dictionary with stats (total tracks, artists, albums, genres)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) FROM sounds")
    stats['total_tracks'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT artist) FROM sounds WHERE artist IS NOT NULL")
    stats['total_artists'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT album) FROM sounds WHERE album IS NOT NULL")
    stats['total_albums'] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT genre) FROM sounds WHERE genre IS NOT NULL")
    stats['total_genres'] = cursor.fetchone()[0]
    
    conn.close()
    return stats


if __name__ == '__main__':
    # Test queries
    print("=== Music Library Query Tests ===\n")
    
    stats = get_database_stats()
    print(f"Library Stats:")
    print(f"  Total Tracks: {stats['total_tracks']}")
    print(f"  Total Artists: {stats['total_artists']}")
    print(f"  Total Albums: {stats['total_albums']}")
    print(f"  Total Genres: {stats['total_genres']}")
    print()
    
    print("Searching for 'Pink Floyd'...")
    results = search_by_artist('Pink Floyd', limit=5)
    for i, path in enumerate(results, 1):
        print(f"  {i}. {Path(path).name}")
    print()
    
    print("Searching for genre 'Jazz'...")
    results = search_by_genre('Jazz', limit=5)
    for i, path in enumerate(results, 1):
        print(f"  {i}. {Path(path).name}")
    print()
    
    print("Searching for year '1985'...")
    results = search_by_year('1985', limit=5)
    for i, path in enumerate(results, 1):
        print(f"  {i}. {Path(path).name}")
