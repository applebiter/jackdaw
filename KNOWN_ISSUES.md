# Known Issues

This document tracks known bugs, limitations, and platform-specific issues in Jackdaw.

---

## Web Patchbay

### Chrome/Chromium Browser Issues

**Problem:** The JACK web patchbay does not work correctly in Google Chrome or Chromium-based browsers.

**Symptoms:**
- Drag-to-connect functionality fails
- Connection lines don't render properly
- Interface elements may not respond to mouse events

**Workaround:** Use **Mozilla Firefox** instead. The patchbay has been tested and works correctly in Firefox.

**Status:** Under investigation. May be related to Chrome's canvas rendering or event handling differences.

**Affected Versions:** All versions with web patchbay (v2.0.0+)

---

## Windows Platform

### Limited Testing

**Problem:** Windows support is newly added and has limited real-world testing.

**Status:** Windows compatibility layer implemented in v2.0.0+, but needs community testing.

**Known Limitations:**
- Music library scanning not tested with Windows paths
- LLM chat (Ollama) setup not documented for Windows
- Some plugins may have Linux-specific dependencies

**Recommendation:** Windows users should focus on JackTrip client functionality for now.

---

## JackTrip Hub Connection Indicator

### Status Not Updating

**Problem:** The "Hub Connection" indicator in the system tray menu may not change from ○ to ● when connected.

**Symptoms:**
- Connection works correctly
- Audio routes properly
- Status indicator remains as empty circle (○)

**Impact:** Cosmetic only - does not affect functionality

**Status:** TODO - needs signal/slot mechanism for status updates instead of polling

**Workaround:** Use voice command "jam session status" to verify connection

**Affected Versions:** v2.0.0+

---

## Platform-Specific Issues

### Linux

**None currently known**

### macOS

**Status:** Not tested. Platform abstraction layer supports macOS, but no testing has been performed.

---

## Reporting Issues

Found a bug? Please report it on GitHub:

**https://github.com/applebiter/jackdaw/issues**

Include:
- Your platform (Linux distro, Windows version, macOS version)
- Jackdaw version (from git tag or release)
- Steps to reproduce
- Log files from `logs/` directory
- JACK configuration details

---

## Workarounds and Solutions

This section will be updated as workarounds are discovered for common issues.

### Issue: Vosk Model Not Loading

**Solution:** Ensure model structure is correct:
```
model/
├── am/
│   └── final.mdl
├── conf/
│   ├── mfcc.conf
│   └── model.conf
├── graph/
│   └── ...
└── ivector/
    └── ...
```

### Issue: JACK Ports Not Connecting

**Solution:** 
1. Check JACK is running: `jack_lsp`
2. Verify Jackdaw processes are running
3. Use QjackCtl or `jack_lsp -c` to view connections
4. Manually connect in QjackCtl patchbay if needed

### Issue: Wake Word Not Detected

**Solutions:**
- Speak clearly and pause after wake word
- Check microphone level in JACK mixer
- Try different wake word in config
- Reduce background noise
- Check `logs/voice_command.log` for recognition results

---

## Fixed Issues (Historical)

This section documents issues that have been resolved in released versions.

### Volume Documentation Mismatch (Fixed in v2.0.0)
- **Issue:** Documentation showed wrong percentages (30/60/90 vs 20/50/80)
- **Fixed:** Commit b9a2e1d
- **Solution:** Documentation corrected to match implementation

### Widget Z-Order Issues (Fixed in v2.0.0)
- **Issue:** Dialog windows blocked each other
- **Fixed:** Commit f71bedc
- **Solution:** Changed all dialogs to non-modal

### Orphaned Windows on Exit (Fixed in v2.0.0)
- **Issue:** GUI windows remained open after tray app quit
- **Fixed:** Commit df814c6
- **Solution:** Window tracking and cleanup on exit

---

Last Updated: 2025-12-03
