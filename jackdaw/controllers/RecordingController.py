import os
from configparser import ConfigParser
import sounddevice as sd
import wavio
import numpy as np


class RecordingController:
    """Controller for recording"""

    def __init__(self):
        """"""

        self.frames = []
        self.is_recording = False
        self.stream = None
        self.device = None
        self.samplerate = None
        self.channels = None
        self.save_folder = None

        try:

            config = ConfigParser()
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(__file__))
            )
            config.read(f"{project_root}/config.cfg")
            self.device = config.get("recording", "device")
            self.samplerate = config.getint("recording", "samplerate")
            self.channels = config.getint("recording", "channels")
            self.save_folder = config.get("input", "root")

        except Exception as e:
            raise e

    def start(self):
        """Start recording"""
        self.frames = []
        self.is_recording = True
        sd.default.device = self.device
        sd.default.samplerate = self.samplerate
        sd.default.channels = self.channels
        self.stream = sd.InputStream(callback=self.callback)
        self.stream.start()

    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        sd.stop()
        self.save_recording()

    def save_recording(self):
        """Save the recording to a file"""
        if self.frames:
            wavio.write(
                f"{self.save_folder}/input.wav", np.array(self.frames),
                self.samplerate, sampwidth=self.channels
            )

    def callback(self, indata, frames, time, status):
        """Callback for recording"""
        if self.is_recording:
            self.frames.extend(indata.copy())
