# Music Library Browser

A graphical application for browsing, searching, and playing music from your Jackdaw music library database.

## Features

- **Browse & Search**: Paginated table view with sorting and searching by artist, album, title, genre, or year
- **Track Details**: View complete metadata including audio properties, BPM, credits, and file information
- **Local Playback**: Play tracks on your local JACK audio system
- **Icecast Streaming**: Stream tracks to your Icecast2 server
- **Dual Mode**: Play locally and stream simultaneously
- **Multi-Selection**: Select multiple tracks to create on-the-fly playlists
- **Shuffle Support**: Random or sequential playback

## Quick Start

```bash
# Launch the browser
./launch_music_browser.sh

# Or manually
source .venv/bin/activate
python music_library_browser.py
```

## Interface Overview

### Main Table
- **Sortable Columns**: Click any column header to sort (click again to reverse)
- **Multi-Selection**: Hold Ctrl/Cmd to select multiple tracks, Shift for range selection
- **Columns**: Title, Artist, Album, Genre, Year, Duration, BPM, File Path

### Search Bar
- Enter search text and select field to search (artist, album, title, genre, year)
- Click "Search" or press Enter to filter results
- Click "Clear" to show all tracks

### Track Details Panel
- Shows complete metadata for selected track
- Audio format information (sample rate, channels, bitrate)
- Credits (composer, producer, engineer, label)
- File path and size

### Pagination Controls
- Navigate pages with Previous/Next buttons
- Adjust page size (10-500 tracks per page)
- Shows current page and total track count

### Playback Controls

#### Local JACK Playback
- **▶ Play Selected on JACK**: Play selected tracks on your local JACK audio system
- **⏹ Stop Local Playback**: Stop currently playing tracks
- **Shuffle**: Enable random playback order (unchecked = sequential)

#### Icecast Streaming
- **📡 Stream Selected to Icecast**: Start streaming selected tracks to your Icecast2 server
- **⏹ Stop Streaming**: Stop the Icecast stream
- **Stream Status**: Shows current streaming state and details

#### Dual Mode
- **🔊 Play Local + Stream**: Play tracks locally AND stream to Icecast simultaneously
- Requires JACK routing setup (see below)

## JACK Routing for Dual Mode

To play music locally while streaming, route the audio outputs in JACK:

```bash
# Connect to local speakers
jack_connect ogg_player:output_1 system:playback_1
jack_connect ogg_player:output_2 system:playback_2

# Connect to stream
jack_connect ogg_player:output_1 IcecastStreamer:input_L
jack_connect ogg_player:output_2 IcecastStreamer:input_R
```

Or use `qjackctl` for visual routing:
1. Open qjackctl connection graph
2. Connect `ogg_player` outputs to both `system:playback` (speakers) and `IcecastStreamer` inputs (stream)

## Configuration

The browser uses your existing `voice_assistant_config.json` for Icecast settings:

```json
{
  "plugins": {
    "icecast_streamer": {
      "enabled": true,
      "host": "localhost",
      "port": 8000,
      "password": "your_source_password",
      "mount": "/jackdaw.ogg",
      "bitrate": 128,
      "format": "ogg"
    }
  }
}
```

## Workflow Examples

### Browse and Play Locally

1. Launch the browser
2. Browse or search for tracks
3. Select one or more tracks (Ctrl+Click for multiple)
4. Click "▶ Play Selected on JACK"
5. Audio plays through your JACK system to your speakers

### Stream to Icecast

1. Make sure Icecast2 server is running
2. Configure streaming settings in `voice_assistant_config.json`
3. Select tracks in the browser
4. Click "📡 Stream Selected to Icecast"
5. Tracks stream to your Icecast server
6. Listen at `http://your-server:8000/jackdaw.ogg`

### DJ Mode: Play + Stream

1. Launch browser and configure Icecast settings
2. Select tracks or create a playlist
3. Click "🔊 Play Local + Stream"
4. Set up JACK routing (if not already done)
5. Music plays locally AND streams online simultaneously

### Create a Playlist

1. Search for tracks (e.g., search "jazz" in genre field)
2. Select multiple tracks using Ctrl+Click or Shift+Click
3. Click play or stream button
4. Tracks play in order (or shuffled if enabled)

## Tips & Tricks

- **Quick Search**: Type in search box and press Enter
- **Sort Multiple Ways**: Click different column headers to organize your view
- **Large Libraries**: Increase page size for fewer page loads
- **Monitor Stream**: Status label updates every 2 seconds with stream info
- **Track Details**: Click a single track to see full metadata in details panel
- **Keyboard Navigation**: Use arrow keys to navigate table, Space to select

## Troubleshooting

### "Database Not Found" Error
- Run the music scanner first: `python tools/scan_music_library.py /path/to/music`
- Make sure `music_library.sqlite3` exists in the Jackdaw directory

### Streaming Doesn't Work
- Verify Icecast2 server is running: `sudo systemctl status icecast2`
- Check configuration in `voice_assistant_config.json`
- Ensure FFmpeg has JACK support: `ffmpeg -devices 2>&1 | grep jack`
- Check logs for error messages

### No Audio on Local Playback
- Verify JACK server is running: `jack_control status`
- Check JACK connections: `jack_lsp -c` or use `qjackctl`
- Make sure speakers are connected in JACK graph

### Tracks Won't Play
- Verify file paths are correct (shown in Track Details)
- Check file permissions
- Ensure audio files are in supported format (Ogg, Opus, FLAC, MP3)

## See Also

- `docs/MUSIC_DATABASE.md` - Music library system guide
- `docs/STREAMING.md` - Icecast2 streaming setup
- `tools/scan_music_library.py` - Database scanner tool
- `voice_assistant_config.json.example` - Configuration template
