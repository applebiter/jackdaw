#!/bin/bash
# Run JackTrip Hub Server locally

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting JackTrip Hub Server..."
echo "Hub will be accessible at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set environment for local development
export HUB_HOST="${HUB_HOST:-localhost}"
export JACKTRIP_BASE_PORT="${JACKTRIP_BASE_PORT:-4464}"
export JACKTRIP_PORT_RANGE="${JACKTRIP_PORT_RANGE:-100}"

# Check if jacktrip is installed
if ! command -v jacktrip &> /dev/null; then
    echo "WARNING: jacktrip not found in PATH"
    echo "Install with: sudo apt install jacktrip"
    echo ""
fi

# Run with uvicorn
cd "$DIR"
uvicorn hub_server:app --host 0.0.0.0 --port 8000 --reload
