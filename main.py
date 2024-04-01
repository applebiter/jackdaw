import os
import subprocess
import time
import ollama
import requests
import whisper

project_root = os.path.dirname(__file__)
jacklab = f"{project_root}/jacklab"
input_folder = f"{project_root}/input"
output_folder = f"{project_root}/output"
whisperer = whisper.load_model("base")


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


SKIP_TICKS = 3000
next_app_tick = get_tick_count()
sleep_time = 0
delete_output_audio = False
app_is_running = True

while app_is_running:

    # 1. Check if the output audio file exists, if it does, delete it
    if os.path.isfile(f"{output_folder}/output.wav"):
        if delete_output_audio:
            print("Found output audio to delete...")
            os.remove(f"{output_folder}/output.wav")
            print("Output audio deleted, waiting for user input...")
            delete_output_audio = False

    # 2. Input audio comes from user, goes to Whisper for processing
    if os.path.isfile(f"{input_folder}/input.wav"):
        print("Found input audio to process...")
        result = whisperer.transcribe(f"{input_folder}/input.wav")

        with open(f"{output_folder}/output.txt", "w") as output:
            text_out = result["text"]
            output.write(text_out)

        os.remove(f"{input_folder}/input.wav")
        time.sleep(0.5)

    # 3. Output text comes from Whisper, goes to Ollama for processing
    if os.path.isfile(f"{output_folder}/output.txt"):
        with open(f"{output_folder}/output.txt", "r") as text_file:
            text = text_file.read()

        priming = "The user will only receive the first 1000 characters from each of the assistant's responses, so please be brief."
        response = ollama.chat(
            model='dolphin-mistral:7b', messages=[
                {'role': 'system', 'content': priming},
                {'role': 'user', 'content': text}
            ], options={'temperature': 1}, keep_alive='10m'
        )

        # 4. Output text from Ollama gets written to input text folder
        with open(f"{input_folder}/input.txt", "w") as input_file:
            input_file.write(response['message']['content'][:1000])

        os.remove(f"{output_folder}/output.txt")
        time.sleep(0.5)

    # 5. Input text comes from language model, goes to MaryTTS for processing
    if os.path.isfile(f"{input_folder}/input.txt"):
        print("Found input text to process...")
        with open(f"{input_folder}/input.txt", "r") as text_file:
            text = text_file.read()

        response = requests.post(
            "http://192.168.32.12:5920/process",
            data={
                "INPUT_TYPE": "TEXT",
                "INPUT_TEXT": text,
                "OUTPUT_TYPE": "AUDIO",
                "AUDIO": "WAVE_FILE",
                "LOCALE": "en_US",
                "VOICE": "cmu-slt-hsmm",
            },
            timeout=None,
            headers={"Content-Type": "application/json"},
        )

        with open(f"{output_folder}/raw.wav", "wb") as audio_file:
            audio_file.write(response.content)
            time.sleep(0.5)

        result = subprocess.run(
            [
                "sox", f"{output_folder}/raw.wav", "--rate", "44.1k",
                "--channels", "2", f"{output_folder}/output.wav"
            ],
            capture_output=True, text=True
        )
        print(result.stdout)
        time.sleep(0.5)

        if os.path.isfile(f"{output_folder}/output.wav"):
            os.remove(f"{output_folder}/raw.wav")
            delete_output_audio = True

        os.remove(f"{input_folder}/input.txt")
        time.sleep(0.5)

    # 6. Output audio comes from MaryTTS, gets played
    if os.path.isfile(f"{output_folder}/output.wav"):
        print("Found output audio to play...")
        result = subprocess.run(
            [
                "python", f"{jacklab}/play_file.py", "-c", "jackdaw",
                f"{output_folder}/output.wav"
            ],
            capture_output=True, text=True
        )
        print(result.stdout)
        time.sleep(0.5)

    next_app_tick += SKIP_TICKS
    sleep_time = next_app_tick - get_tick_count()

    if sleep_time >= 0:
        time.sleep(sleep_time / 1000)
    else:
        next_app_tick = get_tick_count()
