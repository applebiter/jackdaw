# Music Database Query System

## Overview

The voice assistant now includes a powerful music database system that lets you search and play music by artist, album, genre, title, or year using voice commands.

## Database Setup

### Option 1: Scan Your Music Directory (Recommended)

The easiest way to build your database is to scan your existing music collection:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Basic scan (fast, no BPM analysis)
python tools/scan_music_library.py /path/to/your/music

# With BPM analysis (slower, adds 2-5 seconds per track)
python tools/scan_music_library.py /path/to/your/music --bpm
```

The scanner will:
- Recursively find all audio files: `.ogg` (Vorbis), `.opus`, `.flac`, `.mp3`
- Extract metadata tags (artist, album, title, genre, year, etc.)
- Analyze audio properties (duration, sample rate, bit depth, channels)
- Optionally analyze beats per minute (BPM)
- Insert everything into `music_library.sqlite3`
- Skip duplicates automatically

**Supported Formats:**
- **Ogg Vorbis** (.ogg) - Open, lossy compression
- **Opus** (.opus) - Modern, efficient open codec
- **FLAC** (.flac) - Lossless open compression
- **MP3** (.mp3) - Ubiquitous lossy format

**What it extracts:**
- **Audio format**: sample rate, channels, bits per sample, bitrate
- **Duration**: in both timecode (HH:MM:SS) and milliseconds
- **Tags**: title, artist, album artist, album, genre, year
- **Track info**: track number, disc number
- **Credits**: composer, producer, engineer, label, copyright
- **BPM**: beats per minute (optional, requires `--bpm` flag)

**Performance:**
- Without BPM: ~0.1-0.5 seconds per track
- With BPM: ~2-5 seconds per track
- Example: 13,000 tracks without BPM takes ~30-60 minutes

### Option 2: Build Your Own Database

If you need a custom solution:

1. The schema is in `music_library_schema.sql`
2. Create the database: `sqlite3 music_library.sqlite3 < music_library_schema.sql`
3. Populate it with your own scripts or tools

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

### Playback Control

| Command | What It Does |
|---------|--------------|
| `play random track` | Plays random tracks from filesystem directory |
| `next track` | Skip to next track (sequential or shuffle based on mode) |
| `stop playing music` | Stop playback completely |
| `pause music` | Pause current track (maintains position) |
| `resume music` | Resume from paused position |

### Playback Mode (Sequential vs. Shuffle)

By default, playlists play **sequentially** (in order). When you play an album, tracks play in album order.

| Command | What It Does |
|---------|--------------|
| `shuffle on` | Enable random/shuffle mode for playlists |
| `shuffle off` | Enable sequential mode (default - plays in order) |
| `toggle shuffle` | Switch between shuffle and sequential modes |

**Sequential mode** (default):
- Plays tracks in order (1, 2, 3, 4...)
- Perfect for albums that should play in sequence
- "next track" advances to the next track in order
- Wraps back to beginning when playlist ends

**Shuffle mode**:
- Plays tracks randomly from the playlist
- Great for artist collections or genre playlists
- "next track" picks a random track

### Volume Control

| Command | What It Does |
|---------|--------------||
| `volume up` / `volume down` | Adjust volume ±10% |
| `set volume low/medium/high/loud` | Set volume to 20%/50%/80%/95% |

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
# Scan your music directory
source .venv/bin/activate
python tools/scan_music_library.py /path/to/music

# Or create empty database from schema
sqlite3 music_library.sqlite3 < music_library_schema.sql
```

### Wrong file paths

If your music moved, update the database:

```sql
UPDATE sounds 
SET location = REPLACE(location, '/old/path', '/new/path');
```

### Scanner Issues

**Scanner fails with import errors:**
```bash
source .venv/bin/activate
pip install mutagen librosa soundfile pydub
```

**Scanner is too slow:**
- Skip BPM analysis (don't use `--bpm` flag)
- BPM analysis adds 2-5 seconds per track
- For 13,000 tracks: ~1 hour without BPM, ~18-36 hours with BPM

**Scanner skips all files:**
- Check that database doesn't already have those files
- Files are identified by `location + filename` (must be unique)
- Look for "Skipping duplicate" messages in output

**Audio files not recognized:**
- Scanner supports `.ogg` and `.flac` only
- Check file extensions (case-insensitive)
- Verify files aren't corrupted (try playing them)

## Summary

The music database system gives you precise control over what plays, while maintaining the continuous playback experience. Say "play artist pink floyd" and enjoy hours of uninterrupted Floyd, or "play some jazz" for a chill evening soundtrack.

All powered by voice, no screen required! 🎵
