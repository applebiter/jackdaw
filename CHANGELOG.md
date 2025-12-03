# Changelog

All notable changes to Jackdaw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-12-03

### Added - Network Collaboration & Music Management

#### JackTrip Integration
- **JackTrip Hub Server** - Full-featured hub server with authentication, room management, and web patchbay
  - FastAPI-based REST API with bcrypt authentication
  - Single-room collaboration mode
  - Web-based JACK patchbay with zoom, pan, and minimap
  - Automatic client naming and connection management
  - VPS deployment guide for internet collaboration
- **JackTrip Client Plugin** - Voice-controlled client for connecting to hub servers
  - Commands: "start jam session", "stop jam session", "jam session status", "who's in the jam"
  - Automatic JACK routing and connection management
  - GUI status widget in system tray
  - Hub connection status indicator in tray menu
  - Proper cleanup and signal handling

#### Music Library Enhancements
- **Track Metadata Editor** - Standalone widget for editing track information
  - Edit all metadata fields: title, artist, album, genre, year, BPM, composer, producer, etc.
  - Dual-update system: updates both database and file tags
  - Multi-format support: MP3 (ID3), FLAC, OGG Vorbis, M4A/MP4 (iTunes tags)
  - Uses mutagen library for reliable tag writing
  - Non-modal dialog for editing while browsing
- **Format Detection** - Human-readable file format display
  - Added `filetype` column to database
  - Maps extensions to readable names (Ogg Vorbis, FLAC, MP3, Opus, AAC/M4A)
  - Migration script for existing databases
- **Enhanced Search** - More flexible searching options
  - "All Fields" search across title/artist/album/genre
  - BPM search capability
  - Title case display names for field selection
  - Default search changed to Title for better UX
- **Improved Navigation** - Better page controls
  - First/Last page buttons
  - Jump-to-page spinner with Enter key support
  - Handles large libraries (136+ pages) efficiently

#### System Tray Improvements
- **Window Lifecycle Management** - Proper cleanup of all GUI windows
  - Tracks all opened dialogs for cleanup on exit
  - Terminates music browser subprocess on quit
  - No more orphaned windows
- **Widget Independence** - All dialogs can be opened simultaneously
  - Changed from modal to non-modal dialogs
  - Fixed z-order issues
  - Multiple widgets don't block each other
- **Simplified Menu** - Cleaner tray menu organization
  - Removed playback controls from Music submenu (voice-only control)
  - All music control via voice commands for consistency
- **Memory Statistics Tool** - Built-in memory leak detection
  - Shows process RSS/VMS, garbage collection stats
  - Top 15 memory allocations by file:line
  - Refresh button for ongoing monitoring
  - Dark theme for better readability
  - Uses tracemalloc for detailed allocation tracking

#### Documentation
- **Reorganized Documentation** - Better structure and navigation
  - Moved all docs to `docs/` folder
  - Consolidated JackTrip documentation
  - Removed planning/development documents
  - Updated main README with architecture section
- **Windows Compatibility Roadmap** - Plan for cross-platform support
  - Phase 1: JackTrip client for Windows
  - Phase 2: Full feature parity
  - Timeline and resource estimates
- **Improved Voice Command Reference** - Better discoverability
  - Added note about tray menu cheat sheet
  - Mention of command alias customization
  - Links to plugin guide

### Changed
- Separated architecture into "Background Services" and "User Interface" sections in README
- Improved voice command processing and finalization logic
- Enhanced wake word detection debugging

### Fixed
- Wake word processing and utterance finalization
- Silence-triggered finalization timing
- JackTrip client cleanup on shutdown
- Signal handlers for proper cleanup
- Patchbay drag-to-connect functionality
- Volume command documentation (corrected to 20%/50%/80%/95%)

### Technical Improvements
- Better subprocess management with proper cleanup
- Improved error handling in voice recognition
- Enhanced logging for troubleshooting
- Memory tracking at application startup
- Platform-specific considerations documented

---

## [1.0.0] - 2024

Initial release with core functionality:
- Vosk speech recognition with wake word detection
- Ollama LLM integration with conversation history
- Piper TTS for voice responses
- Music library with voice-controlled playback
- Plugin-based architecture
- System tray GUI
- Icecast2 streaming support
- Retroactive buffer recording
- JACK Audio integration

[2.0.0]: https://github.com/applebiter/jackdaw/releases/tag/v2.0.0
[1.0.0]: https://github.com/applebiter/jackdaw/releases/tag/v1.0.0
