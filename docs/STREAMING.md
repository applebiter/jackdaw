# Icecast2 Streaming Plugin

The Icecast2 streaming plugin enables Jackdaw to broadcast audio to an Icecast2 server for live streaming and syndication.

## Use Cases

- Live DJ sets or radio shows
- Collaborative jam sessions
- Broadcasting voice assistant interactions
- Multi-source audio mixing for streaming
- Networked audio distribution

## How It Works

The plugin uses FFmpeg to create a JACK client named `IcecastStreamer` with stereo input ports. You can connect any audio sources in your JACK graph to these inputs - the plugin will mix them and stream to your Icecast2 server. The implementation is in `plugins/icecast_streamer.py`.

## Quick Start

### 1. System Requirements

**FFmpeg with JACK and codec support:**
```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Verify JACK support
ffmpeg -devices 2>&1 | grep jack

# Verify codec support (should show libopus, libvorbis, flac, libmp3lame)
ffmpeg -codecs 2>&1 | grep -E "opus|vorbis|flac|mp3"
```

Most modern FFmpeg builds include all Xiph.org codecs (Opus, Vorbis, FLAC) by default.

### 2. Configure the Plugin

Edit `voice_assistant_config.json`:

```json
{
  "plugins": {
    "icecast_streamer": {
      "enabled": true,
      "host": "icecast.example.com",
      "port": 8000,
      "password": "your_source_password",
      "mount": "/jackdaw.ogg",
      "bitrate": 128,
      "format": "ogg"
    }
  }
}
```

**Configuration Options:**
- `host`: Icecast2 server hostname or IP
- `port`: Server port (default: 8000)
- `password`: Source password (set in Icecast2 config)
- `mount`: Stream mount point (e.g., `/jackdaw.ogg`, `/jackdaw.opus`, `/jackdaw.flac`)
- `bitrate`: Audio bitrate in kbps (ignored for FLAC which is lossless)
- `format`: Stream format - `ogg` (Vorbis), `opus`, `flac`, or `mp3`

**Format Recommendations (Xiph.org formats):**
- **opus**: Best for low-latency streaming, excellent quality at low bitrates (64-96 kbps)
- **ogg**: Classic Vorbis codec, good balance of quality and compatibility (128 kbps)
- **flac**: Lossless compression, highest quality, larger bandwidth requirements
- **mp3**: Widespread compatibility but not open source (128 kbps)

### 3. Choose Your Format

**Example configurations for different use cases:**

```json
// High-quality lossless streaming (studio/archival)
"icecast_streamer": {
  "enabled": true,
  "format": "flac",
  "mount": "/jackdaw.flac"
}

// Low-latency, efficient streaming (recommended for live broadcasts)
"icecast_streamer": {
  "enabled": true,
  "format": "opus",
  "bitrate": 96,
  "mount": "/jackdaw.opus"
}

// Classic streaming (maximum compatibility)
"icecast_streamer": {
  "enabled": true,
  "format": "ogg",
  "bitrate": 128,
  "mount": "/jackdaw.ogg"
}
```

### 4. Start Jackdaw

The plugin loads automatically when enabled. Restart Jackdaw if it's already running.

## Voice Commands

Say your wake word followed by:

- **"start streaming"** - Begin broadcasting to Icecast2
- **"stop streaming"** - End the broadcast
- **"stream status"** - Check current streaming status and bitrate
- **"begin broadcast"** - Alternative for start streaming
- **"end broadcast"** - Alternative for stop streaming

Examples:
- "indigo, start streaming"
- "indigo, what's the streaming status"
- "indigo, stop streaming"

## Implementation Details

The plugin is implemented in `plugins/icecast_streamer.py` and uses FFmpeg to:
1. Create a JACK client named `IcecastStreamer` with stereo input
2. Encode audio in real-time using Xiph.org or other codecs
3. Stream to Icecast2 using the `icecast://` protocol

The plugin monitors the streaming process and logs any errors. It gracefully handles start/stop commands and cleans up resources when disabled.

**Key Features:**
- Voice-controlled start/stop
- Support for Xiph.org formats (Ogg Vorbis, Opus, FLAC) and MP3
- Configurable bitrate (or lossless for FLAC)
- Process monitoring and error logging
- Automatic cleanup on shutdown

**About Xiph.org Formats:**

Jackdaw's streaming plugin supports the excellent open formats maintained by [Xiph.org](https://xiph.org/):

- **Opus**: Modern, low-latency codec perfect for live streaming. Superior quality at low bitrates (64-96 kbps typically sufficient).
- **Vorbis** (in Ogg container): Mature, widely-supported codec with good quality-to-size ratio.
- **FLAC**: Lossless compression for archival quality. No generation loss, larger files.

These formats are patent-free, royalty-free, and benefit the common good of the internet audio community. Xiph.org also maintains Speex (speech), Theora (video), and other important open media technologies.

## Testing Your Stream

1. **Start Icecast2 server** (if not already running)
   ```bash
   sudo systemctl start icecast2
   ```

2. **Configure the plugin** in `voice_assistant_config.json` with your server details

3. **Start Jackdaw** (restart if already running)

4. **Say "start streaming"** to begin the broadcast

5. **Connect audio sources** to the stream:
   ```bash
   # Connect music player
   jack_connect ogg_player:output_1 IcecastStreamer:input_L
   jack_connect ogg_player:output_2 IcecastStreamer:input_R
   
   # Connect voice assistant
   jack_connect tts_client:output_1 IcecastStreamer:input_L
   jack_connect tts_client:output_2 IcecastStreamer:input_R
   
   # Or use qjackctl for visual routing
   ```

6. **Listen to your stream** at: `http://your-icecast-server:8000/jackdaw.ogg`

You can connect multiple sources simultaneously - JACK will mix them automatically.

## Networked Collaboration Scenarios

Jackdaw's streaming capability enables powerful collaborative use cases:

### Distributed Jam Sessions
Musicians in different locations run Jackdaw instances that stream to a central Icecast2 server. Each musician's audio is captured and broadcast independently or mixed together.

### Multi-DJ Broadcasts
Multiple DJs contribute to the same stream using separate Jackdaw instances. The Icecast2 server can handle multiple mount points or sources.

### Recording Studio Broadcasting
Stream live studio sessions while maintaining full JACK routing flexibility. Route any combination of tracks, microphones, or instruments to the stream.

### Podcast Production
Multiple hosts on different machines contribute audio that gets mixed and streamed in real-time. Each host controls their local setup with voice commands.

## Extending the Plugin

The implementation in `plugins/icecast_streamer.py` can be extended with additional features:

### Metadata Updates

Add this method to update stream metadata (now playing information):

```python
def update_metadata(self, title, artist):
    """Update stream metadata using Icecast admin API"""
    import requests
    url = f"http://{self.host}:{self.port}/admin/metadata"
    params = {
        'mount': self.mount,
        'mode': 'updinfo',
        'song': f"{artist} - {title}"
    }
    auth = ('admin', self.password)
    
    try:
        response = requests.get(url, params=params, auth=auth)
        logger.info(f"Updated metadata: {artist} - {title}")
    except Exception as e:
        logger.error(f"Failed to update metadata: {e}")
```

### Auto-Reconnection

Add retry logic to handle network failures:

```python
def _start_stream_with_retry(self, max_retries=3):
    """Start streaming with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            result = self._start_stream()
            if "started" in result.lower():
                return result
        except Exception as e:
            logger.warning(f"Stream attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return "Failed to start stream after multiple attempts"
```

### Multiple Streams

Modify the plugin to support streaming to multiple servers simultaneously by running multiple FFmpeg processes with different configurations.

## See Also

- [Icecast2 Documentation](https://icecast.org/docs/)
- [FFmpeg JACK Documentation](https://trac.ffmpeg.org/wiki/Capture/JACK)
- [JACK Audio Documentation](https://jackaudio.org/)
