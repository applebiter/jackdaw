# Timemachine Plugin - Retroactive Recording

## Overview

The Timemachine plugin integrates JACK Timemachine, a tool that maintains a continuous buffer of recent audio. This lets you "go back in time" and save what was just played or recorded, perfect for capturing spontaneous musical ideas.

**Use case**: You're improvising on piano, play something brilliant, and realize you need to save it *after* it's already happened. Timemachine makes this possible.

## How It Works

1. **Continuous Buffer**: Timemachine runs in the background, constantly recording audio into a rolling buffer (default: 30 seconds)
2. **Retroactive Save**: When you say "save that", it writes the buffer contents to a WAV file
3. **Zero Latency**: The buffer is always recording, so there's no delay when you trigger a save

Think of it as a DVR for your audio interface - constantly recording, ready to save on demand.

## Voice Commands

| Command | What It Does |
|---------|--------------|
| `start recording buffer` | Start timemachine with continuous buffer |
| `stop recording buffer` | Stop timemachine (clears buffer) |
| `save that` | Save the buffer to a WAV file |
| `save the last 30 seconds` | Same as "save that" |
| `save what i just played` | Same as "save that" |
| `timemachine status` | Check if buffer is running |

## Configuration

Add to your `voice_assistant_config.json`:

```json
{
  "plugins": {
    "timemachine": {
      "enabled": true,
      "buffer_seconds": 30,
      "output_dir": "~/recordings",
      "file_prefix": "recording-",
      "channels": 2,
      "format": "wav",
      "jack_name": "TimeMachine",
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
| `channels` | integer | `2` | Number of audio channels (1-8) |
| `format` | string | `"wav"` | File format: `"wav"` or `"w64"` |
| `jack_name` | string | `"TimeMachine"` | JACK client name |
| `auto_connect` | boolean | `true` | Auto-connect to system:capture ports |

### Buffer Length Recommendations

- **10 seconds**: Good for short phrases, quick ideas
- **30 seconds**: Default, covers most improvisations
- **60 seconds**: Longer jams, extended solos
- **120+ seconds**: Full songs, lengthy performances

**Note**: Longer buffers use more RAM (about 10 MB per minute of stereo 44.1kHz audio).

## Usage Examples

### Basic Workflow

```
You: [Improvising on piano]
You: [Play something awesome]
You: "indigo, save that"
Assistant: "Saved the last 30 seconds."
```

The recording is saved to `~/recordings/recording-YYYYMMDD-HHMMSS.wav`

### Start Buffer First (Recommended)

For better reliability, start the buffer when you begin your session:

```
You: "indigo, start recording buffer"
Assistant: "Recording buffer started. Say 'save that' to capture the last 30 seconds."

You: [Play piano for a while]
You: [Play something worth keeping]
You: "indigo, save that"
Assistant: "Saved the last 30 seconds."

You: [Continue playing]
You: [Another great moment]
You: "indigo, save that"
Assistant: "Saved the last 30 seconds."

[When done for the day]
You: "indigo, stop recording buffer"
Assistant: "Recording buffer stopped."
```

### Auto-Start Behavior

If you say "save that" without starting the buffer first, the plugin will:
1. Automatically start timemachine
2. Wait 1 second for initialization
3. Trigger the save

**Caveat**: This only captures what happened *after* timemachine started, so you might miss the beginning of what you wanted to save. Better to start the buffer at the beginning of your session.

## JACK Routing

### Default Behavior (`auto_connect: true`)

Timemachine automatically connects to:
- `system:capture_1` → `TimeMachine:in_1`
- `system:capture_2` → `TimeMachine:in_2`

This records from your audio interface inputs (microphones, instruments, etc.).

### Custom Routing (`auto_connect: false`)

Disable auto-connect and manually route in JACK:

```json
{
  "timemachine": {
    "auto_connect": false
  }
}
```

Then use `qjackctl`, `Carla`, or `jack_connect` to route audio:

```bash
# Connect piano plugin to timemachine
jack_connect pianoteq:out_1 TimeMachine:in_1
jack_connect pianoteq:out_2 TimeMachine:in_2

# Or system playback (record what you hear)
jack_connect system:playback_1 TimeMachine:in_1
jack_connect system:playback_2 TimeMachine:in_2
```

### Advanced Routing Examples

**Record system output (everything you hear):**
```bash
jack_connect system:playback_1 TimeMachine:in_1
jack_connect system:playback_2 TimeMachine:in_2
```

**Record specific JACK client:**
```bash
jack_connect some_synth:left TimeMachine:in_1
jack_connect some_synth:right TimeMachine:in_2
```

**Mono input to stereo:**
```bash
jack_connect system:capture_1 TimeMachine:in_1
jack_connect system:capture_1 TimeMachine:in_2
```

## File Naming

Saved files are automatically timestamped:

```
recording-20251125-143022.wav
recording-20251125-143156.wav
recording-20251125-144301.wav
```

Format: `{prefix}YYYYMMDD-HHMMSS.{format}`

## Technical Details

### How Timemachine Works

1. Maintains a circular buffer in RAM
2. Continuously writes incoming audio to buffer
3. When triggered (SIGUSR1 signal), writes buffer to disk
4. Buffer overwrites oldest data (rolling window)

### Signal-Based Control

The plugin controls timemachine using Unix signals:

- **SIGUSR1**: Trigger save (write buffer to file)
- **SIGTERM**: Graceful shutdown
- **SIGKILL**: Force kill (if SIGTERM fails)

### Process Management

- Timemachine runs as subprocess
- Plugin tracks PID for signal delivery
- Automatic cleanup on voice assistant shutdown
- Safe handling of multiple save requests

### Performance

- **RAM usage**: ~10 MB per minute (stereo, 44.1kHz, 16-bit)
  - 30 seconds: ~5 MB
  - 60 seconds: ~10 MB
  - 120 seconds: ~20 MB
- **CPU usage**: Negligible (< 1%)
- **Disk I/O**: Only during saves

## Troubleshooting

### "Failed to start recording buffer"

**Check if timemachine is installed:**
```bash
which timemachine
timemachine -h
```

**Install if missing:**
```bash
sudo apt install timemachine
```

### "Failed to save buffer"

**Possible causes:**
1. Buffer not started - say "start recording buffer" first
2. Output directory doesn't exist - check `output_dir` config
3. No disk space - check `df -h`
4. Permissions issue - ensure output dir is writable

### No Audio in Saved Files

**Check JACK connections:**
```bash
jack_lsp -c | grep TimeMachine
```

Should show connections like:
```
TimeMachine:in_1
   system:capture_1
TimeMachine:in_2
   system:capture_2
```

**If not connected:**
- Enable `auto_connect: true` in config
- Or manually connect in qjackctl/Carla
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

| Feature | Timemachine | Ardour | JACK Recorder |
|---------|-------------|--------|---------------|
| Retroactive recording | ✅ Yes | ❌ No | ❌ No |
| Voice control | ✅ Yes | ❌ No | ⚠️ Limited |
| Buffer size | Configurable | N/A | N/A |
| Lightweight | ✅ Yes | ❌ No | ✅ Yes |
| GUI | ❌ No | ✅ Yes | ⚠️ Optional |
| Multi-track | ❌ No | ✅ Yes | ✅ Yes |
| Real-time | ✅ Yes | ✅ Yes | ✅ Yes |

**When to use Timemachine:**
- Capturing spontaneous ideas
- Improvisation sessions
- "Oops, should have recorded that"
- Lightweight, always-on recording

**When to use Ardour:**
- Full production
- Multi-track recording
- Editing and mixing
- Project-based work

## Summary

The Timemachine plugin turns your voice assistant into a retroactive recording safety net. Keep it running in the background during practice or composition sessions, and never lose a great idea again.

Perfect for:
- 🎹 Piano improvisations
- 🎸 Guitar riffs
- 🎤 Vocal ideas
- 🎛️ Synthesizer patches
- 🥁 Drum grooves

Just say "save that" and it's preserved forever! 🎵
