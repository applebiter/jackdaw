# JACK Patchbay Interface

The JackTrip hub includes a web-based JACK patchbay interface for visualizing and manipulating audio routing between clients, similar to Carla or QjackCtl.

## Features

- **Real-time visualization** of JACK audio graph with Bezier connection lines
- **Drag-and-drop routing** - click output connector, drag to input connector
- **Draggable client boxes** - click and drag headers to reposition
- **Zoom controls** - zoom in/out with buttons or mouse wheel
- **Pan canvas** - click and drag background to navigate
- **Minimap** - birds-eye view with draggable viewport indicator
- **Client splitting** - clients with both inputs and outputs shown as separate boxes
- **WebSocket updates** - live graph changes without refresh
- **No duplicate lines** - clean, single connection lines between ports

## Accessing the Patchbay

### Direct URL (HTTPS)
```
https://localhost:8000/patchbay/{room_id}
```

Replace `{room_id}` with your room's ID. Note the HTTPS protocol - the hub now uses SSL/TLS by default.

**Browser Warning**: For development with self-signed certificates, your browser will show a security warning. Click "Advanced" → "Proceed anyway" to access the patchbay.

## Interface Elements

### Header & Controls
- **Room ID**: Shows which room you're controlling
- **Refresh button**: Manually refresh the graph
- **Clear All button**: Disconnect all ports
- **Auto Route button**: Automatically connect common routing patterns
- **Zoom Controls**: +/- buttons and percentage display
- **Zoom Reset**: Click percentage to reset to 100%

### Canvas (10000x10000px)
- **Client boxes**: Each JACK client appears as a draggable box
  - Clients with both inputs and outputs are split into "(In)" and "(Out)" boxes
  - Dark theme with blue headers
- **Output ports**: Right side of client boxes, green dot connectors
- **Input ports**: Left side of client boxes, green dot connectors
- **Connection lines**: Green Bezier curves showing active connections
- **Pan**: Click and drag empty canvas space to move around
- **Zoom**: Mouse wheel to zoom in/out around cursor

### Minimap (Bottom-left)
- **200x200px overview** of entire 10000x10000 canvas
- **Green rectangles**: Represent client boxes
- **Red viewport box**: Shows current view area
- **Draggable viewport**: Click and drag the red box to navigate quickly

### Status Bar
- Shows connection count and number of clients
- Displays real-time updates from WebSocket

## Creating Connections

1. **Click** on an output port connector (green dot on right side of box)
2. **Drag** to an input port connector (green dot on left side of box)  
3. **Release** to create the connection

The connection appears as a green Bezier curve between the ports.

**Port Direction Notes**:
- System `capture` ports are **outputs** (send audio from hardware)
- System `playback` ports are **inputs** (receive audio to hardware)
- This follows JACK semantics, not intuitive naming

## Disconnecting

Use the "Clear All" button to remove all connections. Individual connection removal is not yet implemented.

## Auto-Routing

The "Auto Route" button sets up standard routing:
- `system:capture` → `jd_*:send_*` (microphone to JackTrip send)
- `jd_*:receive_*` → `system:playback` (JackTrip receive to speakers)

This is useful for quickly setting up a standard jam session configuration.

## API Endpoints

The patchbay uses these REST and WebSocket endpoints:

### REST API

#### Get JACK Graph
```http
GET /jack/graph
Authorization: Bearer {token}
```

Returns:
```json
{
  "clients": {
    "system": [
      {
        "name": "system:capture_1",
        "type": "audio",
        "direction": "output",
        "connections": ["jd_client:send_1"]
      }
    ]
  },
  "connections": [
    ["system:capture_1", "jd_client:send_1"]
  ]
}
```

#### Connect Ports
```http
POST /jack/connect?source={port1}&dest={port2}
Authorization: Bearer {token}
```

#### Disconnect Ports
```http
POST /jack/disconnect?source={port1}&dest={port2}
Authorization: Bearer {token}
```

### WebSocket

Connect to:
```
wss://localhost:8000/ws/patchbay
```

Note: Use `wss://` (WebSocket Secure) not `ws://` since the hub uses HTTPS.

Send messages:
```json
{
  "type": "connect",
  "source": "system:capture_1",
  "dest": "jd_client:send_1"
}
```

```json
{
  "type": "disconnect",
  "source": "system:capture_1",
  "dest": "jd_client:send_1"
}
```

```json
{
  "type": "refresh"
}
```

Receive updates:
```json
{
  "type": "graph",
  "data": {
    "clients": {...},
    "connections": [...]
  }
}
```

## Technical Details

### Port Naming Convention

JackTrip clients follow this pattern:
- `jd_{client_name}:send_{N}` - Audio being sent to hub
- `jd_{client_name}:receive_{N}` - Audio received from hub

System ports:
- `system:capture_{N}` - Microphone inputs
- `system:playback_{N}` - Speaker outputs

### Channel Configuration

The number of send/receive ports depends on the channel configuration in `voice_assistant_config.json`:

```json
{
  "jacktrip_client": {
    "send_channels": 2,
    "receive_channels": 2
  }
}
```

- `send_channels`: Number of outgoing audio channels (your audio to others)
- `receive_channels`: Number of incoming audio channels (others' audio to you)

### Auto-Connect

When `auto_connect: true` in config, the plugin automatically sets up routing when joining a room. The patchbay allows you to modify this routing or set up custom routing when auto-connect is disabled.

## Troubleshooting

### Patchbay shows no clients
- Ensure JACK is running: `jack_lsp`
- Verify JackTrip client is connected: `jack_lsp | grep jd_`

### Can't create connections
- Check if ports are compatible (outputs connect to inputs only)
- Ensure WebSocket is connected (check status bar)

### WebSocket keeps disconnecting
- Hub server might not be running
- Check hub logs: `tools/jacktrip_hub/run_local_hub.sh`

### Drag-and-drop not working
- Try using the REST API directly for debugging
- Check browser console for JavaScript errors

## Keyboard & Mouse Controls

- **Mouse Wheel**: Zoom in/out (zooms around cursor position)
- **Click + Drag Background**: Pan canvas
- **Click + Drag Header**: Move individual client box
- **Click + Drag Minimap Box**: Navigate to different canvas area
- **+/- Buttons**: Zoom controls
- **Click Zoom %**: Reset zoom to 100%

## Completed Features

- ✅ Large scrollable canvas (10000x10000)
- ✅ Zoom with mouse wheel and buttons
- ✅ Pan by dragging canvas
- ✅ Draggable client boxes
- ✅ Minimap with viewport indicator
- ✅ Client splitting (separate In/Out boxes)
- ✅ Correct port direction detection
- ✅ Single connection lines (no duplicates)
- ✅ Synchronized zoom/pan transforms
- ✅ Transform-origin fixes for proper scaling

## Future Enhancements

- Click connection lines to disconnect
- Right-click context menus
- Connection presets/templates
- Visual feedback for audio levels
- Room creator restrictions (only creator can modify routing)
- Color coding for different audio types
- Port search/filter
- Save/load patchbay layouts
- Undo/redo for connections
