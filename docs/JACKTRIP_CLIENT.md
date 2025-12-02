# JackTrip Client Setup Guide

Complete guide for using Jackdaw's JackTrip plugin to connect to a hub and collaborate with other musicians over the network.

## Overview

The JackTrip client plugin allows you to:
- Connect to a JackTrip hub server on your LAN or internet
- Create and join jam rooms with other musicians
- Collaborate in real-time with low-latency audio
- Use voice commands to control everything
- View and modify audio routing via web patchbay

All audio routing happens through JACK, integrating seamlessly with your audio workflow.

---

## Prerequisites

### Required Software

1. **Jackdaw** - This voice assistant (already installed)
2. **JACK Audio** - Must be running (`jackd`)
3. **JackTrip** - Install via:
   ```bash
   # Ubuntu/Debian
   sudo apt install jacktrip
   
   # Fedora
   sudo dnf install jacktrip
   
   # Or compile from source:
   # https://github.com/jacktrip/jacktrip
   ```

### Hub Server

You need access to a JackTrip hub server. Options:

- **LAN Setup**: Run hub on one PC in your home (see LAN Setup section below)
- **Internet Server**: Connect to a hosted hub (requires public domain/IP)

---

## Quick Start (Existing Hub)

If someone has already set up a hub server, here's how to connect:

### 1. Get Hub Credentials

You need:
- Hub URL (e.g., `https://192.168.1.10:8000` for LAN or `https://jamhub.example.com:8000`)
- Your username and password (or register a new account)

### 2. Configure Jackdaw

Edit `voice_assistant_config.json`:

```json
{
  "plugins": {
    "jacktrip_client": {
      "enabled": true,
      "hub_url": "https://192.168.1.10:8000",
      "username": "your_username",
      "password": "your_password",
      "send_channels": 2,
      "receive_channels": 2,
      "jack_client_name": "jacktrip_client",
      "auto_connect": true
    }
  }
}
```

**Important**: Use `https://` not `http://` - the hub requires secure connections.

### 3. Trust the Certificate (LAN Only)

If using a LAN setup with self-signed certificates, you'll need to trust the certificate. See the "Certificate Trust" section below.

### 4. Test Connection

Start Jackdaw:
```bash
./launch_tray_app.sh
```

Say your wake word, then:
- **"list jam rooms"** - See available rooms
- **"create jam room test session"** - Create a room named "test session"
- **"join jam room test session"** - Join the room

If it works, you'll hear audio connections being made through JACK.

---

## LAN Setup Guide

Complete instructions for setting up a JackTrip hub on your home network for testing.

### Architecture

```
┌─────────────────┐
│   Hub Server    │  One PC running hub_server.py
│  192.168.1.10   │  - Manages rooms
│   JACK + Hub    │  - Spawns JackTrip servers
└────────┬────────┘  - Provides web patchbay
         │
    ┌────┴────┐
    │   LAN   │
    └────┬────┘
         │
    ┌────┴─────────────────┐
    │                      │
┌───┴─────┐          ┌─────┴───┐
│ Client 1│          │ Client 2│
│  Guitar │          │  Vocals │
│ JACK    │          │  JACK   │
└─────────┘          └─────────┘
```

### Step 1: Choose Your Hub PC

Pick one computer to be the hub server. Requirements:
- Runs Linux
- Has JACK Audio installed
- Connected to your LAN (wired is better than WiFi)
- Decent CPU (handles audio routing for all clients)

This PC will run both:
- JackTrip hub server (Python FastAPI)
- JACK audio server
- Local audio interface (if monitoring)

### Step 2: Setup Hub Server

On your chosen hub PC:

#### Install Dependencies

```bash
# Navigate to jackdaw directory
cd ~/Programs/jack-voice-assistant

# Activate virtual environment
source .venv/bin/activate

# Dependencies should already be installed from jackdaw setup
# But ensure bcrypt is there:
pip install bcrypt
```

#### Configure Hub

Find your hub PC's LAN IP address:
```bash
ip addr show
# Look for something like: inet 192.168.1.10/24
```

Set environment variable:
```bash
export HUB_HOST=192.168.1.10  # Use YOUR actual IP
```

#### Start Hub Server

```bash
cd tools/jacktrip_hub
../../.venv/bin/python hub_server.py
```

You should see:
```
Generating self-signed certificate for development...
✓ Certificate generated at .../certs/cert.pem

============================================================
JackTrip Hub Server
============================================================
URL: https://192.168.1.10:8000
⚠️  Using self-signed certificate - browsers will show warnings
============================================================
```

Keep this terminal open (or run in screen/tmux).

#### Firewall Configuration

Open the necessary ports:
```bash
# Hub API (HTTPS)
sudo ufw allow 8000/tcp

# JackTrip audio (UDP)
sudo ufw allow 4464:4563/udp

# Check status
sudo ufw status
```

### Step 3: Export Certificate

To allow clients to connect without certificate warnings, export the self-signed certificate:

```bash
# On hub PC
cd ~/Programs/jack-voice-assistant/tools/jacktrip_hub/certs

# Copy cert.pem to a USB drive or shared folder
cp cert.pem /path/to/shared/location/hub-cert.pem
```

### Step 4: Setup Client PCs

On each client PC (including the hub PC if you want to use it as a client too):

#### Install Certificate

```bash
# Copy the certificate from hub
cp /path/to/hub-cert.pem ~/hub-cert.pem

# Install in system certificate store
sudo cp ~/hub-cert.pem /usr/local/share/ca-certificates/jacktrip-hub.crt
sudo update-ca-certificates
```

For Python requests library specifically:
```bash
# Option 1: Set environment variable
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Option 2: Or add to .bashrc
echo 'export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt' >> ~/.bashrc
```

#### Configure Jackdaw Client

Edit `voice_assistant_config.json`:

```json
{
  "plugins": {
    "jacktrip_client": {
      "enabled": true,
      "hub_url": "https://192.168.1.10:8000",
      "username": "",
      "password": "",
      "send_channels": 2,
      "receive_channels": 2,
      "jack_client_name": "jacktrip_client",
      "auto_connect": true
    }
  }
}
```

**Note**: Leave `username` and `password` empty on first run - you'll register via voice command.

### Step 5: Register Users

On each client PC, start Jackdaw and say:

**"register on jam hub as [username]"** (Not yet implemented - see manual registration below)

**Manual registration for now**:
```bash
# On each client
curl -k -X POST https://192.168.1.10:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"guitarist","password":"mypassword"}'

# Save the token returned, or just update config file with username/password
```

Then update `voice_assistant_config.json` with your credentials:
```json
"username": "guitarist",
"password": "mypassword"
```

### Step 6: Test It!

On any client, say:
- **"create jam room test session"**
- On another client: **"join jam room test session"**
- **"open patchbay"** (opens web browser to view audio routing)

You should hear audio connections being established through JACK!

---

## Voice Commands

### Room Management

| Command | Description |
|---------|-------------|
| `create jam room [name]` | Create a new room |
| `list jam rooms` | Show all available rooms |
| `join jam room [name]` | Join an existing room |
| `leave jam room` | Disconnect from current room |
| `who's in the room` | List current room participants |
| `jam room status` | Show your connection status |

### Audio Management

| Command | Description |
|---------|-------------|
| `open patchbay` | Open web-based JACK patchbay |

### Private Rooms (Future)

Private rooms with passphrases are supported by the hub but not yet implemented in voice commands. Use the web patchbay or API directly:

```bash
# Create private room
curl -k -X POST https://192.168.1.10:8000/rooms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Private Jam",
    "passphrase": "secret123"
  }'

# Join private room
curl -k -X POST https://192.168.1.10:8000/rooms/$ROOM_ID/join \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"passphrase": "secret123"}'
```

---

## Configuration Options

### Plugin Configuration

In `voice_assistant_config.json`:

```json
{
  "plugins": {
    "jacktrip_client": {
      "enabled": true,
      "hub_url": "https://192.168.1.10:8000",
      "username": "your_username",
      "password": "your_password",
      "send_channels": 2,
      "receive_channels": 2,
      "jack_client_name": "jacktrip_client",
      "auto_connect": true
    }
  }
}
```

**Options**:

- `hub_url`: Hub server HTTPS URL (use actual LAN IP or domain)
- `username`: Your registered username on the hub
- `password`: Your password
- `send_channels`: Number of audio channels to send (1-32)
- `receive_channels`: Number of audio channels to receive (1-32)
- `jack_client_name`: Name of JACK client (shows in patchbay)
- `auto_connect`: Automatically connect JACK ports on join (true/false)

### Channel Configuration

Common configurations:

**Mono (one microphone)**:
```json
"send_channels": 1,
"receive_channels": 2
```

**Stereo (two microphones or interface)**:
```json
"send_channels": 2,
"receive_channels": 2
```

**Multi-track (interface with many inputs)**:
```json
"send_channels": 8,
"receive_channels": 8
```

---

## Web Patchbay

Access the visual JACK patchbay at:
```
https://192.168.1.10:8000/patchbay/test-room
```

Features:
- Drag-and-drop cable routing
- Zoom and pan the canvas
- Minimap for navigation
- Real-time updates as others join
- See all JACK clients and connections

See [JACKTRIP_PATCHBAY.md](../JACKTRIP_PATCHBAY.md) for full patchbay documentation.

---

## Certificate Trust

### Why Certificates?

All hub communication uses HTTPS to protect your passwords. For LAN testing, the hub generates a self-signed certificate, which browsers and Python don't trust by default.

### Option 1: Install Certificate (Recommended for LAN)

Install the hub's certificate on each client:

```bash
# Copy from hub PC
scp user@192.168.1.10:~/Programs/jack-voice-assistant/tools/jacktrip_hub/certs/cert.pem ~/hub-cert.pem

# Install system-wide
sudo cp ~/hub-cert.pem /usr/local/share/ca-certificates/jacktrip-hub.crt
sudo update-ca-certificates

# For Python requests
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

### Option 2: Disable Verification (NOT RECOMMENDED)

Only for temporary testing:

```python
# In jacktrip_client.py, add verify=False to requests:
response = requests.post(url, json=data, verify=False)
```

This is insecure and should not be used long-term!

### Option 3: Use Real Certificates (Production)

For internet-accessible hubs:

1. Get a domain name
2. Use Let's Encrypt:
   ```bash
   sudo certbot certonly --standalone -d jamhub.example.com
   ```
3. Configure hub:
   ```bash
   export SSL_CERTFILE=/etc/letsencrypt/live/jamhub.example.com/fullchain.pem
   export SSL_KEYFILE=/etc/letsencrypt/live/jamhub.example.com/privkey.pem
   ```

---

## Troubleshooting

### "Unable to authenticate with JackTrip hub"

**Cause**: Can't connect to hub or wrong credentials.

**Solutions**:
1. Check hub is running: `curl -k https://192.168.1.10:8000/health`
2. Verify URL in config (must be `https://`)
3. Check username/password are correct
4. Ensure certificate is trusted (see Certificate Trust section)

### "Failed to start JackTrip client"

**Cause**: JackTrip binary not found or JACK not running.

**Solutions**:
1. Check JACK is running: `jack_lsp`
2. Verify JackTrip installed: `which jacktrip`
3. Check logs in terminal for error details

### "No audio" or "Can't hear anyone"

**Cause**: JACK ports not connected.

**Solutions**:
1. Open patchbay: Say **"open patchbay"**
2. Check connections between:
   - `system:capture` → `jacktrip_client:send_*`
   - `jacktrip_client:receive_*` → `system:playback`
3. If `auto_connect: true`, it should happen automatically
4. Manually connect in patchbay or `qjackctl`

### "High latency" or "Choppy audio"

**Causes**: Network issues, buffer settings, CPU load.

**Solutions**:
1. Use wired Ethernet (not WiFi)
2. Check JACK buffer size: Lower for less latency
3. Adjust JackTrip queue depth (`-q` flag)
4. Close other network-heavy applications
5. Check CPU usage: `top` or `htop`

### Certificate errors

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution**: Install the hub's certificate (see Certificate Trust section)

**Quick test**: Temporarily add `-k` to curl or `verify=False` in Python

### Can't create/join rooms

**Cause**: Not authenticated or wrong permissions.

**Solutions**:
1. Register an account first
2. Update config with correct username/password
3. Check hub logs for authentication errors

### Firewall blocking connections

**Cause**: Ports not open on hub or client.

**Solutions**:
```bash
# On hub
sudo ufw allow 8000/tcp
sudo ufw allow 4464:4563/udp

# On clients (if firewall is very strict)
sudo ufw allow out to 192.168.1.10 port 8000 proto tcp
sudo ufw allow out to 192.168.1.10 port 4464:4563 proto udp
```

---

## Advanced Topics

### Running Hub as Systemd Service

Create `/etc/systemd/system/jacktrip-hub.service`:

```ini
[Unit]
Description=JackTrip Hub Server
After=network.target jack.service

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/Programs/jack-voice-assistant/tools/jacktrip_hub
Environment="HUB_HOST=192.168.1.10"
Environment="PATH=/home/yourusername/Programs/jack-voice-assistant/.venv/bin:/usr/bin"
ExecStart=/home/yourusername/Programs/jack-voice-assistant/.venv/bin/python hub_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jacktrip-hub
sudo systemctl start jacktrip-hub
sudo systemctl status jacktrip-hub
```

### Custom JackTrip Flags

To pass custom flags to JackTrip client, the hub server returns them in the join response. You can't currently override via voice commands, but you can modify the hub server to add flags.

Common flags:
- `-q N` - Queue buffer length (1-32, default 4)
- `-b` - Bind to specific local port
- `-r` - Sample rate
- `-B` - Broadcast audio to all clients

### Multiple Rooms

You can be in only one room at a time. To switch rooms:
1. **"leave jam room"**
2. **"join jam room [other name]"**

### Monitoring Hub Status

View hub logs:
```bash
# If running in terminal
# Just watch the output

# If running as systemd service
sudo journalctl -u jacktrip-hub -f
```

Check active rooms:
```bash
curl -k -X GET https://192.168.1.10:8000/rooms \
  -H "Authorization: Bearer $TOKEN"
```

---

## Security Best Practices

### For LAN Testing

1. **Use strong passwords** - Even on LAN, use decent passwords
2. **Keep the hub updated** - Pull latest changes regularly
3. **Monitor who connects** - Check logs for unexpected users
4. **Use passphrases for private sessions**

### For Internet Deployment

1. **Get a real domain** - Don't use raw IP addresses
2. **Use Let's Encrypt certificates** - Free, trusted, auto-renewing
3. **Enable firewall** - Block all ports except what's needed
4. **Regular backups** - Back up `hub.db` with user accounts
5. **Monitor logs** - Watch for suspicious activity
6. **Rate limiting** - Consider adding to prevent abuse (not yet implemented)

---

## Future Features

Coming soon:
- Voice command to register accounts
- Voice command to manage user permissions
- Reconnection handling (auto-rejoin on disconnect)
- Audio effects/processing plugins
- Recording integration
- Latency monitoring

---

## Getting Help

If you encounter issues:

1. **Check logs**: Look at terminal output or systemd logs
2. **Test hub**: `curl -k https://hub-ip:8000/health`
3. **Verify JACK**: `jack_lsp` should show clients
4. **Check network**: `ping hub-ip`
5. **Review config**: Double-check `voice_assistant_config.json`

For bugs or feature requests, see the main Jackdaw repository.
