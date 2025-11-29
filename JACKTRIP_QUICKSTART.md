# JackTrip Integration Quick Start

## What is it?

Anonymous real-time audio jamming with friends! Connect to a JackTrip hub server where you can create rooms and jam together without exposing your IP addresses to each other.

## Quick Setup

### 1. Install Hub Dependencies

```bash
cd tools/jacktrip_hub
pip install -r requirements.txt
```

Make sure `jacktrip` is installed:
```bash
sudo apt install jacktrip
# or install from: https://github.com/jacktrip/jacktrip
```

### 2. Start the Local Hub

```bash
cd tools/jacktrip_hub
./run_local_hub.sh
```

The hub will be accessible at: http://localhost:8000

### 3. Enable the Plugin

Edit your `voice_assistant_config.json`:

```json
{
  "plugins": {
    "jacktrip_client": {
      "enabled": true
    }
  },
  "jacktrip_hub": {
    "hub_url": "http://localhost:8000",
    "username": "demo",
    "password": "demo"
  }
}
```

### 4. Start Jackdaw

```bash
./start_voice_assistant.sh
```

## Voice Commands

Say these naturally to Jackdaw after the wake word "Indigo":

- **"Indigo, create jam room [name]"** - Create and join a room (e.g. "create jam room my studio")
- **"Indigo, list jam rooms"** - See all available rooms
- **"Indigo, join jam room [name]"** - Join an existing room (e.g. "join jam room my studio")
- **"Indigo, leave jam room"** - Leave the current room
- **"Indigo, who's in the room"** - See how many participants are in your room
- **"Indigo, jam room status"** - Check if your JackTrip connection is active

## Testing

Test the hub is working:

```bash
cd tools/jacktrip_hub
./test_hub.sh
```

## LAN Demo with Friends

To let friends on your local network join:

1. Find your LAN IP: `ip addr show`
2. Edit `tools/jacktrip_hub/run_local_hub.sh` and set:
   ```bash
   export HUB_HOST="192.168.1.10"  # Your LAN IP
   ```
3. Friends update their config:
   ```json
   "jacktrip_hub": {
     "hub_url": "http://192.168.1.10:8000"
   }
   ```
4. Make sure firewall allows:
   - TCP 8000 (API)
   - UDP 4464-4563 (JackTrip)

## Production VPS

For Internet jamming:

1. Get a VPS (DigitalOcean, Linode, etc.) near your location
2. Deploy hub server to VPS
3. Set up HTTPS reverse proxy
4. Update client configs with your domain

See `tools/jacktrip_hub/README.md` for detailed deployment guide.

## Architecture

```
You                     Hub Server              Friend
[Jackdaw] ----API----> [FastAPI]
  |                         |
  |                    [JackTrip Server]
  |                         |
[JackTrip Client] <---UDP--> |
                              |
                         [JackTrip Server]
                              |
                    <---UDP--> [JackTrip Client]
                                   |
                               [Jackdaw]
```

Everyone connects only to the hub, never directly to each other. IP addresses stay private!

## Troubleshooting

**Hub won't start:**
- Check Python dependencies: `pip install -r tools/jacktrip_hub/requirements.txt`
- Verify port 8000 is free: `netstat -tulpn | grep 8000`

**Plugin not working:**
- Check logs: `tail -f logs/voice_command_client.log`
- Verify config has `"jacktrip_client": {"enabled": true}`
- Restart voice assistant

**JackTrip won't connect:**
- Check `jacktrip` is installed: `which jacktrip`
- Verify JACK is running: `jack_lsp`
- Check firewall allows UDP ports

**High latency:**
- Use wired connections, not WiFi
- Hub should be geographically close
- Reduce JackTrip buffer (but may cause dropouts)
