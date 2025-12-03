# Windows Compatibility Roadmap

## Goal
Enable Windows users (especially bandmates) to use Jackdaw for JackTrip collaboration without Linux knowledge.

## Target Users
- Non-technical musicians on Windows 10/11
- Users with JACK for Windows and JackTrip already installed
- Band members who need simple "double-click and it works" experience

---

## Phase 1: JackTrip Client (Minimal Windows Build)

**Priority: HIGH** - Core band collaboration functionality

### What Bandmates Need
- JackTrip client plugin (voice-controlled connection)
- System tray application (basic controls)
- Basic voice commands (join/leave room, status)
- Simple installer package

### What to Skip (Linux-Only for Now)
- Music library scanning (Linux paths, shell scripts)
- LLM chat (Ollama setup complexity)
- Advanced plugins (icecast, buffer recording)
- Development tools

### Implementation Tasks

#### 1. Platform Abstraction Layer
**File:** `platform_utils.py` (new)

```python
"""Cross-platform utilities for process and system management."""
import platform
import subprocess
from typing import Optional, List

def is_windows() -> bool:
    return platform.system() == "Windows"

def is_linux() -> bool:
    return platform.system() == "Linux"

def find_process(pattern: str) -> Optional[int]:
    """Find process ID by name pattern."""
    if is_windows():
        # Use tasklist
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq python*", "/FO", "CSV"],
            capture_output=True, text=True
        )
        # Parse and match pattern
    else:
        # Use pgrep
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True
        )
    return int(result.stdout.strip()) if result.returncode == 0 else None

def kill_process(pattern: str) -> bool:
    """Kill process by name pattern."""
    if is_windows():
        # Use taskkill with pattern matching
        pid = find_process(pattern)
        if pid:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)])
            return True
    else:
        # Use pkill
        subprocess.run(["pkill", "-f", pattern])
        return True
    return False

def get_python_executable() -> str:
    """Get platform-appropriate Python executable."""
    import sys
    return sys.executable
```

#### 2. Cross-Platform Launcher
**File:** `launch.py` (new)

```python
#!/usr/bin/env python3
"""
Cross-platform launcher for Jackdaw voice assistant.
Works on Windows, Linux, and macOS.
"""
import sys
import subprocess
from pathlib import Path
import platform_utils

def main():
    """Launch the Jackdaw tray application."""
    script_dir = Path(__file__).parent
    tray_app = script_dir / "voice_assistant_tray.py"
    
    if not tray_app.exists():
        print(f"Error: Could not find {tray_app}")
        sys.exit(1)
    
    python_exe = platform_utils.get_python_executable()
    
    print("Starting Jackdaw...")
    subprocess.Popen([python_exe, str(tray_app)])
    print("✓ Jackdaw tray app launched")

if __name__ == "__main__":
    main()
```

#### 3. Update voice_assistant_tray.py
Replace all `pgrep`/`pkill` calls with `platform_utils` functions:

**Lines to update:**
- `_cleanup_existing_processes()` method (~line 310)
- `_check_for_duplicate_tray()` method (~line 332)
- `update_status()` method (~line 427-431)

**Example change:**
```python
# OLD:
result = subprocess.run(["pgrep", "-f", "voice_command_client.py"], ...)

# NEW:
import platform_utils
pid = platform_utils.find_process("voice_command_client.py")
if pid:
    # Process is running
```

#### 4. Signal Handler Fix
**File:** `voice_assistant_tray.py` (~line 45)

```python
# OLD:
signal.signal(signal.SIGINT, self._signal_handler)
signal.signal(signal.SIGTERM, self._signal_handler)

# NEW:
signal.signal(signal.SIGINT, self._signal_handler)
if not platform_utils.is_windows():
    signal.signal(signal.SIGTERM, self._signal_handler)  # Not available on Windows
```

#### 5. Windows Installer
**Tool:** PyInstaller or cx_Freeze

Create standalone executable:
```bash
# On Windows
pip install pyinstaller
pyinstaller --name Jackdaw --windowed --icon=icons/jackdaw.ico voice_assistant_tray.py
```

Package structure:
```
JackdawClient-Windows/
├── Jackdaw.exe
├── config.json.example
├── voices/ (Piper TTS voices)
├── model/ (Vosk model)
└── README-WINDOWS.txt
```

#### 6. Windows Setup Guide
**File:** `docs/WINDOWS_SETUP.md` (new)

Topics:
- Installing JACK for Windows
- Installing JackTrip
- Downloading and running Jackdaw installer
- Configuring hub connection
- Testing microphone/speakers
- Basic voice commands
- Troubleshooting

---

## Phase 2: Full Feature Parity (Future)

### Additional Work Required

#### Music Library Support
- Adapt file scanning for Windows paths (`C:\Users\...`)
- Replace shell scripts with Python equivalents
- Test with Windows audio file locations

#### LLM Integration
- Ollama Windows installation guide
- Simplified model download process
- Test conversation storage on Windows

#### Advanced Plugins
- Icecast streaming (requires Windows Icecast2)
- Buffer recording (test JACK routing on Windows)
- System updates plugin (Windows-specific package managers)

#### Installer Improvements
- Auto-download dependencies (JACK, JackTrip)
- Wizard-style configuration
- Start menu integration
- Auto-start on Windows boot

---

## Testing Checklist

### Before Release 1.1.0 (Linux Polish)
- [ ] All current features stable on Linux
- [ ] Documentation complete and accurate
- [ ] No known critical bugs
- [ ] Memory leaks checked
- [ ] Performance acceptable

### Phase 1 Testing (Windows Client)
Test on Windows 11 machine:
- [ ] Tray app launches without errors
- [ ] JackTrip plugin connects to hub
- [ ] Voice commands work (join/leave room)
- [ ] Audio routing functions in JACK
- [ ] Multiple clients can collaborate
- [ ] Clean shutdown works
- [ ] No process zombies

### Phase 2 Testing (Full Windows Support)
- [ ] Music library scanner works
- [ ] LLM chat functions
- [ ] All plugins operational
- [ ] Installer works for non-technical users

---

## Timeline Estimate

**Release 1.1.0 (Linux Polish):**
- Current focus: Bug fixes, documentation, stability
- Target: Ready for production Linux use

**Release 1.2.0 (Windows Client):**
- Phase 1 implementation: ~2-3 days development
- Testing on Windows: ~1 day
- Documentation: ~1 day
- **Total: ~1 week**

**Release 2.0.0 (Full Windows Parity):**
- Phase 2 implementation: ~1-2 weeks
- Extensive testing: ~3-5 days
- Installer polish: ~2-3 days
- **Total: ~3-4 weeks**

---

## Resources Needed

### Development
- Windows 11 test machine (✓ available)
- JACK for Windows (✓ installed)
- JackTrip for Windows (✓ installed)

### Testing
- Multiple Windows bandmates for beta testing
- Various Windows versions (10, 11)
- Different audio interfaces

### Documentation
- Screenshots on Windows
- Video tutorial for non-technical users
- Quick start guide (1-page)

---

## Success Criteria

### Phase 1 (Minimal Client)
✅ Bandmate can:
1. Run installer
2. Double-click Jackdaw icon
3. Say "Indigo, join jam room [name]"
4. Hear and play with the band
5. Say "Indigo, leave jam room"
6. Close without issues

### Phase 2 (Full Features)
✅ Windows user has feature parity with Linux
✅ No "Linux-only" limitations
✅ Works without command-line knowledge
✅ Reliable enough for live performances

---

## Notes

- Prioritize JackTrip collaboration over music/LLM features
- Keep bandmate experience simple and reliable
- Test with actual non-technical users before release
- Document every step assuming zero Linux knowledge
- Consider creating video tutorials
- Build trust with reliability over feature count

---

## Open Questions

1. **Vosk model download:** Auto-download on Windows or manual?
2. **Piper voices:** Include in installer or separate download?
3. **JACK setup:** Require pre-installed or bundle?
4. **Update mechanism:** Auto-update on Windows?
5. **Telemetry:** Crash reporting for Windows debugging?

---

## Reference Links

- JACK for Windows: https://jackaudio.org/downloads/
- JackTrip: https://github.com/jacktrip/jacktrip
- PyInstaller: https://pyinstaller.org/
- Vosk models: https://alphacephei.com/vosk/models
- Piper voices: https://huggingface.co/rhasspy/piper-voices
