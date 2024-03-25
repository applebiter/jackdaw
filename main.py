import time
import whisper
# Imports for realistic voices
import torch
import torchaudio
from tortoise import utils, api
# import torch.nn as nn
# import torch.nn.functional as F
from tortoise.api import TextToSpeech
from tortoise.utils.audio import load_audio, load_voice, load_voices

stt_agent = whisper.load_model("base")
audio_folder = "/home/rick/Workspace/jackdaw/audio"
text_folder = "/home/rick/Workspace/jackdaw/text"

clips_paths = [
    "/home/rick/Workspace/jackdaw/audio/EmmaThompsonClip.mp3",
]

reference_clips = [utils.audio.load_audio(p, 22050) for p in clips_paths]
tts = api.TextToSpeech()
pcm_audio = tts.tts_with_preset(
    "Wonderful, darling! It looks like you done figured it out!", voice_samples=reference_clips, preset='fast')


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
next_game_tick = get_tick_count()
sleep_time = 0
app_is_running = False

while app_is_running:

    # Poll a directory for a new text file
    # if a new file is found, use dome TTS to process it
    # move the text file to a new directory

    # Poll a directory for a new audio file
    # if a new file is found, use Whisper to process it
    # move the audio file to a new directory

    next_game_tick += SKIP_TICKS
    sleep_time = next_game_tick - get_tick_count()

    if sleep_time >= 0:
        time.sleep(sleep_time / 1000)
    else:
        next_game_tick = get_tick_count()
