#!/bin/bash
# Run JackTrip Hub Server locally

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting JackTrip Hub Server..."
echo "Hub will be accessible at: https://\$(hostname):8000"
echo "API docs at: https://\$(hostname):8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set environment for local development
# HUB_HOST will be the actual hostname of the machine (karate for remote, indigo for local testing)
export HUB_HOST="${HUB_HOST:-$(hostname)}"
export JACKTRIP_BASE_PORT="${JACKTRIP_BASE_PORT:-4464}"
export JACKTRIP_PORT_RANGE="${JACKTRIP_PORT_RANGE:-100}"

# Single room mode configuration
export SINGLE_ROOM_MODE="${SINGLE_ROOM_MODE:-true}"
export BAND_NAME="${BAND_NAME:-The Band}"

# Set SSL certificates for HTTPS
export SSL_CERTFILE="${SSL_CERTFILE:-$DIR/certs/cert.pem}"
export SSL_KEYFILE="${SSL_KEYFILE:-$DIR/certs/key.pem}"

# Check if SSL certificates exist, if not generate them
if [ ! -f "$SSL_CERTFILE" ] || [ ! -f "$SSL_KEYFILE" ]; then
    echo "Generating self-signed SSL certificates..."
    mkdir -p "$DIR/certs"
    openssl req -x509 -newkey rsa:4096 -nodes -out "$SSL_CERTFILE" -keyout "$SSL_KEYFILE" -days 365 -subj "/CN=localhost"
    echo "Certificates generated at: $SSL_CERTFILE and $SSL_KEYFILE"
    echo ""
fi

# Check if jacktrip is installed
if ! command -v jacktrip &> /dev/null; then
    echo "WARNING: jacktrip not found in PATH"
    echo "Install with: sudo apt install jacktrip"
    echo ""
fi

# Activate virtual environment
VENV_PATH="$DIR/../../.venv"
if [[ -d "$VENV_PATH" ]]; then
    source "$VENV_PATH/bin/activate"
    echo "Using virtual environment: $VENV_PATH"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
fi

# Run with uvicorn using SSL
cd "$DIR"

# Create a trap to clean up child processes on SIGINT (Ctrl-C)
cleanup() {
    echo "Shutting down hub..."
    exit 0
}

trap cleanup SIGINT

# Run uvicorn in foreground without --reload to avoid reloader issues with Ctrl-C
# This ensures clean shutdown and proper port release when pressing Ctrl-C
echo "Hub running (production mode, no auto-reload)"
exec uvicorn hub_server:app --host 0.0.0.0 --port 8000 --ssl-certfile="$SSL_CERTFILE" --ssl-keyfile="$SSL_KEYFILE"
