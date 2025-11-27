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
    # Always save to workspace root, not tools/ directory
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    cfg_path = workspace_root / "jack_routing.json"
    
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
    
    # Save ALL JACK connections in the graph by iterating through all output ports
    # This captures the complete routing state, not just Jackdaw-specific connections
    all_connections = []
    seen_connections = set()  # Avoid duplicates
    
    # Get all output ports in the system
    output_ports = [p for p in all_ports if p.is_output]
    
    for port in output_ports:
        connections = client.get_all_connections(port)
        if connections:
            for dest_port in connections:
                connection_pair = (port.name, dest_port.name)
                if connection_pair not in seen_connections:
                    seen_connections.add(connection_pair)
                    all_connections.append([port.name, dest_port.name])
                    
                    # Mark Jackdaw connections specially
                    is_jackdaw = (port.name.split(':')[0] in jackdaw_clients or 
                                 dest_port.name.split(':')[0] in jackdaw_clients)
                    marker = "✅" if is_jackdaw else "  "
                    print(f"{marker} {port.name} -> {dest_port.name}")
    
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
