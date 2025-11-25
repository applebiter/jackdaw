#!/usr/bin/env python3
"""
Voice Assistant Dashboard

A Gradio-based web dashboard for monitoring and controlling the voice assistant system.
Provides real-time log viewing, now playing info, buffer status, and file management.

Usage:
    python gradio_dashboard.py
    
Then open http://localhost:7865 in your browser
"""

import gradio as gr
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import subprocess
import os
from typing import Optional, Dict, List, Tuple


class VoiceAssistantDashboard:
    """Dashboard for monitoring voice assistant system."""
    
    def __init__(self, config_path: str = "voice_assistant_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Paths
        self.logs_dir = Path("logs")
        self.recordings_dir = Path(self.config.get("plugins", {}).get("timemachine", {}).get("output_dir", "~/recordings")).expanduser()
        self.music_db = Path(self.config.get("plugins", {}).get("music_player", {}).get("database_path", "music_library.sqlite3"))
        
        # Log file paths
        self.voice_log = self.logs_dir / "voice_command.log"
        self.llm_log = self.logs_dir / "llm_processor.log"
        self.tts_log = self.logs_dir / "tts_client.log"
        
        # Track last read positions for efficient log tailing
        self.log_positions = {
            "voice": 0,
            "llm": 0,
            "tts": 0
        }
    
    def _load_config(self) -> dict:
        """Load voice assistant configuration."""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return {}
    
    def get_now_playing(self) -> Tuple[str, str]:
        """
        Get currently playing track info from voice command log.
        
        Returns:
            Tuple of (track_info_markdown, album_art_path or None)
        """
        try:
            if not self.voice_log.exists():
                return "No playback information available", None
            
            # Read last 100 lines to find most recent "Now playing"
            with open(self.voice_log, 'r') as f:
                lines = f.readlines()[-100:]
            
            # Find last "Now playing" message
            for line in reversed(lines):
                if "Now playing:" in line or "Playing:" in line:
                    # Extract track info
                    info = line.split("Now playing:")[-1].split("Playing:")[-1].strip()
                    
                    # Format as markdown
                    markdown = f"### 🎵 Now Playing\n\n**{info}**\n\n"
                    
                    # Try to extract artist/album for database lookup
                    # (simplified - could be enhanced)
                    return markdown, None
            
            return "No track currently playing", None
            
        except Exception as e:
            return f"Error getting now playing: {e}", None
    
    def get_buffer_status(self) -> str:
        """Get ring buffer recorder status from logs."""
        try:
            if not self.voice_log.exists():
                return "No buffer status available"
            
            with open(self.voice_log, 'r') as f:
                lines = f.readlines()[-50:]
            
            # Look for buffer messages
            is_running = False
            buffer_info = ""
            
            for line in reversed(lines):
                if "[RingBuffer] Started recording" in line:
                    is_running = True
                    break
                elif "[RingBuffer] Stopped" in line:
                    is_running = False
                    break
                elif "[timemachine] Stopping recorder" in line:
                    is_running = False
                    break
            
            if is_running:
                # Extract buffer details from log
                for line in reversed(lines):
                    if "Buffer:" in line and "seconds" in line:
                        buffer_info = line.split("Buffer:")[-1].strip()
                        break
                
                status = "### 🎙️ Ring Buffer Status\n\n"
                status += "**Status:** 🟢 Recording\n\n"
                if buffer_info:
                    status += f"**Buffer:** {buffer_info}\n"
                status += "\nSay 'save that' to capture the buffer!"
            else:
                status = "### 🎙️ Ring Buffer Status\n\n"
                status += "**Status:** ⚫ Stopped\n\n"
                status += "Say 'start the buffer' to begin recording"
            
            return status
            
        except Exception as e:
            return f"Error getting buffer status: {e}"
    
    def tail_log(self, log_name: str, num_lines: int = 50) -> str:
        """
        Tail a log file efficiently.
        
        Args:
            log_name: Name of log (voice, llm, tts)
            num_lines: Number of recent lines to return
            
        Returns:
            Log content as string
        """
        log_map = {
            "voice": self.voice_log,
            "llm": self.llm_log,
            "tts": self.tts_log
        }
        
        log_path = log_map.get(log_name)
        if not log_path or not log_path.exists():
            return f"Log file not found: {log_path}"
        
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                return ''.join(lines[-num_lines:])
        except Exception as e:
            return f"Error reading log: {e}"
    
    def get_recent_recordings(self) -> List[Tuple[str, str, str]]:
        """
        Get list of recent recordings.
        
        Returns:
            List of (filename, size, date) tuples
        """
        try:
            if not self.recordings_dir.exists():
                return []
            
            recordings = []
            for file_path in sorted(self.recordings_dir.glob("*.wav"), reverse=True)[:20]:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                recordings.append((
                    file_path.name,
                    f"{size_mb:.1f} MB",
                    mtime.strftime("%Y-%m-%d %H:%M:%S")
                ))
            
            return recordings
            
        except Exception as e:
            print(f"Error getting recordings: {e}")
            return []
    
    def get_system_status(self) -> str:
        """Get system status (processes running, JACK status, etc.)."""
        status = "### 🖥️ System Status\n\n"
        
        try:
            # Check if voice assistant processes are running
            pid_file = Path(".voice_assistant.pid")
            if pid_file.exists():
                with open(pid_file) as f:
                    pids = f.read().strip().split()
                
                running = []
                for pid in pids:
                    try:
                        os.kill(int(pid), 0)  # Check if process exists
                        running.append(pid)
                    except:
                        pass
                
                if running:
                    status += f"**Voice Assistant:** 🟢 Running ({len(running)} processes)\n\n"
                else:
                    status += "**Voice Assistant:** 🔴 Stopped\n\n"
            else:
                status += "**Voice Assistant:** 🔴 Not running\n\n"
            
            # Check JACK status
            try:
                result = subprocess.run(
                    ["jack_lsp"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    num_ports = len(result.stdout.strip().split('\n'))
                    status += f"**JACK Audio:** 🟢 Running ({num_ports} ports)\n\n"
                else:
                    status += "**JACK Audio:** 🔴 Not running\n\n"
            except:
                status += "**JACK Audio:** ❓ Unknown\n\n"
            
            # Disk space for recordings
            if self.recordings_dir.exists():
                result = subprocess.run(
                    ["df", "-h", str(self.recordings_dir)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 5:
                            status += f"**Disk Space:** {parts[3]} available ({parts[4]} used)\n\n"
            
        except Exception as e:
            status += f"Error getting system status: {e}\n"
        
        return status
    
    def get_music_stats(self) -> str:
        """Get music library statistics."""
        try:
            if not self.music_db.exists():
                return "Music database not found"
            
            conn = sqlite3.connect(self.music_db)
            cursor = conn.cursor()
            
            stats = "### 📚 Music Library\n\n"
            
            # Count tracks
            cursor.execute("SELECT COUNT(*) FROM tracks")
            track_count = cursor.fetchone()[0]
            stats += f"**Tracks:** {track_count:,}\n\n"
            
            # Count artists
            cursor.execute("SELECT COUNT(DISTINCT artist) FROM tracks WHERE artist IS NOT NULL")
            artist_count = cursor.fetchone()[0]
            stats += f"**Artists:** {artist_count:,}\n\n"
            
            # Count albums
            cursor.execute("SELECT COUNT(DISTINCT album) FROM tracks WHERE album IS NOT NULL")
            album_count = cursor.fetchone()[0]
            stats += f"**Albums:** {album_count:,}\n\n"
            
            # Total duration
            cursor.execute("SELECT SUM(duration) FROM tracks WHERE duration IS NOT NULL")
            total_seconds = cursor.fetchone()[0] or 0
            hours = int(total_seconds // 3600)
            stats += f"**Total Duration:** {hours:,} hours\n\n"
            
            conn.close()
            return stats
            
        except Exception as e:
            return f"Error getting music stats: {e}"
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        
        with gr.Blocks(title="Voice Assistant Dashboard", theme=gr.themes.Glass(primary_hue="blue", secondary_hue="purple")) as dashboard:
            gr.Markdown("# 🎤 Voice Assistant Dashboard")
            gr.Markdown("Real-time monitoring and control for your JACK voice assistant system")
            
            with gr.Tabs():
                # Overview Tab
                with gr.Tab("📊 Overview"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            system_status = gr.Markdown(
                                value=self.get_system_status(),
                                every=5
                            )
                        
                        with gr.Column(scale=1):
                            now_playing = gr.Markdown(
                                value=self.get_now_playing()[0],
                                every=2
                            )
                        
                        with gr.Column(scale=1):
                            buffer_status = gr.Markdown(
                                value=self.get_buffer_status(),
                                every=3
                            )
                    
                    with gr.Row():
                        music_stats = gr.Markdown(
                            value=self.get_music_stats(),
                            every=30
                        )
                
                # Logs Tab
                with gr.Tab("📋 Logs"):
                    with gr.Row():
                        log_refresh_btn = gr.Button("🔄 Refresh Logs")
                    
                    with gr.Tabs():
                        with gr.Tab("Voice Commands"):
                            voice_log_box = gr.Textbox(
                                label="Voice Command Log (last 50 lines)",
                                value=lambda: self.tail_log("voice", 50),
                                lines=25,
                                max_lines=25,
                                interactive=False,
                                every=3
                            )
                        
                        with gr.Tab("LLM Processor"):
                            llm_log_box = gr.Textbox(
                                label="LLM Processor Log (last 50 lines)",
                                value=lambda: self.tail_log("llm", 50),
                                lines=25,
                                max_lines=25,
                                interactive=False,
                                every=5
                            )
                        
                        with gr.Tab("TTS Client"):
                            tts_log_box = gr.Textbox(
                                label="TTS Client Log (last 50 lines)",
                                value=lambda: self.tail_log("tts", 50),
                                lines=25,
                                max_lines=25,
                                interactive=False,
                                every=5
                            )
                
                # Recordings Tab
                with gr.Tab("🎙️ Recordings"):
                    gr.Markdown("### Recent Ring Buffer Recordings")
                    
                    recordings_table = gr.Dataframe(
                        headers=["Filename", "Size", "Date"],
                        value=self.get_recent_recordings,
                        every=5,
                        interactive=False
                    )
                    
                    recordings_refresh_btn = gr.Button("🔄 Refresh Recordings")
                    recordings_refresh_btn.click(
                        fn=self.get_recent_recordings,
                        outputs=recordings_table
                    )
                    
                    recordings_path = gr.Textbox(
                        label="Recordings Directory",
                        value=str(self.recordings_dir),
                        interactive=False
                    )
                
                # Configuration Tab
                with gr.Tab("⚙️ Configuration"):
                    config_display = gr.JSON(
                        label="Current Configuration",
                        value=self.config
                    )
                    
                    gr.Markdown(f"""
                    ### Configuration File
                    
                    **Path:** `{self.config_path}`
                    
                    To modify configuration:
                    1. Stop the voice assistant
                    2. Edit `voice_assistant_config.json`
                    3. Restart the voice assistant
                    """)
            
            gr.Markdown("""
            ---
            ### 💡 Tips
            
            - **Real-time Updates:** Most panels refresh automatically
            - **Remote Access:** Access from any device on your network at `http://YOUR_IP:7865`
            - **Logs:** View live logs without SSH access
            - **Recordings:** Browse and download saved audio files
            
            ### 🎯 Quick Commands
            
            - "indigo, start the buffer" - Start ring buffer recording
            - "indigo, save that" - Save last 30 seconds
            - "indigo, play artist pink floyd" - Play music
            - "indigo, hey" - Talk to LLM
            """)
        
        return dashboard


def main():
    """Main entry point."""
    print("Starting Voice Assistant Dashboard...")
    print("=" * 60)
    
    # Create dashboard
    dashboard = VoiceAssistantDashboard()
    interface = dashboard.create_interface()
    
    # Launch with custom port
    print("\n🚀 Dashboard launching on http://localhost:7865")
    print("   Access from network: http://YOUR_IP:7865")
    print("\nPress Ctrl+C to stop the dashboard\n")
    
    interface.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7865,
        share=True,  # Create public Gradio link
        inbrowser=False  # Set to True to auto-open browser
    )


if __name__ == "__main__":
    main()
