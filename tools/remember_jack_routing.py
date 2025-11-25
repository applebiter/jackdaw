#!/usr/bin/env python3
"""Capture and remember the current JACK source connected to VoiceCommandClient:input.

Usage:
  python remember_jack_routing.py

After you manually connect your preferred capture client to
`VoiceCommandClient:input` once, run this script. It will inspect
current JACK connections and write `jack_routing.json` with the
source port name so the voice client can auto-connect it on startup.
"""

import jack
import json
from pathlib import Path


def main() -> None:
    client = jack.Client("RoutingInspector")

    input_port_name = "VoiceCommandClient:input"
    input_ports = [p for p in client.get_ports() if p.name == input_port_name]
    if not input_ports:
        print(f"Input port not found: {input_port_name}")
        return

    input_port = input_ports[0]

    # Use the client API to get connections for this port
    connections = client.get_all_connections(input_port)
    if not connections:
        print(f"No sources currently connected to {input_port_name}.")
        print("Connect your desired capture client to this port, then rerun.")
        return

    # For now, just take the first connected source
    source_port = connections[0].name
    cfg_path = Path("jack_routing.json")
    data = {"voice_input_source": source_port}
    with cfg_path.open("w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved JACK routing: {source_port} -> {input_port_name} in {cfg_path}")


if __name__ == "__main__":
    main()
