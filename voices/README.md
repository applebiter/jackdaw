# Piper TTS Voice Models

This directory should contain Piper text-to-speech voice models.

## Download

**Primary Source (HuggingFace):**
1. Visit: https://huggingface.co/rhasspy/piper-voices/tree/main/en
2. Navigate to your desired language folder (e.g., `en/en_US/`)
3. Select a voice (e.g., `lessac/medium/`)
4. Download **BOTH** files:
   - Click on the `.onnx` file → Click "Download" button
   - Click on the `.onnx.json` file → Click "Download" button

**Alternative (GitHub Releases):**
- Visit: https://github.com/rhasspy/piper/releases
- Browse voice samples: https://rhasspy.github.io/piper-samples/

## Important

**Always download BOTH files for each voice:**
- `voice-name.onnx` - The model file
- `voice-name.onnx.json` - The configuration file (required!)

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

## Installation

**From HuggingFace (recommended):**
```bash
cd voices/

# Example: Download lessac voice from HuggingFace
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

**Or from GitHub Releases:**
```bash
cd voices/

# Example: Download from GitHub release
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json
```

## Structure

After downloading, this directory should contain:
```
voices/
├── README.md (this file)
├── en_US-lessac-medium.onnx
├── en_US-lessac-medium.onnx.json
├── en_US-amy-medium.onnx
├── en_US-amy-medium.onnx.json
└── ... (other voices)
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
