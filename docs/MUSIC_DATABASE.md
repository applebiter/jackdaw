# Music Database Query System

## Overview

The voice assistant now includes a powerful music database system that lets you search and play music by artist, album, genre, title, or year using voice commands.

## Database Setup

### Migrating Your Music Library

If you have a MySQL music database (like the xiphsound schema):

```bash
# Ensure mysql-connector-python is installed in your venv
source .venv/bin/activate
pip install mysql-connector-python

# Run the migration script
python3 tools/migrate_music_db.py
```

The migration script will:
- Connect to MySQL and export all tracks
- Create a SQLite database (`music_library.sqlite3`)
- Import all metadata (artist, album, genre, title, year, etc.)
- Create indexes for fast searching

### Building Your Own Database

If you don't have an existing database, you can create one from scratch:

1. The schema is in `music_library_schema.sql`
2. Populate it with track metadata from your music files
3. Use a tool like [Mutagen](https://mutagen.readthedocs.io/) to read ID3/Vorbis tags

## Voice Commands

### Database-Driven Playback

| Command | What It Does | Example |
|---------|--------------|---------|
| `play artist` | Prompts for artist name, plays matching tracks | "indigo, play artist" → "Pink Floyd" |
| `play album` | Prompts for album name, plays album tracks in order | "indigo, play album" → "Dark Side of the Moon" |
| `play genre` | Prompts for genre, plays random tracks from that genre | "indigo, play genre" → "Jazz" |
| `play song` | Prompts for song title, plays matching tracks | "indigo, play song" → "Comfortably Numb" |
| `play year` | Prompts for year, plays tracks from that year/decade | "indigo, play year" → "1985" |
| `play some` | General search (genre-focused) | "indigo, play some" → "funk" |

### Library Information

| Command | What It Does |
|---------|--------------|
| `music library stats` | Reports total tracks, artists, albums, and genres |

### Traditional Commands (Still Work)

| Command | What It Does |
|---------|--------------|
| `play random track` | Plays random tracks from filesystem directory |
| `next track` | Skip to next track |
| `stop playing music` | Stop playback completely |
| `pause music` | Pause current track (maintains position) |
| `resume music` | Resume from paused position |
| `volume up` / `volume down` | Adjust volume ±10% |
| `set volume low/medium/high` | Set volume to 30%/60%/90% |
| `what's the volume` | Report current volume level |

## How It Works

### Query System

The `music_query.py` module provides search functions:

```python
from music_query import search_by_artist, search_by_genre

# Find Pink Floyd tracks
tracks = search_by_artist('Pink Floyd', limit=200)

# Find jazz tracks
jazz_tracks = search_by_genre('jazz', limit=100)
```

All searches are:
- **Case-insensitive**: "pink floyd" matches "Pink Floyd"
- **Partial match**: "floyd" matches "Pink Floyd"
- **Randomized results**: Different tracks each time (except albums)

### Playlist Mode

When you use a database query command, the system:

1. Searches the database for matching tracks
2. Creates a custom playlist from results
3. Plays tracks randomly from the playlist
4. Continues playing until you say "stop playing music"

Unlike directory-based playback, playlist mode remembers the search results and only plays tracks that matched your query.

### Database Schema

The `sounds` table includes:

- **Core**: `id`, `uuid`, `location`, `filename`
- **Audio**: `mimetype`, `extension`, `size`, `duration`, `bitrate`, `samplerate`, `channels`
- **Metadata**: `artist`, `albumartist`, `album`, `title`, `genre`, `year`
- **Extended**: `tracknumber`, `discnumber`, `label`, `composer`, `producer`, `engineer`, `comment`
- **Timestamps**: `created`, `modified`

Indexes on: `artist`, `album`, `genre`, `title`, `year`, `albumartist`

## Configuration

No additional configuration needed! The music_player plugin automatically:
- Uses the database if `music_library.sqlite3` exists
- Falls back to directory scanning for "play random track"
- Uses the `library_path` from config for filesystem operations

## Examples

### Play Music by Artist

```
You: "indigo, play artist"
Assistant: "What artist?"
You: "the beatles"
Assistant: "Playing 187 tracks by the beatles"
[Music starts playing random Beatles tracks]
```

### Play an Album

```
You: "indigo, play album"
Assistant: "What album?"
You: "abbey road"
Assistant: "Playing album abbey road"
[Album plays in track order]
```

### Play a Genre

```
You: "indigo, play genre"
Assistant: "What genre?"
You: "reggae"
Assistant: "Playing 43 tracks from reggae"
[Random reggae tracks play]
```

### Quick Genre Playback

```
You: "indigo, play some"
Assistant: "Play some what?"
You: "rock"
Assistant: "Playing 2,347 tracks"
[Random rock tracks play]
```

### Library Stats

```
You: "indigo, music library stats"
Assistant: "Music library has 13,569 tracks, 1,035 artists, 1,204 albums, and 215 genres"
```

## Technical Details

### Database Location

- **File**: `music_library.sqlite3` (in project root)
- **Size**: ~5-10 MB for 13,000+ tracks
- **Status**: Excluded from git (in `.gitignore`)

### Performance

- **Search queries**: < 100ms (indexed fields)
- **Playlist creation**: Instant (in-memory list)
- **No filesystem scanning**: Database queries are much faster than directory traversal

### Matching Algorithm

Searches use SQLite's `LIKE` operator with wildcards:

```sql
WHERE artist LIKE '%pink floyd%'
```

This means:
- "pink" matches "Pink Floyd", "Pinkerton", "Pink Martini"
- "floyd" matches "Pink Floyd"
- "the beatles" matches "The Beatles", "Beatles"

### Future Enhancements

Potential additions:
- **LLM integration**: "play something relaxing" → LLM interprets as genre query
- **Mood-based playback**: Tag tracks with moods, play by feeling
- **Smart shuffle**: Avoid repeating artists/albums too quickly
- **Recently played**: Track listening history
- **Favorites**: Mark and play favorite tracks
- **Collaborative filtering**: "play something like this"

## Troubleshooting

### "No tracks found"

- Check if database exists: `ls -lh music_library.sqlite3`
- Verify search term spelling
- Try broader terms (e.g., "rock" instead of "alternative rock")

### Database not found

```bash
# Re-run migration
python3 tools/migrate_music_db.py

# Or create from schema
sqlite3 music_library.sqlite3 < music_library_schema.sql
```

### Wrong file paths

If your music moved, update the database:

```sql
UPDATE sounds 
SET location = REPLACE(location, '/old/path', '/new/path');
```

## Summary

The music database system gives you precise control over what plays, while maintaining the continuous playback experience. Say "play artist pink floyd" and enjoy hours of uninterrupted Floyd, or "play some jazz" for a chill evening soundtrack.

All powered by voice, no screen required! 🎵
