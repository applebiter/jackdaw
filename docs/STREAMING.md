# Icecast2 Streaming Plugin

This document describes how to implement streaming capabilities in Jackdaw using Icecast2.

## Overview

The streaming plugin enables Jackdaw to broadcast audio to an Icecast2 server for live streaming and syndication. This is useful for:
- Live DJ sets or radio shows
- Collaborative jam sessions
- Broadcasting voice assistant interactions
- Multi-source audio mixing for streaming

## Architecture Options

### Option 1: Direct Icecast2 Connection (Recommended)

Stream directly to Icecast2 using Python libraries like `python-shout` (libshout bindings) or `ffmpeg`. This approach is simpler and more reliable.

**Advantages:**
- Fewer moving parts (no external processes)
- Better error handling and status reporting
- Direct control over stream quality and encoding
- Easier to implement voice commands (start/stop streaming)

**Implementation:**
```python
import shout
import jack
import numpy as np

class IcecastStreamer:
    def __init__(self, host, port, password, mount):
        self.shout = shout.Shout()
        self.shout.host = host
        self.shout.port = port
        self.shout.password = password
        self.shout.mount = mount
        self.shout.format = 'mp3'  # or 'ogg'
        
        self.client = jack.Client('IcecastStreamer')
        self.client.inports.register('input_L')
        self.client.inports.register('input_R')
        
    def process(self, frames):
        # Capture stereo audio from JACK
        left = self.client.inports[0].get_array()
        right = self.client.inports[1].get_array()
        
        # Encode and send to Icecast2
        audio_data = self.encode_audio(left, right)
        self.shout.send(audio_data)
```

**Required Packages:**
```bash
pip install python-shout
# or
pip install pydub  # for ffmpeg-based encoding
```

### Option 2: Ices2 Source Client

Use `ices2` as an external source client, piping audio via `jack_stdout`.

**Advantages:**
- Battle-tested streaming software
- Built-in reconnection logic
- Playlist support

**Disadvantages:**
- More complex process management
- Harder to integrate voice commands
- Additional dependency

**Implementation:**
```bash
# Create a JACK client that outputs to stdout
jack_stdout -c 2 IcecastOutput | ices2 config.xml
```

**Ices2 Configuration (config.xml):**
```xml
<?xml version="1.0"?>
<ices>
    <background>0</background>
    <logpath>/path/to/logs</logpath>
    <logfile>ices.log</logfile>
    
    <stream>
        <metadata>
            <name>Jackdaw Stream</name>
            <genre>Various</genre>
            <description>Live audio from Jackdaw</description>
        </metadata>
        
        <input>
            <module>stdinpcm</module>
            <param name="rate">48000</param>
            <param name="channels">2</param>
            <param name="metadata">1</param>
        </input>
        
        <instance>
            <hostname>icecast.example.com</hostname>
            <port>8000</port>
            <password>hackme</password>
            <mount>/jackdaw.ogg</mount>
            <encode>
                <quality>5</quality>
                <samplerate>48000</samplerate>
                <channels>2</channels>
            </encode>
        </instance>
    </stream>
</ices>
```

## Recommended Implementation: Direct Python Streaming

Here's a complete plugin implementation using direct streaming:

```python
# plugins/icecast_streamer.py

from plugin_base import VoiceAssistantPlugin
import threading
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

class IcecastStreamerPlugin(VoiceAssistantPlugin):
    """
    Streams audio to Icecast2 server using FFmpeg for encoding.
    Creates a JACK client with stereo input that accepts connections
    from any audio source in the JACK graph.
    """
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.streaming_process = None
        self.stream_thread = None
        self.is_streaming = False
        
        plugin_config = config_manager.get("plugins", {}).get("icecast_streamer", {})
        self.host = plugin_config.get("host", "localhost")
        self.port = plugin_config.get("port", 8000)
        self.password = plugin_config.get("password", "hackme")
        self.mount = plugin_config.get("mount", "/jackdaw.ogg")
        self.bitrate = plugin_config.get("bitrate", 128)
        
    def get_name(self):
        return "icecast_streamer"
    
    def get_description(self):
        return "Stream audio to Icecast2 server"
    
    def get_commands(self):
        return {
            "start streaming": self._start_stream,
            "stop streaming": self._stop_stream,
            "stream status": self._stream_status,
            "begin broadcast": self._start_stream,
            "end broadcast": self._stop_stream,
        }
    
    def _start_stream(self):
        """Start streaming to Icecast2 server"""
        if self.is_streaming:
            logger.info("Already streaming")
            return "Already streaming"
        
        try:
            # FFmpeg command to capture from JACK and stream to Icecast
            cmd = [
                'ffmpeg',
                '-f', 'jack',
                '-channels', '2',
                '-i', 'IcecastStreamer',  # JACK client name
                '-acodec', 'libvorbis',
                '-b:a', f'{self.bitrate}k',
                '-content_type', 'application/ogg',
                '-f', 'ogg',
                f'icecast://source:{self.password}@{self.host}:{self.port}{self.mount}'
            ]
            
            self.streaming_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_streaming = True
            logger.info(f"Started streaming to {self.host}:{self.port}{self.mount}")
            return "Stream started"
            
        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            return f"Failed to start stream: {e}"
    
    def _stop_stream(self):
        """Stop streaming"""
        if not self.is_streaming:
            logger.info("Not currently streaming")
            return "Not streaming"
        
        try:
            if self.streaming_process:
                self.streaming_process.terminate()
                self.streaming_process.wait(timeout=5)
                self.streaming_process = None
            
            self.is_streaming = False
            logger.info("Stream stopped")
            return "Stream stopped"
            
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return f"Error stopping stream: {e}"
    
    def _stream_status(self):
        """Report streaming status"""
        if self.is_streaming:
            return f"Streaming to {self.host}:{self.port}{self.mount}"
        else:
            return "Not currently streaming"
    
    def cleanup(self):
        """Cleanup when plugin is unloaded"""
        if self.is_streaming:
            self._stop_stream()


def create_plugin(config_manager):
    return IcecastStreamerPlugin(config_manager)
```

## Configuration

Add to `voice_assistant_config.json`:

```json
{
  "plugins": {
    "icecast_streamer": {
      "enabled": true,
      "host": "icecast.example.com",
      "port": 8000,
      "password": "your_source_password",
      "mount": "/jackdaw.ogg",
      "bitrate": 128
    }
  }
}
```

## Voice Commands

Once configured and enabled, use these commands:

- **"start streaming"** - Begin broadcasting to Icecast2
- **"stop streaming"** - End the broadcast
- **"stream status"** - Check if currently streaming
- **"begin broadcast"** - Alternative for start streaming
- **"end broadcast"** - Alternative for stop streaming

## JACK Routing

The streaming plugin creates a JACK client named `IcecastStreamer` with stereo input ports. Connect any audio sources you want to stream:

```bash
# Connect music player to stream
jack_connect ogg_player:output_1 IcecastStreamer:input_L
jack_connect ogg_player:output_2 IcecastStreamer:input_R

# Connect voice assistant output
jack_connect tts_client:output_1 IcecastStreamer:input_L
jack_connect tts_client:output_2 IcecastStreamer:input_R

# Or use qjackctl for visual routing
```

You can connect multiple sources - JACK will mix them automatically.

## System Requirements

**For FFmpeg approach (recommended):**
```bash
sudo apt install ffmpeg
# FFmpeg must be compiled with --enable-libjack and --enable-libvorbis
```

**For python-shout approach:**
```bash
sudo apt install libshout3-dev
pip install python-shout
```

## Testing Your Stream

1. Start the Icecast2 server
2. Configure the plugin in `voice_assistant_config.json`
3. Say "start streaming"
4. Connect audio sources in JACK
5. Listen at: `http://your-icecast-server:8000/jackdaw.ogg`

## Networked Collaboration

Jackdaw's streaming capability enables powerful collaborative scenarios:

1. **Distributed Jam Sessions**: Musicians in different locations connect their local Jackdaw instances to stream their parts to a central Icecast2 server
2. **Multi-DJ Broadcasts**: Multiple DJs contribute to the same stream using separate Jackdaw instances
3. **Recording Studio Broadcasting**: Stream studio sessions live while maintaining full JACK routing flexibility
4. **Podcast Production**: Multiple hosts on different machines contribute audio that gets mixed and streamed

## Advanced: Metadata Updates

To update stream metadata (now playing information):

```python
def update_metadata(self, title, artist):
    """Update stream metadata"""
    if self.is_streaming and self.streaming_process:
        # Use Icecast admin API to update metadata
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

## Future Enhancements

- Auto-reconnection on network failure
- Buffer management for stream stability
- Multiple stream outputs (stream to multiple servers)
- Stream recording locally while broadcasting
- Automatic metadata from music player plugin
- Voice command to announce current stream URL

## See Also

- [Icecast2 Documentation](https://icecast.org/docs/)
- [FFmpeg JACK Documentation](https://trac.ffmpeg.org/wiki/Capture/JACK)
- [JACK Audio Documentation](https://jackaudio.org/)
