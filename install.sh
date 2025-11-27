#!/bin/bash
# Voice Assistant Installation Script
# Sets up the voice assistant with all dependencies and configuration

set -e  # Exit on error

echo "=========================================="
echo "🐦‍⬛ Jackdaw Voice Assistant Installation"
echo "=========================================="
echo ""
echo "This installer will set up Jackdaw on your system."
echo "It takes about 5-10 minutes depending on your internet speed."
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}Error: This script is designed for Linux systems${NC}"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Check for required system packages
echo ""
echo "Checking system dependencies..."
MISSING_DEPS=()

if ! command -v jack_lsp &> /dev/null; then
    MISSING_DEPS+=("jackd2 or pipewire-jack")
fi

if ! command -v ffmpeg &> /dev/null; then
    MISSING_DEPS+=("ffmpeg")
fi

# Check for Qt/XCB platform libraries (needed for GUI tray app)
if ! ldconfig -p | grep -q libxcb-xinerama; then
    MISSING_DEPS+=("libxcb-xinerama0 (for Qt GUI)")
fi

if ! ldconfig -p | grep -q libxcb-cursor; then
    MISSING_DEPS+=("libxcb-cursor0 (for Qt GUI)")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${YELLOW}Warning: Missing system dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Install with:"
    echo "  sudo apt install jackd2 ffmpeg libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0  # Debian/Ubuntu"
    echo "  sudo dnf install jack-audio-connection-kit ffmpeg libxcb xcb-util-cursor  # Fedora"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ All system dependencies found${NC}"
fi

# Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists, skipping...${NC}"
else
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo -e "${GREEN}✓ Python packages installed${NC}"

# Create directories
echo ""
echo "Creating directories..."
mkdir -p logs
mkdir -p ~/recordings
mkdir -p model
mkdir -p voices
echo -e "${GREEN}✓ Directories created${NC}"

# Check for Vosk model
echo ""
echo "Checking for Vosk speech recognition model..."
if [ ! -f "model/final.mdl" ]; then
    echo -e "${YELLOW}Warning: Vosk model not found in model/ directory${NC}"
    echo ""
    echo "Download a model from: https://alphacephei.com/vosk/models"
    echo "Recommended: vosk-model-small-en-us-0.15 (40 MB)"
    echo ""
    echo "Example:"
    echo "  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    echo "  unzip vosk-model-small-en-us-0.15.zip"
    echo "  mv vosk-model-small-en-us-0.15 model"
    echo ""
else
    echo -e "${GREEN}✓ Vosk model found${NC}"
fi

# Check for Piper TTS voice
echo ""
echo "Checking for Piper TTS voice model..."
if [ ! -f "voices/en_US-lessac-medium.onnx" ]; then
    echo -e "${YELLOW}Warning: Piper voice model not found in voices/ directory${NC}"
    echo ""
    echo "Download a voice from: https://github.com/rhasspy/piper/releases"
    echo "Recommended: en_US-lessac-medium"
    echo ""
    echo "Example:"
    echo "  cd voices"
    echo "  wget https://github.com/rhasspy/piper/releases/download/v1.0.0/en_US-lessac-medium.onnx"
    echo "  wget https://github.com/rhasspy/piper/releases/download/v1.0.0/en_US-lessac-medium.onnx.json"
    echo "  cd .."
    echo ""
else
    echo -e "${GREEN}✓ Piper voice model found${NC}"
fi

# Create config file if it doesn't exist
echo ""
echo "Setting up configuration..."
if [ -f "voice_assistant_config.json" ]; then
    echo -e "${YELLOW}Configuration file already exists, skipping...${NC}"
else
    HOSTNAME=$(hostname)
    echo "Creating voice_assistant_config.json..."
    cp voice_assistant_config.json.example voice_assistant_config.json
    
    # Update wake word to match hostname
    if command -v jq &> /dev/null; then
        jq --arg hostname "$HOSTNAME" '.voice.recognition.wake_word = $hostname' voice_assistant_config.json > voice_assistant_config.json.tmp
        mv voice_assistant_config.json.tmp voice_assistant_config.json
        echo -e "${GREEN}✓ Configuration created (wake word: $HOSTNAME)${NC}"
    else
        echo -e "${YELLOW}⚠ Configuration created but wake word not updated (jq not found)${NC}"
        echo "  Please edit voice_assistant_config.json and set wake_word to your hostname"
    fi
fi

# Create empty database files
echo ""
echo "Initializing databases..."
if [ ! -f "conversations.sqlite3" ]; then
    touch conversations.sqlite3
    echo -e "${GREEN}✓ Conversation database created${NC}"
fi

if [ ! -f "music_library.sqlite3" ]; then
    touch music_library.sqlite3
    echo -e "${YELLOW}⚠ Music database created (empty)${NC}"
    echo "  Run: python tools/scan_music_library.py to populate"
fi

# Make scripts executable
echo ""
echo "Setting script permissions..."
chmod +x start_voice_assistant.sh
chmod +x stop_voice_assistant.sh
echo -e "${GREEN}✓ Scripts are executable${NC}"

# Install Desktop Launcher and Autostart
echo ""
echo "=========================================="
echo "Jackdaw Desktop Integration"
echo "=========================================="
echo ""
echo "Installing desktop launcher and autostart..."

# Get current directory for absolute paths in desktop file
INSTALL_DIR=$(pwd)

# Update desktop file with absolute paths
if [ -f "jackdaw.desktop" ]; then
    # Create temporary desktop file with absolute paths
    sed "s|Exec=.*launch_tray_app.sh|Exec=${INSTALL_DIR}/launch_tray_app.sh|" jackdaw.desktop > /tmp/jackdaw.desktop.tmp
    sed -i "s|Icon=.*jackdaw-icon.png|Icon=${INSTALL_DIR}/jackdaw-icon.png|" /tmp/jackdaw.desktop.tmp
    
    # Install desktop file
    mkdir -p ~/.local/share/applications
    cp /tmp/jackdaw.desktop.tmp ~/.local/share/applications/jackdaw.desktop
    chmod +x ~/.local/share/applications/jackdaw.desktop
    rm /tmp/jackdaw.desktop.tmp
    echo -e "${GREEN}✓ Desktop launcher installed${NC}"
    
    # Install autostart
    mkdir -p ~/.config/autostart
    cp ~/.local/share/applications/jackdaw.desktop ~/.config/autostart/
    echo -e "${GREEN}✓ Autostart configured${NC}"
else
    echo -e "${YELLOW}⚠ jackdaw.desktop not found, skipping desktop integration${NC}"
fi

echo ""
echo "Jackdaw will:"
echo "  • Appear in your applications menu"
echo "  • Start automatically at login"
echo ""
echo "You can also start manually:"
echo "  GUI:  ./launch_tray_app.sh"
echo "  CLI:  ./start_voice_assistant.sh"
echo ""

# Check for Ollama
echo ""
echo "Checking for Ollama LLM server..."
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama found${NC}"
    
    # Check if model is available
    if ollama list | grep -q "granite4:tiny-h"; then
        echo -e "${GREEN}✓ granite4:tiny-h model available${NC}"
    else
        echo -e "${YELLOW}⚠ granite4:tiny-h model not found${NC}"
        echo "  Install with: ollama pull granite4:tiny-h"
    fi
else
    echo -e "${YELLOW}Warning: Ollama not found${NC}"
    echo "  Install from: https://ollama.com/"
    echo "  After installing, run: ollama pull granite4:tiny-h"
fi

# Summary
echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo -e "${BLUE}📖 Next Steps:${NC}"
echo ""
echo "1️⃣  Download required models (if you saw warnings above):"
echo ""
echo "   🧠 Speech Recognition (Vosk):"
echo "      wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
echo "      unzip vosk-model-small-en-us-0.15.zip && rm -rf model/*"
echo "      mv vosk-model-small-en-us-0.15/* model/ && rm *.zip"
echo ""
echo "   🗣️  Text-to-Speech (Piper):"
echo "      cd voices"
echo "      wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
echo "      wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
echo "      cd .."
echo ""
echo "2️⃣  Configure your wake word (optional):"
echo "      nano voice_assistant_config.json"
echo "      # Change \"wake_word\": \"alpha\" to your preferred word"
echo ""
echo "3️⃣  Scan your music library (optional):"
echo "      source .venv/bin/activate"
echo "      python tools/scan_music_library.py"
echo ""
echo "4️⃣  Connect audio in JACK (Carla or QjackCtl):"
echo "      Microphone → VoiceCommandClient:input"
echo "      TTSJackClient:out_L/R → Speakers"
echo "      OggPlayer:out_L/R → Speakers"
echo ""
echo -e "${GREEN}=========================================="
echo "🚀 Ready to Launch!"
echo "==========================================${NC}"
echo ""
echo "Launch Jackdaw:"
echo "  • Search for 'Jackdaw' in your applications menu"
echo "  • Or run: ./launch_tray_app.sh"
echo "  • CLI mode: ./start_voice_assistant.sh"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "  • Complete guide: ${GREEN}GETTING_STARTED.md${NC} ⭐"
echo "  • Quick reference: ${GREEN}docs/QUICK_REFERENCE.md${NC}"
echo "  • All docs: ${GREEN}docs/README.md${NC}"
echo ""
echo -e "${YELLOW}First time using JACK Audio?${NC}"
echo "  Don't worry! GETTING_STARTED.md walks you through everything."
echo ""
echo "Need help? Check the docs or open an issue:"
echo "  https://github.com/applebiter/jackdaw/issues"
echo ""
echo -e "${GREEN}Enjoy your voice-controlled audio system! 🎵🎤🐦‍⬛${NC}"
echo ""