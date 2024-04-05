import os
import re
import subprocess
import threading
import time
from configparser import ConfigParser
from os.path import realpath
import requests
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import whisper
from jackdaw import Jackdaw

# Load the configuration
filepath = realpath(__file__)
project_root = os.path.dirname(filepath)
config = ConfigParser()
config.read(f"{project_root}/config.cfg")
# Database connectivity
user = config.get("postgresql", "user")
password = config.get("postgresql", "password")
host = config.get("postgresql", "host")
port = config.get("postgresql", "port")
database = config.get("postgresql", "database")
# Jackdaw application launch
# jackdaw = Jackdaw(f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}")
jackdaw = Jackdaw(f"sqlite:///{database}.db")
# plumbing
export_folder = config.get("export", "root")
output_folder = config.get("output", "root")
input_folder = config.get("input", "root")
scripts_root = f"{project_root}/scripts"
# openai-whisper
whisperer = whisper.load_model("base")


def get_tick_count() -> int:
    """Return the current number of milliseconds that have elapsed since the app started"""
    return int(time.time() * 1000)


def delete_output_audio_file(path_to_audio_file: str):
    """Delete the output audio file if it exists"""
    if os.path.isfile(path_to_audio_file):
        os.remove(path_to_audio_file)


def start_recording():
    if not jackdaw("recording").is_recording:
        jackdaw("recording").start()


def stop_recording():
    if jackdaw("recording").is_recording:
        jackdaw("recording").stop_recording()


def transcribe_audio(input_root: str, output_root: str):
    global check_for_input_audio
    transcription = whisperer.transcribe(f"{input_root}/input.wav")
    os.remove(f"{input_root}/input.wav")
    check_for_input_audio = False
    with open(f"{output_root}/transcription.txt", "w") as output:
        text_out = transcription["text"]
        output.write(text_out)
        return True


def quit_jackdaw():
    global app_is_running
    app_is_running = False


def run_once():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    icon = QIcon(f"{project_root}/icons/jackdaw.svg")
    # Create the tray
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)
    # Create the menu
    menu = QMenu()
    act_start_recording = QAction("Start Recording")
    act_start_recording.triggered.connect(start_recording)
    menu.addAction(act_start_recording)
    act_stop_recording = QAction("Stop Recording")
    act_stop_recording.triggered.connect(stop_recording)
    menu.addAction(act_stop_recording)
    act_quit = QAction("Quit")
    act_quit.triggered.connect(quit_jackdaw)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)
    # Add the menu to the tray
    tray.setContextMenu(menu)
    app.exec()


# Start GUI tray application
gui = threading.Thread(target=run_once)
gui.start()
gui_started = True
# Start main loop
SKIP_TICKS = 3000
next_app_tick = get_tick_count()
sleep_time = 0
delete_output_audio = False
check_for_input_audio = True
check_for_transcription = False
session_uuid = None
chat_is_running = False
app_is_running = True

while app_is_running:

    # 2. Check if the output audio file exists, if it does, delete it
    if delete_output_audio:
        delete_output_audio_file(f"{output_folder}/output.wav")
        delete_output_audio = False
        check_for_input_audio = True

    # 3. Input audio comes from user, goes to Whisper for processing
    if check_for_input_audio:
        if os.path.isfile(f"{input_folder}/input.wav"):
            print("Found input query...")
            check_for_transcription = transcribe_audio(
                input_folder, output_folder
            )

    # 4. Output text comes from Whisper, goes to Ollama for processing
    if check_for_transcription:
        if os.path.isfile(f"{output_folder}/transcription.txt"):
            transcript = f"{output_folder}/transcription.txt"
            with open(transcript, "r") as file:
                txt = file.read()
            print("Sending transcribed query to the LLM...")
            # priming = "The user will only receive the first 1500 characters \
            #            from each of the assistant's responses, so please be \
            #            brief."
            priming = "The user will only receive the first 2500 characters of the assistant's response, so please \
                            be brief where possible."
            session_uuid = jackdaw("assistant").session_uuid if session_uuid is None else session_uuid
            resp = jackdaw("assistant").chat(
                priming=priming, prompt=txt, temperature=1.0,
                session_uuid=session_uuid
            )
            with open(f"{input_folder}/input.txt", "w") as input_file:
                input_file.write(resp['message']['content'][:2500])
            os.remove(f"{output_folder}/transcription.txt")
            check_for_transcription = False

    # 5. Input text comes from language model, goes to MaryTTS for processing
    if os.path.isfile(f"{input_folder}/input.txt"):
        print("Synthesizing LLM's response into speech...")
        with open(f"{input_folder}/input.txt", "r") as text_file:
            text = text_file.read()
        request_url = config.get("marytts", "request_url")
        voice = config.get("marytts", "voice")
        rate = config.get("marytts", "rate")
        response = requests.post(
            request_url,
            data={
                "INPUT_TYPE": "TEXT",
                "INPUT_TEXT": text,
                "OUTPUT_TYPE": "AUDIO",
                "AUDIO": "WAVE_FILE",
                "LOCALE": "en_US",
                "VOICE": voice,
                "effect_durScale_selected": "on",
                "effect_durScale_parameters": f"{rate}",
            },
            timeout=None,
            headers={"Content-Type": "application/json"},
        )

        with open(f"{output_folder}/raw.wav", "wb") as audio_file:
            audio_file.write(response.content)
            time.sleep(0.25)

        samplerate = config.get("recording", "samplerate")
        channels = config.get("recording", "channels")
        result = subprocess.run(
            [
                "sox", f"{output_folder}/raw.wav", "--rate", f"{samplerate}",
                "--channels", f"{channels}", f"{output_folder}/output.wav"
            ],
            capture_output=True, text=True
        )
        time.sleep(0.25)

        if os.path.isfile(f"{output_folder}/output.wav"):
            os.remove(f"{output_folder}/raw.wav")

        os.remove(f"{input_folder}/input.txt")
        time.sleep(0.25)

    # 6. Output audio comes from MaryTTS, gets played
    if os.path.isfile(f"{output_folder}/output.wav"):
        print("Found output audio to play...")
        result = subprocess.run(
            [
                "python", f"{scripts_root}/play_file.py", "-c", "jackdaw",
                f"{output_folder}/output.wav"
            ],
            capture_output=True, text=True
        )
        os.remove(f"{output_folder}/output.wav")
        delete_output_audio = True
        check_for_input_audio = True
        time.sleep(0.25)

    next_app_tick += SKIP_TICKS
    sleep_time = next_app_tick - get_tick_count()

    if sleep_time >= 0:
        time.sleep(sleep_time / 1000)
    else:
        next_app_tick = get_tick_count()
