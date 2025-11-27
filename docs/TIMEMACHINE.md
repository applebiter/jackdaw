# Ring Buffer Recorder - Retroactive Recording

## Overview

The Ring Buffer Recorder plugin provides retroactive audio recording using a Python-based implementation. It maintains a continuous buffer of recent audio, letting you "go back in time" and save what was just played or recorded - perfect for capturing spontaneous musical ideas.

**Use case**: You're improvising on piano, play something brilliant, and realize you need to save it *after* it's already happened. The ring buffer makes this possible.

## How It Works

1. **Continuous Buffer**: A Python JACK client runs in the background, constantly recording audio into a rolling buffer (default: 30 seconds)
2. **Retroactive Save**: When you say "save that", it writes the buffer contents to a timestamped WAV file
3. **Zero Latency**: The buffer is always recording, so there's no delay when you trigger a save
4. **Fully Headless**: Pure Python implementation - no GUI, no clicking, fully voice-controlled

Think of it as a DVR for your audio interface - constantly recording, ready to save on demand.

## Voice Commands

| Command | What It Does |
|---------|--------------|
| `start the buffer` | Start timemachine with continuous buffer |
| `stop the buffer` | Stop timemachine (clears buffer) |
| `save that` | Save the buffer to a WAV file |
| `save the last 30 seconds` | Same as "save that" |
| `save what i just played` | Same as "save that" |
| `buffer status` | Check if buffer is running |

## Configuration

Add to your `voice_assistant_config.json`:

```json
{
  "plugins": {
    "buffer": {
      "enabled": true,
      "buffer_seconds": 30,
      "output_dir": "~/recordings",
      "file_prefix": "recording-",
      "channels": 2,
      "format": "WAV",
      "jack_name": "RingBufferRecorder",
      "auto_connect": true
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable plugin |
| `buffer_seconds` | integer | `30` | Length of rolling buffer in seconds |
| `output_dir` | string | `"~/recordings"` | Where to save captured audio |
| `file_prefix` | string | `"recording-"` | Prefix for saved filenames |
| `channels` | integer | `2` | Number of audio channels |
| `format` | string | `"WAV"` | File format: WAV, FLAC, OGG, etc. |
| `jack_name` | string | `"RingBufferRecorder"` | JACK client name |
| `auto_connect` | boolean | `true` | Auto-connect to system:capture ports (deprecated) |

### Buffer Length Recommendations

- **10 seconds**: Good for short phrases, quick ideas
- **30 seconds**: Default, covers most improvisations
- **60 seconds**: Longer jams, extended solos
- **120+ seconds**: Full songs, lengthy performances

**Note**: Longer buffers use more RAM (about 10 MB per minute of stereo 44.1kHz audio).

## Usage Examples

### Basic Workflow

```
You: "indigo, start the buffer"
Assistant: [Starts ring buffer recorder]

You: [Improvising on piano]
You: [Play something awesome]
You: "indigo, save that"
Assistant: [Saves last 30 seconds to file]
```

The recording is saved to `~/recordings/recording-YYYYMMDD_HHMMSS.wav` (default location)

### Recommended Session Workflow

Start the buffer at the beginning of your session for best results:

```
You: "indigo, start the buffer"
Assistant: [Starts ring buffer]

[Connect audio sources in qjackctl/Carla if not auto-connected]

You: [Play piano for a while]
You: [Play something worth keeping]
You: "indigo, save that"
Assistant: [Saves last 30 seconds to WAV file]

You: [Continue playing]
You: [Another great moment]
You: "indigo, save that"
Assistant: [Saves another recording]

[When done for the day]
You: "indigo, stop the buffer"
Assistant: [Stops recorder]
```

### Auto-Start Behavior

If you say "save that" without starting the buffer first, the plugin will:
1. Automatically start the recorder
2. Wait 1 second for initialization
3. Trigger the save

**Caveat**: This only captures what happened *after* the recorder started, so you'll miss the beginning. Always start the buffer at the beginning of your session.

## JACK Routing

### Initial Setup (One-Time)

1. **Start the buffer**: Say "indigo, start the buffer"
2. **Connect sources**: In qjackctl or Carla, connect your audio sources to:
   - `RingBufferRecorder:in_1`
   - `RingBufferRecorder:in_2`
3. **Remember connections**: Run the routing memory tool:
   ```bash
   python tools/remember_jack_routing.py
   ```

After this one-time setup, connections will auto-restore every time you start the buffer!

### Manual Routing

Use `qjackctl`, `Carla`, or `jack_connect` to route audio:

```bash
# Connect microphone to ring buffer
jack_connect system:capture_1 RingBufferRecorder:in_1
jack_connect system:capture_1 RingBufferRecorder:in_2

# Connect piano plugin to ring buffer
jack_connect pianoteq:out_1 RingBufferRecorder:in_1
jack_connect pianoteq:out_2 RingBufferRecorder:in_2

# Record system playback (everything you hear)
jack_connect system:playback_1 RingBufferRecorder:in_1
jack_connect system:playback_2 RingBufferRecorder:in_2
```

### Remembering JACK Connections

The `remember_jack_routing.py` tool saves your JACK connections:

```bash
# While buffer is running with connections made:
python tools/remember_jack_routing.py
```

This saves to `jack_routing.json` and connections auto-restore on next startup.

### Advanced Routing Examples

**Record system output (everything you hear):**
```bash
jack_connect system:playback_1 RingBufferRecorder:in_1
jack_connect system:playback_2 RingBufferRecorder:in_2
```

**Record specific JACK client:**
```bash
jack_connect some_synth:left RingBufferRecorder:in_1
jack_connect some_synth:right RingBufferRecorder:in_2
```

**Mono input to stereo:**
```bash
jack_connect system:capture_1 RingBufferRecorder:in_1
jack_connect system:capture_1 RingBufferRecorder:in_2
```

## File Naming

Saved files are automatically timestamped:

```
recording-20251125_143022.wav
recording-20251125_143156.wav
recording-20251125_144301.wav
```

Format: `{prefix}YYYYMMDD_HHMMSS.{format}`

## Technical Details

### How the Ring Buffer Works

1. Maintains a circular buffer in RAM using NumPy arrays
2. JACK process callback continuously writes incoming audio to buffer
3. Write position wraps around when reaching buffer end
4. When triggered, copies buffer to disk asynchronously
5. Oldest data automatically overwritten (rolling window)

### Architecture

- **Pure Python**: No external processes or GUI dependencies
- **JACK-Client**: Native Python JACK integration
- **NumPy**: Efficient audio buffer storage
- **SoundFile**: High-quality audio file writing
- **Threading**: Async file saves don't block audio

### Implementation

```python
RingBufferRecorder
├── JACK process callback (real-time)
│   └── Writes audio to circular buffer
├── Save method (voice triggered)
│   └── Copies buffer and queues save
└── Background thread
    └── Writes files asynchronously
```

### Performance

- **RAM usage**: ~10 MB per minute (stereo, 44.1kHz, 32-bit float)
  - 30 seconds: ~5 MB
  - 60 seconds: ~10 MB
  - 120 seconds: ~20 MB
- **CPU usage**: Negligible (< 0.5%)
- **Disk I/O**: Only during saves (async, non-blocking)
- **Latency**: Zero - buffer is real-time

## Troubleshooting

### "Failed to start recording buffer"

**Check Python dependencies:**
```bash
pip list | grep -E "JACK-Client|numpy|soundfile"
```

**If missing, install:**
```bash
pip install JACK-Client numpy soundfile
```

**Check JACK is running:**
```bash
jack_lsp
```

### "Failed to save buffer"

**Possible causes:**
1. Buffer not started - say "start the buffer" first
2. Output directory doesn't exist - check `output_dir` config
3. No disk space - check `df -h`
4. Permissions issue - ensure output dir is writable

### No Audio in Saved Files

**Check JACK connections:**
```bash
jack_lsp -c | grep RingBuffer
```

Should show connections like:
```
RingBufferRecorder:in_1
   system:capture_1
RingBufferRecorder:in_2
   system:capture_2
```

**If not connected:**
- Manually connect in qjackctl/Carla
- Run `python tools/remember_jack_routing.py` to save connections
- Or use `jack_connect` commands

### Buffer Too Short

If you consistently miss the beginning of what you want to save, increase buffer length:

```json
{
  "timemachine": {
    "buffer_seconds": 60
  }
}
```

### Multiple Saves Overwrite Each Other

Not possible - each save gets a unique timestamp in the filename.

## Integration Ideas

### Auto-Start on Voice Assistant Launch

Modify `start_voice_assistant.sh`:

```bash
#!/bin/bash
# ... existing code ...

# Start recording buffer automatically
sleep 2
echo "Starting timemachine buffer..."
# Could add a direct timemachine start here, or rely on voice command
```

### Combine with JACK Transport

Record while JACK transport is rolling:

```python
# Future enhancement: start buffer when transport starts
# Stop buffer when transport stops
```

### Post-Processing Pipeline

Save recordings and automatically:
- Normalize levels
- Remove silence
- Apply compression
- Convert to MP3
- Add to music library database

## Comparison with Other Recording Tools

| Feature | Ring Buffer | Timemachine (C) | Ardour | JACK Recorder |
|---------|-------------|-----------------|--------|---------------|
| Retroactive recording | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Voice control | ✅ Yes | ❌ No | ❌ No | ⚠️ Limited |
| Buffer size | Configurable | Configurable | N/A | N/A |
| Lightweight | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| GUI required | ❌ No | ✅ Yes | ✅ Yes | ⚠️ Optional |
| Headless operation | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| Multi-format | ✅ Yes | ⚠️ Limited | ✅ Yes | ✅ Yes |
| Python-based | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Multi-track | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| Real-time | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

**When to use Ring Buffer Recorder:**
- Capturing spontaneous ideas
- Improvisation sessions
- "Oops, should have recorded that"
- Lightweight, always-on recording
- Fully headless/voice-controlled workflow

**When to use Ardour:**
- Full production
- Multi-track recording
- Editing and mixing
- Project-based work

## Summary

The Ring Buffer Recorder plugin turns your voice assistant into a retroactive recording safety net. Keep it running in the background during practice or composition sessions, and never lose a great idea again.

Perfect for:
- 🎹 Piano improvisations
- 🎸 Guitar riffs
- 🎤 Vocal ideas
- 🎛️ Synthesizer patches
- 🥁 Drum grooves

Just say "save that" and it's preserved forever! 🎵
