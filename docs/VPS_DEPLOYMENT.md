# VPS Deployment Guide - Jackdaw Hub

## Overview
Deploy Jackdaw JackTrip Hub on a headless VPS (Virtual Private Server) for band collaboration. The VPS runs JACK in dummy mode (no audio hardware required) and serves as a pure routing hub for JackTrip clients.

## Why Deploy on VPS?

### Advantages
- **Central Meeting Point** - Band members connect from anywhere
- **Low Latency** - Data center network connections
- **Always Available** - 24/7 uptime for impromptu sessions
- **Clean Patchbay** - Only shows JackTrip client ports, no local hardware
- **Dedicated Resources** - No competition with desktop apps

### Requirements
- **Minimum Specs:** 2 CPU cores, 2GB RAM, 20GB storage
- **Recommended:** 4 CPU cores, 4GB RAM, 40GB storage
- **OS:** Ubuntu 22.04 or 24.04 LTS
- **Network:** Low latency connection, static IP preferred
- **Ports:** 8000 (HTTPS), 4464+ (JackTrip)

## Initial Server Setup

### 1. Create VPS Instance
Choose a provider with good network performance:
- DigitalOcean, Linode, Vultr (US/EU locations)
- AWS EC2, Google Cloud Compute (more expensive)
- Hetzner (EU, great price/performance)

**Location:** Choose closest to band members or central location

### 2. Initial Server Configuration

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y

# Create non-root user
adduser jackdaw
usermod -aG sudo jackdaw

# Enable firewall
ufw allow 22/tcp     # SSH
ufw allow 8000/tcp   # HTTPS hub
ufw allow 4464:4564/tcp  # JackTrip ports (100 port range)
ufw allow 4464:4564/udp  # JackTrip UDP
ufw enable

# Switch to jackdaw user
su - jackdaw
```

### 3. Install Dependencies

```bash
# Install system packages
sudo apt install -y \
    jackd2 \
    jack-tools \
    jacktrip \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    sqlite3 \
    build-essential

# Disable audio hardware requirement for JACK
# This allows JACK to run without audio devices
sudo dpkg-reconfigure -p high jackd2
# Select "No" when asked about realtime priority (or "Yes" if you want it)
```

### 4. Clone Repository

```bash
cd ~
git clone https://github.com/applebiter/jackdaw.git
cd jackdaw
```

### 5. Setup Python Environment

```bash
# Create virtual environment
python3.12 -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn bcrypt python-multipart requests
```

### 6. Generate SSL Certificates

For production, use Let's Encrypt. For testing, self-signed works:

#### Option A: Self-Signed (Testing)
```bash
mkdir -p tools/jacktrip_hub/certs
cd tools/jacktrip_hub/certs

openssl req -x509 -newkey rsa:4096 -nodes \
    -out cert.pem -keyout key.pem -days 365 \
    -subj "/CN=YOUR_DOMAIN_OR_IP"

cd ~/jackdaw
```

#### Option B: Let's Encrypt (Production)
```bash
# Install certbot
sudo apt install -y certbot

# Get certificate (requires domain name)
sudo certbot certonly --standalone -d your-band-hub.com

# Link certificates
mkdir -p tools/jacktrip_hub/certs
sudo ln -s /etc/letsencrypt/live/your-band-hub.com/fullchain.pem \
    tools/jacktrip_hub/certs/cert.pem
sudo ln -s /etc/letsencrypt/live/your-band-hub.com/privkey.pem \
    tools/jacktrip_hub/certs/key.pem
```

## JACK Dummy Backend Setup

### Start Script with JACK Dummy
Create `~/jackdaw/start_headless_hub.sh`:

```bash
#!/bin/bash
# Jackdaw Hub Startup Script for Headless VPS
# Uses JACK dummy backend (no audio hardware needed)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Jackdaw Hub - VPS Headless Mode ==="
echo ""

# Kill any existing JACK servers
echo "Stopping existing JACK servers..."
killall -9 jackd 2>/dev/null || true
sleep 1

# Start JACK with dummy backend
echo "Starting JACK with dummy backend..."
jackd -d dummy \
    -r 48000 \
    -p 128 \
    --nperiods 3 \
    > /tmp/jackd.log 2>&1 &

JACK_PID=$!
echo "JACK started (PID: $JACK_PID)"

# Wait for JACK to initialize
sleep 2

# Verify JACK is running
if ! jack_lsp > /dev/null 2>&1; then
    echo "ERROR: JACK failed to start!"
    cat /tmp/jackd.log
    exit 1
fi

echo "JACK is running in dummy mode (no audio hardware)"
echo ""

# Set environment variables
export HUB_HOST="${HUB_HOST:-$(hostname)}"
export JACKTRIP_BASE_PORT="${JACKTRIP_BASE_PORT:-4464}"
export JACKTRIP_PORT_RANGE="${JACKTRIP_PORT_RANGE:-100}"

# SSL certificates
export SSL_CERTFILE="$SCRIPT_DIR/tools/jacktrip_hub/certs/cert.pem"
export SSL_KEYFILE="$SCRIPT_DIR/tools/jacktrip_hub/certs/key.pem"

echo "Configuration:"
echo "  Hub Host: $HUB_HOST"
echo "  JackTrip Ports: $JACKTRIP_BASE_PORT-$((JACKTRIP_BASE_PORT + JACKTRIP_PORT_RANGE - 1))"
echo "  HTTPS: enabled"
echo ""

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Start hub server
echo "Starting Jackdaw Hub Server..."
cd "$SCRIPT_DIR/tools/jacktrip_hub"

# Cleanup handler
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $JACK_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run hub (this blocks)
exec uvicorn hub_server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile="$SSL_CERTFILE" \
    --ssl-keyfile="$SSL_KEYFILE"
```

Make it executable:
```bash
chmod +x ~/jackdaw/start_headless_hub.sh
```

### Test Manual Start
```bash
cd ~/jackdaw
./start_headless_hub.sh
```

You should see:
```
=== Jackdaw Hub - VPS Headless Mode ===

Stopping existing JACK servers...
Starting JACK with dummy backend...
JACK started (PID: 12345)
JACK is running in dummy mode (no audio hardware)

Configuration:
  Hub Host: your-vps-hostname
  JackTrip Ports: 4464-4563
  HTTPS: enabled

Starting Jackdaw Hub Server...
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:8000 (Press CTRL+C to quit)
```

Press Ctrl+C to stop. Now set up systemd for automatic startup.

## Systemd Service Setup

### Create Service File
```bash
sudo nano /etc/systemd/system/jackdaw-hub.service
```

Paste this configuration:

```ini
[Unit]
Description=Jackdaw JackTrip Hub with JACK Dummy Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jackdaw
Group=jackdaw
WorkingDirectory=/home/jackdaw/jackdaw

# Environment variables
Environment="HUB_HOST=your-vps-hostname-or-ip"
Environment="JACKTRIP_BASE_PORT=4464"
Environment="JACKTRIP_PORT_RANGE=100"
Environment="SSL_CERTFILE=/home/jackdaw/jackdaw/tools/jacktrip_hub/certs/cert.pem"
Environment="SSL_KEYFILE=/home/jackdaw/jackdaw/tools/jacktrip_hub/certs/key.pem"

# Use the startup script
ExecStart=/home/jackdaw/jackdaw/start_headless_hub.sh

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jackdaw-hub

[Install]
WantedBy=multi-user.target
```

**Important:** Replace `your-vps-hostname-or-ip` with your VPS's public hostname or IP address!

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable jackdaw-hub

# Start service now
sudo systemctl start jackdaw-hub

# Check status
sudo systemctl status jackdaw-hub
```

### View Logs
```bash
# Follow live logs
sudo journalctl -u jackdaw-hub -f

# View recent logs
sudo journalctl -u jackdaw-hub -n 100

# View JACK dummy backend logs
tail -f /tmp/jackd.log
```

## Verify Deployment

### 1. Check JACK is Running
```bash
jack_lsp
```

Should output nothing (no ports yet) or show any existing JackTrip client ports.

### 2. Check Hub is Running
```bash
curl -k https://localhost:8000/health
```

Should return JSON health status.

### 3. Access from Remote Machine
From your local machine:
```bash
curl -k https://YOUR_VPS_IP:8000/health
```

### 4. Test Web Interface
Open in browser: `https://YOUR_VPS_IP:8000`

You should see the login page.

## First Time Setup

### 1. Create Owner Account
- Navigate to `https://YOUR_VPS_IP:8000`
- Click "Register"
- Create first account (becomes owner automatically)
- Login

### 2. Configure Voice Assistant
On your local machine, update `voice_assistant_config.json`:

```json
{
  "jacktrip_hub": {
    "hub_url": "https://YOUR_VPS_IP_OR_DOMAIN:8000",
    "username": "your_username",
    "password": "your_password",
    "verify_ssl": false
  }
}
```

For production with Let's Encrypt: `"verify_ssl": true`

### 3. Test Connection
Voice command: "join session" or "join jam room [name]"

Should connect successfully and show JackTrip client ports in the patchbay.

## VPS Patchbay Usage

### What You'll See
The patchbay on a VPS shows **only JackTrip client ports**:

```
member1:send_1       →  Connect to other members
member1:send_2
member1:receive_1    ←  Receive from other members
member1:receive_2
member2:send_1
member2:send_2
member2:receive_1
member2:receive_2
```

### Common Routing Patterns

#### 1. Full Band Mix (Everyone hears everyone)
Connect each member's send to all other members' receives:
```
member1:send_1 → member2:receive_1
member1:send_2 → member2:receive_2
member1:send_1 → member3:receive_1
member1:send_2 → member3:receive_2

member2:send_1 → member1:receive_1
member2:send_2 → member1:receive_2
member2:send_1 → member3:receive_1
member2:send_2 → member3:receive_2

... (and so on)
```

#### 2. Monitor Mixes (Custom per member)
- Drummer hears everyone
- Vocalist only hears backing track + drums
- etc.

#### 3. Sub-groups
Route specific members together before sending to others.

### No Local I/O
Since this is a headless server:
- ❌ No `system:capture_*` ports
- ❌ No `system:playback_*` ports  
- ❌ No `pulse_in/out` ports
- ✅ Clean, focused routing interface
- ✅ Only band member connections visible

## Maintenance

### Update Jackdaw
```bash
cd ~/jackdaw
git pull origin main
sudo systemctl restart jackdaw-hub
```

### Check Disk Space
```bash
df -h
```

### Monitor Resource Usage
```bash
# CPU and memory
htop

# Network
iftop

# JACK performance
jack_cpu_load
```

### Backup Database
```bash
# Backup users database
cp ~/jackdaw/tools/jacktrip_hub/hub.db \
   ~/jackdaw_backup_$(date +%Y%m%d).db

# Optional: backup to another machine
scp ~/jackdaw/tools/jacktrip_hub/hub.db \
    user@backup-server:/backups/
```

### Renew SSL Certificates (Let's Encrypt)
Certbot auto-renews, but verify:
```bash
sudo certbot renew --dry-run
sudo systemctl restart jackdaw-hub
```

## Troubleshooting

### JACK Won't Start
```bash
# Check if jackd is already running
ps aux | grep jackd

# Kill all JACK processes
killall -9 jackd

# Check logs
cat /tmp/jackd.log

# Try starting manually
jackd -d dummy -r 48000 -p 128
```

### Hub Won't Start
```bash
# Check logs
sudo journalctl -u jackdaw-hub -n 50

# Check if port 8000 is in use
sudo lsof -i :8000

# Test Python dependencies
source ~/jackdaw/.venv/bin/activate
python -c "import fastapi, uvicorn, bcrypt"
```

### Can't Connect from Clients
```bash
# Check firewall
sudo ufw status

# Ensure ports are open
sudo ufw allow 8000/tcp
sudo ufw allow 4464:4564/tcp
sudo ufw allow 4464:4564/udp

# Check if hub is listening
sudo netstat -tlnp | grep 8000
```

### JackTrip Clients Not Appearing
```bash
# Check if JackTrip server is running
ps aux | grep jacktrip

# Check JackTrip logs in hub
sudo journalctl -u jackdaw-hub | grep -i jacktrip

# Verify JACK is seeing connections
jack_lsp -c
```

## Performance Tuning

### For More Users
Increase JackTrip port range:
```bash
sudo nano /etc/systemd/system/jackdaw-hub.service
# Change: Environment="JACKTRIP_PORT_RANGE=200"
sudo systemctl daemon-reload
sudo systemctl restart jackdaw-hub
```

### Lower Latency
Reduce JACK period size (increases CPU usage):
```bash
# Edit start_headless_hub.sh
# Change: jackd -d dummy -r 48000 -p 64 --nperiods 2
```

### Higher Reliability
Increase buffer for unstable networks:
```bash
# Change: jackd -d dummy -r 48000 -p 256 --nperiods 3
```

## Security Best Practices

1. **Use SSH Keys** (disable password auth)
2. **Enable Automatic Updates**
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```
3. **Use Let's Encrypt** (not self-signed certificates)
4. **Regular Backups** (database + configs)
5. **Monitor Logs** for suspicious activity
6. **Limit User Registration** (if needed, modify hub code)

## Cost Estimates

### Monthly VPS Costs
- **Basic (2 CPU, 2GB RAM):** $10-15/month
  - Supports 4-6 simultaneous users
- **Recommended (4 CPU, 4GB RAM):** $20-30/month
  - Supports 8-12 simultaneous users
- **High Performance (8 CPU, 8GB RAM):** $40-60/month
  - Supports 15+ simultaneous users

### Domain Name (Optional)
- **Domain:** $10-15/year
- Makes SSL certificate setup easier
- Easier to remember than IP address

## Next Steps

1. ✅ Deploy hub on VPS
2. ✅ Create owner account
3. ✅ Test connection from local machine
4. ✅ Invite band members to register
5. ✅ Configure patchbay routing
6. 🎵 Start jamming!

## Support

For issues or questions:
- GitHub: https://github.com/applebiter/jackdaw/issues
- Check logs: `sudo journalctl -u jackdaw-hub -f`
- Verify JACK: `jack_lsp` and `/tmp/jackd.log`
