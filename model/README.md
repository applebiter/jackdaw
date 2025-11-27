# Vosk Speech Recognition Model

This directory should contain a Vosk speech recognition model for English.

## Recommended Model

For native English speakers, we recommend **vosk-model-small-en-us-0.15** (or the latest small English model).

This is a lightweight model (~40MB) that provides:
- Good accuracy for voice commands
- Fast recognition speed
- Low latency (~150ms)
- Minimal resource usage

## Installation

### Quick Install (Recommended)

Run these commands from the jackdaw directory:

```bash
# Download the model (40 MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

# Extract it
unzip vosk-model-small-en-us-0.15.zip

# Move files to model directory
rm -rf model/*  # Clear placeholder files
mv vosk-model-small-en-us-0.15/* model/

# Clean up
rm vosk-model-small-en-us-0.15.zip
rmdir vosk-model-small-en-us-0.15
```

**That's it!** The model is now installed.

### Manual Installation

1. Visit https://alphacephei.com/vosk/models
2. Download **vosk-model-small-en-us-0.15** (or the current small US English model)
3. Extract the downloaded archive
4. Copy/move all the extracted files into this `model/` directory

### Verify Installation

After installation, this directory should contain:
- `am/` - Acoustic model files
- `conf/` - Configuration files
- `graph/` - Language model graph
- `ivector/` - i-Vector extractor files

**Check it:**
```bash
ls -la model/
# Should show: am/ conf/ graph/ ivector/
```

## Alternative Models

- **Larger models**: If you need higher accuracy and have more resources, consider `vosk-model-en-us-0.22` (~1.8GB)
- **Other languages**: Browse the models page for support in other languages
- **Server models**: For server deployments with more CPU/RAM available

## Troubleshooting

If Jackdaw fails to start with a model error:
1. Verify all model files are in this directory
2. Check that the model files are not corrupted
3. Ensure you downloaded a compatible Vosk model (not Kaldi or other formats)
4. Try re-downloading the model if issues persist

## More Information

- Vosk Documentation: https://alphacephei.com/vosk/
- Model Downloads: https://alphacephei.com/vosk/models
- Vosk GitHub: https://github.com/alphacep/vosk-api
