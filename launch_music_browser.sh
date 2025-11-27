#!/bin/bash
# Launch Music Library Browser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    python music_library_browser.py
else
    echo "Error: Virtual environment not found at .venv/"
    echo "Please run ./install.sh first"
    exit 1
fi
