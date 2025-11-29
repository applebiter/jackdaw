#!/usr/bin/env python3
"""
JackTrip Response Watcher

Monitors jacktrip_response.txt and speaks responses via TTS
"""

import time
import os
from pathlib import Path
import subprocess

RESPONSE_FILE = Path("jacktrip_response.txt")
TTS_FILE = Path("llm_response.txt")
CHECK_INTERVAL = 0.5  # seconds

def speak_response(text: str):
    """Write text to TTS response file"""
    try:
        with open(TTS_FILE, 'w') as f:
            f.write(text)
        print(f"[TTS] Speaking: {text}")
    except Exception as e:
        print(f"Error writing TTS file: {e}")

def watch_for_responses():
    """Watch for JackTrip responses and speak them"""
    print("JackTrip TTS watcher started...")
    last_mtime = 0
    
    while True:
        try:
            if RESPONSE_FILE.exists():
                current_mtime = RESPONSE_FILE.stat().st_mtime
                
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    
                    # Read and speak the response
                    with open(RESPONSE_FILE, 'r') as f:
                        text = f.read().strip()
                    
                    if text:
                        speak_response(text)
                        # Clear the file
                        RESPONSE_FILE.unlink()
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nStopping JackTrip TTS watcher...")
            break
        except Exception as e:
            print(f"Error in watcher: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    watch_for_responses()
