"""
Icecast2 Streaming Plugin for Jackdaw

Streams audio to an Icecast2 server using FFmpeg for encoding.
Creates a JACK client with stereo input that accepts connections
from any audio source in the JACK graph.
"""

from plugin_base import VoiceAssistantPlugin
import subprocess
import logging
import time
import threading

logger = logging.getLogger(__name__)


class IcecastStreamerPlugin(VoiceAssistantPlugin):
    """
    Streams audio to Icecast2 server using FFmpeg for encoding.
    Creates a JACK client with stereo input that accepts connections
    from any audio source in the JACK graph.
    """
    
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.streaming_process = None
        self.monitor_thread = None
        self.is_streaming = False
        self.should_monitor = False
        
        plugin_config = config_manager.get("plugins", {}).get("icecast_streamer", {})
        self.host = plugin_config.get("host", "localhost")
        self.port = plugin_config.get("port", 8000)
        self.password = plugin_config.get("password", "hackme")
        self.mount = plugin_config.get("mount", "/jackdaw.ogg")
        self.bitrate = plugin_config.get("bitrate", 128)
        self.format = plugin_config.get("format", "ogg")  # ogg (vorbis), opus, flac, mp3
        
        # Validate format - supporting Xiph.org formats plus MP3
        valid_formats = ["ogg", "opus", "flac", "mp3"]
        if self.format not in valid_formats:
            logger.warning(f"Invalid format '{self.format}', defaulting to 'ogg'. Valid formats: {', '.join(valid_formats)}")
            self.format = "ogg"
    
    def get_name(self):
        return "icecast_streamer"
    
    def get_description(self):
        return "Stream audio to Icecast2 server"
    
    def get_commands(self):
        return {
            "start streaming": self._start_stream,
            "stop streaming": self._stop_stream,
            "stream status": self._stream_status,
            "begin broadcast": self._start_stream,
            "end broadcast": self._stop_stream,
            "streaming status": self._stream_status,
        }
    
    def _start_stream(self):
        """Start streaming to Icecast2 server"""
        if self.is_streaming:
            logger.info("Already streaming")
            return "Already streaming"
        
        try:
            # Determine codec and content type based on format
            # Supporting Xiph.org formats: Ogg Vorbis, Opus, FLAC
            if self.format == "mp3":
                codec = "libmp3lame"
                content_type = "audio/mpeg"
                ffmpeg_format = "mp3"
            elif self.format == "opus":
                codec = "libopus"
                content_type = "audio/ogg"  # Opus in Ogg container
                ffmpeg_format = "ogg"
            elif self.format == "flac":
                codec = "flac"
                content_type = "audio/flac"
                ffmpeg_format = "flac"
            else:  # ogg (vorbis)
                codec = "libvorbis"
                content_type = "application/ogg"
                ffmpeg_format = "ogg"
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-f', 'jack',
                '-channels', '2',
                '-i', 'IcecastStreamer',  # JACK client name
                '-acodec', codec,
            ]
            
            # FLAC doesn't use bitrate (lossless), others do
            if self.format != "flac":
                cmd.extend(['-b:a', f'{self.bitrate}k'])
            
            # Add remaining parameters
            cmd.extend([
                '-content_type', content_type,
                '-f', ffmpeg_format,
                f'icecast://source:{self.password}@{self.host}:{self.port}{self.mount}'
            ])
            
            logger.info(f"Starting stream with command: {' '.join(cmd[:10])}...")  # Don't log password
            
            self.streaming_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait longer to check if it starts successfully
            time.sleep(2.0)
            if self.streaming_process.poll() is not None:
                # Process died immediately
                stderr_output = self.streaming_process.stderr.read()
                stdout_output = self.streaming_process.stdout.read()
                error_msg = f"FFmpeg failed to start. Exit code: {self.streaming_process.returncode}"
                if stderr_output:
                    error_msg += f"\nStderr: {stderr_output[:1000]}"
                if stdout_output:
                    error_msg += f"\nStdout: {stdout_output[:500]}"
                logger.error(error_msg)
                print(f"[IcecastStreamer] ERROR:\n{error_msg}")
                
                # Also write to a file for debugging
                try:
                    with open("logs/icecast_error.log", "a") as f:
                        import datetime
                        f.write(f"\n{'='*60}\n")
                        f.write(f"{datetime.datetime.now()}\n")
                        f.write(error_msg)
                        f.write(f"\n{'='*60}\n")
                except Exception:
                    pass
                
                self.streaming_process = None
                return f"Failed to start stream - check logs/icecast_error.log"
            
            # Start monitoring thread
            self.should_monitor = True
            self.monitor_thread = threading.Thread(target=self._monitor_stream, daemon=True)
            self.monitor_thread.start()
            
            self.is_streaming = True
            logger.info(f"Started streaming to {self.host}:{self.port}{self.mount}")
            print(f"[IcecastStreamer] FFmpeg started successfully, JACK client 'IcecastStreamer' should now be available")
            return "Stream started"
            
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install ffmpeg with JACK support.")
            return "Error: FFmpeg not installed"
        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            return f"Failed to start stream: {e}"
    
    def _monitor_stream(self):
        """Monitor the streaming process for errors"""
        while self.should_monitor and self.streaming_process:
            # Check if process has terminated
            if self.streaming_process.poll() is not None:
                # Process has ended
                stderr_output = self.streaming_process.stderr.read()
                stdout_output = self.streaming_process.stdout.read()
                
                if stderr_output:
                    logger.error(f"Stream process stderr: {stderr_output}")
                    print(f"[IcecastStreamer] FFmpeg stderr:\n{stderr_output}")
                if stdout_output:
                    logger.info(f"Stream process stdout: {stdout_output}")
                    
                exit_code = self.streaming_process.returncode
                if exit_code != 0:
                    logger.error(f"Stream process exited with code {exit_code}")
                    print(f"[IcecastStreamer] FFmpeg exited with code {exit_code}")
                else:
                    logger.info("Stream process ended normally")
                
                self.is_streaming = False
                self.streaming_process = None
                break
            
            time.sleep(1)
    
    def _stop_stream(self):
        """Stop streaming"""
        if not self.is_streaming:
            logger.info("Not currently streaming")
            return "Not streaming"
        
        try:
            self.should_monitor = False
            
            if self.streaming_process:
                self.streaming_process.terminate()
                try:
                    self.streaming_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Stream process didn't terminate, killing it")
                    self.streaming_process.kill()
                    self.streaming_process.wait()
                
                self.streaming_process = None
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2)
            
            self.is_streaming = False
            logger.info("Stream stopped")
            return "Stream stopped"
            
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return f"Error stopping stream: {e}"
    
    def _stream_status(self):
        """Report streaming status"""
        if self.is_streaming:
            return f"Streaming to {self.host}:{self.port}{self.mount} at {self.bitrate} kilobits per second"
        else:
            return "Not currently streaming"
    
    def cleanup(self):
        """Cleanup when plugin is unloaded"""
        if self.is_streaming:
            self._stop_stream()


def create_plugin(config_manager):
    return IcecastStreamerPlugin(config_manager)
