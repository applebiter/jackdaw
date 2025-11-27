#!/usr/bin/env python3
"""Capture and remember JACK routing for voice assistant components.

Usage:
  python remember_jack_routing.py

After manually connecting your preferred sources to:
- `VoiceCommandClient:input` (for voice recognition)
- `RingBufferRecorder:in_1` and `RingBufferRecorder:in_2` (for retroactive recording)
- `IcecastStreamer:input_1` and `IcecastStreamer:input_2` (for streaming to Icecast)

Run this script to save the connections. They will be auto-restored on startup.
"""

import jack
import json
from pathlib import Path


def main() -> None:
    client = jack.Client("RoutingInspector")
    cfg_path = Path("jack_routing.json")
    
    # Load existing config if present
    data = {}
    if cfg_path.exists():
        try:
            with cfg_path.open("r") as f:
                data = json.load(f)
        except:
            pass
    
    # Check VoiceCommandClient:input
    voice_port_name = "VoiceCommandClient:input"
    voice_ports = [p for p in client.get_ports() if p.name == voice_port_name]
    if voice_ports:
        connections = client.get_all_connections(voice_ports[0])
        if connections:
            source_port = connections[0].name
            data["voice_input_source"] = source_port
            print(f"✅ Voice input: {source_port} -> {voice_port_name}")
        else:
            print(f"⚠️  No connections to {voice_port_name}")
    else:
        print(f"⚠️  {voice_port_name} not found (voice assistant not running?)")
    
    # Check ring buffer recorder inputs (new Python-based recorder)
    buffer_connections = []
    recorder_found = False
    for channel in [1, 2]:
        buf_port_name = f"RingBufferRecorder:in_{channel}"
        buf_ports = [p for p in client.get_ports() if p.name == buf_port_name]
        if buf_ports:
            recorder_found = True
            connections = client.get_all_connections(buf_ports[0])
            if connections:
                for conn in connections:
                    buffer_connections.append([conn.name, buf_port_name])
                    print(f"✅ Ring Buffer: {conn.name} -> {buf_port_name}")
    
    # Also check for legacy TimeMachine inputs (for backwards compatibility)
    if not recorder_found:
        for channel in [1, 2]:
            tm_port_name = f"TimeMachine:in_{channel}"
            tm_ports = [p for p in client.get_ports() if p.name == tm_port_name]
            if tm_ports:
                connections = client.get_all_connections(tm_ports[0])
                if connections:
                    for conn in connections:
                        buffer_connections.append([conn.name, tm_port_name])
                        print(f"✅ Timemachine: {conn.name} -> {tm_port_name}")
    
    if not buffer_connections and not recorder_found:
        print(f"⚠️  RingBufferRecorder not found (buffer not started?)")
    
    if buffer_connections:
        data["timemachine_inputs"] = buffer_connections
    
    # Check IcecastStreamer inputs (for streaming)
    icecast_connections = []
    icecast_found = False
    for channel in [1, 2]:
        ice_port_name = f"IcecastStreamer:input_{channel}"
        ice_ports = [p for p in client.get_ports() if p.name == ice_port_name]
        if ice_ports:
            icecast_found = True
            connections = client.get_all_connections(ice_ports[0])
            if connections:
                for conn in connections:
                    icecast_connections.append([conn.name, ice_port_name])
                    print(f"✅ IcecastStreamer: {conn.name} -> {ice_port_name}")
    
    if not icecast_connections and icecast_found:
        print(f"⚠️  IcecastStreamer has no connections")
    elif not icecast_found:
        print(f"⚠️  IcecastStreamer not found (streaming not started?)")
    
    if icecast_connections:
        data["icecast_inputs"] = icecast_connections
    
    # Save config
    if data:
        with cfg_path.open("w") as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Saved JACK routing to {cfg_path}")
    else:
        print("\n❌ No connections found to save.")
        print("\nTo use this tool:")
        print("1. Start the voice assistant")
        print("2. Say 'indigo start the buffer' and/or 'indigo start streaming'")
        print("3. Manually connect audio sources in qjackctl/Carla")
        print("4. Run this script again to remember the connections")


if __name__ == "__main__":
    main()
