# importing libraries
import sounddevice as sd
import wavio
import tkinter as tk
import numpy as np
from tkinter import messagebox


# creating class for recording
class AudioRecorder:

    # creating an constructor
    def __init__(self):
        self.frames = []
        self.is_recording = False

    # creating method to start recording
    def start_recording(self):
        self.frames = []
        self.is_recording = True
        sd.default.samplerate = 44100
        sd.default.channels = 2
        self.stream = sd.InputStream(callback=self.callback)
        self.stream.start()

    # creating method to stop recording
    def stop_recording(self):
        self.is_recording = False
        sd.stop()

    # creating method to save recording
    def save_recording(self, filename):
        if self.frames:
            wavio.write(filename, np.array(self.frames), 44100, sampwidth=2)
            messagebox.showinfo("Success", "Recording saved successfully.")
        else:
            messagebox.showwarning("Warning", "No recording to save.")

    def callback(self, indata, frames, time, status):
        if self.is_recording:
            self.frames.extend(indata.copy())


# creating GUI functions
def start_recording():
    global recorder
    recorder.start_recording()
    record_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)


def stop_recording():
    global recorder
    recorder.stop_recording()
    record_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


def save_recording():
    global recorder
    filename = file_entry.get()
    if filename.strip() == "":
        messagebox.showerror("Error", "Please enter a filename.")
    else:
        recorder.save_recording(filename + ".wav")


# Create main window
root = tk.Tk()
root.title("Audio Recorder")

# Create recorder instance
recorder = AudioRecorder()

# Create UI elements
record_button = tk.Button(root, text="Start Recording", command=start_recording)
stop_button = tk.Button(root, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
save_button = tk.Button(root, text="Save Recording", command=save_recording)
file_label = tk.Label(root, text="Enter Filename:")
file_entry = tk.Entry(root)

# Arrange UI elements
record_button.grid(row=0, column=0, padx=5, pady=5)
stop_button.grid(row=0, column=1, padx=5, pady=5)
save_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
file_label.grid(row=2, column=0, padx=5, pady=5)
file_entry.grid(row=2, column=1, padx=5, pady=5)

# Start the Tkinter event loop
root.mainloop()
