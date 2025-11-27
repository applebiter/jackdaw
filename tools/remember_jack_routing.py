#!/usr/bin/env python3
"""Capture and remember JACK routing for all Jackdaw components.

Usage:
  python remember_jack_routing.py

Automatically discovers all Jackdaw JACK clients (prefixed with "jd_"):
- jd_voice (voice recognition)
- jd_tts (text-to-speech output)
- jd_music (music playback)
- jd_buffer (timemachine recording)
- jd_stream (Icecast streaming)

After manually connecting your preferred audio sources to any Jackdaw clients in qjackctl/Carla,
run this script to save ALL the connections. They will be auto-restored on next startup.
"""

import jack
import json
from pathlib import Path


def main() -> None:
    client = jack.Client("jd_route_inspector")
    cfg_path = Path("jack_routing.json")
    
    # Load existing config if present
    data = {}
    if cfg_path.exists():
        try:
            with cfg_path.open("r") as f:
                data = json.load(f)
        except:
            pass
    
    # Find all Jackdaw clients (those starting with "jd_")
    all_ports = client.get_ports()
    jackdaw_clients = set()
    
    for port in all_ports:
        port_name = port.name
        if port_name.startswith("jd_"):
            client_name = port_name.split(":")[0]
            jackdaw_clients.add(client_name)
    
    # Also check for legacy client names for backwards compatibility
    legacy_names = ["VoiceCommandClient", "RingBufferRecorder", "TimeMachine", "IcecastStreamer", "OggPlayer", "TTSClient"]
    for port in all_ports:
        port_name = port.name
        for legacy in legacy_names:
            if port_name.startswith(f"{legacy}:"):
                jackdaw_clients.add(legacy)
                break
    
    if not jackdaw_clients:
        print("⚠️  No Jackdaw JACK clients found. Is the voice assistant running?")
        print("\nMake sure you've started the components you want to save:")
        print("  - Voice assistant (automatic)")
        print("  - Say 'indigo start the buffer' for timemachine")
        print("  - Say 'indigo start streaming' for Icecast")
        return
    
    print(f"Found {len(jackdaw_clients)} Jackdaw JACK client(s): {', '.join(sorted(jackdaw_clients))}\n")
    
    # Save all input port connections for each Jackdaw client
    all_connections = []
    
    for jd_client in sorted(jackdaw_clients):
        client_ports = [p for p in all_ports if p.name.startswith(f"{jd_client}:") and p.is_input]
        
        for port in client_ports:
            connections = client.get_all_connections(port)
            if connections:
                for source_port in connections:
                    connection_pair = [source_port.name, port.name]
                    all_connections.append(connection_pair)
                    print(f"✅ {source_port.name} -> {port.name}")
            else:
                print(f"⚠️  No connections to {port.name}")
    
    if all_connections:
        data["jackdaw_connections"] = all_connections
    
    # Save config
    if all_connections:
        with cfg_path.open("w") as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Saved {len(all_connections)} JACK connection(s) to {cfg_path}")
    else:
        print("\n❌ No connections found to save.")
        print("\nTo use this tool:")
        print("1. Start the voice assistant")
        print("2. Say 'indigo start the buffer' and/or 'indigo start streaming'")
        print("3. Manually connect audio sources in qjackctl/Carla")
        print("4. Run this script again to remember the connections")


if __name__ == "__main__":
    main()
