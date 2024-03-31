import json
import os
import time
import whisper

project_root = os.path.dirname(__file__)
input_audio_folder = f"{project_root}/jackdaw/input"
input_audio = f"{input_audio_folder}/input.ogg"
output_text_folder = f"{project_root}/jackdaw/output"
output_text = f"{output_text_folder}/output.txt"
stt_agent = whisper.load_model("base")
tts_agent = None


def get_tick_count() -> int:
    """returns the current number of milliseconds that have elapsed since the
    game started without using a third-party like PyGame
    """

    return int(time.time() * 1000)


def fetch_new_text_file():
    """Poll a directory for a new text file
    """


def fetch_new_audio_file():
    """Poll a directory for a new audio file

    1. If a new file is found, use Whisper to process it
        Use Python's functions to scan a directory for new files
        Collect the path of the new file(s) and store it in a list
        Use Whisper to process each audio file, one at a time, and return the text for each transcription using a \
            generator (yield)
    """

FRAMES_PER_SECOND = 25
SKIP_TICKS = 1000
next_app_tick = get_tick_count()
sleep_time = 0
app_is_running = False

while app_is_running:

    # Poll a directory for a new text file
    # if a new file is found, use MaryTTS to process it
    # move the text file to a new directory

    # Poll a directory for a new audio file
    # if a new file is found, use Whisper to process it
    # move the audio file to a new directory
    if os.path.isfile(input_audio):
        result = stt_agent.transcribe(f"{input_audio}")

        with open(output_text, "w") as output:
            output.write(result["text"])
            
        os.remove(input_audio)

    next_app_tick += SKIP_TICKS
    sleep_time = next_app_tick - get_tick_count()

    if sleep_time >= 0:
        time.sleep(sleep_time / 1000)
    else:
        next_app_tick = get_tick_count()
