# Piper TTS Voice Models

This directory should contain Piper text-to-speech voice models.

## Quick Installation (Recommended)

Run these commands from the jackdaw directory:

```bash
cd voices/

# Download the recommended voice (lessac - clear and professional)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Verify you got both files
ls -lh en_US-lessac-medium.*
# Should show two files: .onnx and .onnx.json

cd ..
```

**That's it!** The voice is now installed and ready to use.

### Want a Different Voice?

**Listen to samples first:** https://rhasspy.github.io/piper-samples/

**Then download from HuggingFace:**
1. Visit: https://huggingface.co/rhasspy/piper-voices/tree/main/en
2. Navigate to your desired language folder (e.g., `en/en_US/`)
3. Select a voice (e.g., `amy/medium/`)
4. Download **BOTH** files:
   - Click on the `.onnx` file → Click "Download" button
   - Click on the `.onnx.json` file → Click "Download" button
5. Place both files in the `voices/` directory

**Alternative (Command Line):**
```bash
cd voices/
# Replace with your chosen voice URL
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
cd ..
```

## ⚠️ IMPORTANT

**Always download BOTH files for each voice:**
- `voice-name.onnx` - The model file (~20-30 MB)
- `voice-name.onnx.json` - The configuration file (required!)

**Missing the .json file?** Jackdaw will fail to start with an error!

## Recommended Voices

**English (US):**
- `en_US-lessac-medium` - Clear, professional (recommended)
- `en_US-amy-medium` - Friendly, conversational
- `en_US-arctic-medium` - Neutral, clear
- `en_US-joe-medium` - Male voice

**Quality Levels:**
- `low` - Fastest, lower quality (~5-10 MB)
- `medium` - Balanced speed/quality (~20-30 MB)
- `high` - Best quality, slower (~50-100 MB)

## Download Multiple Voices (Optional)

You can install multiple voices and switch between them in the config:

```bash
cd voices/

# Amy voice (friendly, conversational)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# Joe voice (male)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json

cd ..
```

## Directory Structure

After downloading, this directory should look like:
```
voices/
├── README.md (this file)
├── en_US-lessac-medium.onnx
├── en_US-lessac-medium.onnx.json
├── en_US-amy-medium.onnx (optional)
├── en_US-amy-medium.onnx.json (optional)
└── ... (other voices you download)
```

## Configuration

The voice model is configured in `voice_assistant_config.json`:

```json
{
  "voice": {
    "synthesis": {
      "model_path": "voices/en_US-lessac-medium.onnx"
    }
  }
}
```

**To switch voices:** Change `model_path` to point to a different `.onnx` file:

```bash
nano voice_assistant_config.json
```

Examples:
- `"voices/en_US-lessac-medium.onnx"` - Professional, clear
- `"voices/en_US-amy-medium.onnx"` - Friendly, conversational
- `"voices/en_US-joe-medium.onnx"` - Male voice

Restart Jackdaw after changing voices.

## Voice Samples

Listen to samples before downloading:
https://rhasspy.github.io/piper-samples/

## Troubleshooting

**"Voice model not found" error:**
- Ensure both `.onnx` and `.onnx.json` files are present
- Check that `model_path` in config points to the correct file
- Verify file names match exactly (case-sensitive)

**"Missing config file" error:**
- Download the `.onnx.json` file (often forgotten!)
- Ensure it has the same base name as the `.onnx` file

## Other Languages

Piper supports many languages:
- Spanish (es_ES, es_MX)
- French (fr_FR)
- German (de_DE)
- Italian (it_IT)
- Portuguese (pt_BR)
- Russian (ru_RU)
- Chinese (zh_CN)
- And many more!

Visit the Piper samples page to explore available voices.
