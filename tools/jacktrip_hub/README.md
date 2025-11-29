# JackTrip Hub Server

A secure hub server for anonymous JackTrip collaboration. This allows multiple users to jam together in real-time without exposing their IP addresses to each other.

## Features

- **Secure Authentication**: User registration/login with bcrypt password hashing
- **HTTPS by Default**: Auto-generates self-signed certificates for development
- **Private Rooms**: Optional passphrase protection for rooms
- **Web Patchbay**: Interactive JACK connection graph with drag-and-drop routing
- **Real-time Updates**: WebSocket-based live graph updates
- **Room Management**: Create, join, and manage jam sessions

## Architecture

- **Hub Server**: FastAPI-based HTTPS service with SQLite user database
- **Clients**: Connect via the JackTrip plugin in Jackdaw or HTTP API
- **Privacy**: All users connect only to the hub, never directly to each other
- **Security**: Passwords never sent in plaintext (HTTPS + bcrypt)

## Quick Start

### 1. Install Dependencies

```bash
cd tools/jacktrip_hub
pip install -r requirements.txt
```

Make sure you have JackTrip installed:

```bash
# Ubuntu/Debian
sudo apt install jacktrip

# Or build from source
# https://github.com/jacktrip/jacktrip
```

### 2. Run the Hub (Local Development)

```bash
# Using virtual environment
cd /path/to/jack-voice-assistant
.venv/bin/python tools/jacktrip_hub/hub_server.py
```

The server will:
- Auto-generate a self-signed SSL certificate (first run)
- Initialize SQLite database (`hub.db`)
- Start on HTTPS port 8000

**Note**: Browsers will show security warnings for self-signed certificates. This is normal for development.

### 3. Register a User

```bash
curl -k -X POST https://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser","password":"mypassword"}'
```

This returns an auth token for API requests.

### 4. Access Web Patchbay

Open `https://localhost:8000/patchbay/test-room` in your browser (accept the certificate warning).

The patchbay provides:
- Visual JACK connection graph
- Drag-and-drop cable routing
- Zoom and pan controls
- Minimap navigation
- Real-time updates

### 4. Test with Jackdaw

Load the JackTrip plugin and use voice commands:
- "Create jam room"
- "List jam rooms"
- "Join Tuesday session"
- "Leave room"

## Configuration

Environment variables for the hub server:

- `HUB_HOST`: Hostname/IP for JackTrip connections (default: `localhost`)
- `HUB_PORT`: HTTPS port for web server (default: `8000`)
- `JACKTRIP_BIN`: Path to jacktrip binary (default: `jacktrip`)
- `JACKTRIP_BASE_PORT`: Starting port for JackTrip instances (default: `4464`)
- `JACKTRIP_PORT_RANGE`: Number of ports available (default: `100`)
- `SSL_CERTFILE`: Path to SSL certificate (optional, auto-generates if not set)
- `SSL_KEYFILE`: Path to SSL private key (optional, auto-generates if not set)

## Deployment

### Local LAN Demo

1. Find your machine's LAN IP: `ip addr show`
2. Set `HUB_HOST` to your LAN IP (e.g., `192.168.1.10`)
3. Friends connect their Jackdaw clients to `http://192.168.1.10:8000`
4. Make sure firewall allows UDP ports 4464-4563

### Production VPS

For production deployment to a VPS:

1. Get a domain name (e.g., `jamhub.example.com`)
2. Obtain SSL certificates from Let's Encrypt:
   ```bash
   sudo certbot certonly --standalone -d jamhub.example.com
   ```
3. Set environment variables:
   ```bash
   export HUB_HOST=jamhub.example.com
   export HUB_PORT=8000
   export SSL_CERTFILE=/etc/letsencrypt/live/jamhub.example.com/fullchain.pem
   export SSL_KEYFILE=/etc/letsencrypt/live/jamhub.example.com/privkey.pem
   ```
4. Set up systemd service
5. Open firewall for:
   - TCP 8000 (HTTPS API)
   - UDP 4464-4563 (JackTrip)
6. Set up auto-renewal for certificates:
   ```bash
   sudo certbot renew --deploy-hook "systemctl restart jacktrip-hub"
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user (username, password, optional email)
- `POST /auth/login` - Login and get session token

### Rooms
- `GET /rooms` - List all active rooms (requires auth token)
- `POST /rooms` - Create new room with optional passphrase (requires auth)
- `GET /rooms/{id}` - Get room details (requires auth)
- `POST /rooms/{id}/join` - Join room, provide passphrase if private (requires auth)
- `POST /rooms/{id}/leave` - Leave room (requires auth)

### JACK Audio
- `GET /jack/graph` - Get current JACK audio graph
- `POST /jack/connect` - Connect two JACK ports
- `POST /jack/disconnect` - Disconnect two JACK ports
- `GET /patchbay/{room_id}` - Web-based patchbay interface
- `WebSocket /ws/patchbay` - Real-time graph updates

### Health
- `GET /health` - Server health check (no auth required)

## How It Works

1. User creates or joins a room via API
2. Hub spawns a JackTrip server process on a unique UDP port
3. Hub returns connection details: `{hub_host, port, room_name}`
4. Client spawns local JackTrip client: `jacktrip -C {hub_host} -p {port}`
5. JACK automatically connects audio I/O
6. When room is empty, hub stops the JackTrip process

## Troubleshooting

### JackTrip won't start
- Check `jacktrip` is in PATH: `which jacktrip`
- Verify JACK is running: `jack_lsp`

### Can't connect from another machine
- Check firewall: `sudo ufw status`
- Verify hub is listening: `netstat -tulpn | grep 8000`
- Test UDP ports: `nc -u {hub_ip} 4464`

### High latency
- Use wired connections, not WiFi
- Check JackTrip buffer settings (queue depth)
- Consider geographically closer hub location

## Security

### Authentication System
- **User Registration**: Create accounts with username/password
- **Bcrypt Hashing**: Passwords never stored in plaintext
- **Session Tokens**: JWT-style tokens for API authentication
- **SQLite Database**: User accounts and sessions persisted

### HTTPS/TLS
- **Auto-Generated Certificates**: Development mode creates self-signed certs
- **Production Certificates**: Use Let's Encrypt or commercial CA
- **Encrypted Transport**: All credentials sent over HTTPS only

### Room Privacy
- **Public Rooms**: Anyone with an account can join
- **Private Rooms**: Require passphrase to join
- **Creator Control**: Room creator sets privacy level

### Best Practices
- Use strong passwords for user accounts
- Set passphrases on private rooms
- Keep SSL certificates up to date
- Monitor server logs for suspicious activity
- Use firewall rules to limit access
- Consider rate limiting for production
