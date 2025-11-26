#!/bin/bash
# Launcher script for Voice Assistant Tray Application

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Activate virtual environment and run tray app
"$DIR/.venv/bin/python" "$DIR/voice_assistant_tray.py"
