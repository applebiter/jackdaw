#!/usr/bin/env python3
"""
JackTrip Hub Server - Single Band Edition

Central hub for band collaboration via JackTrip. Runs a single persistent room
where all authenticated band members can connect. The hub owner (first user) 
controls patchbay routing and can grant patchbay access to other members.
"""

import asyncio
import bcrypt
import json
import os
import signal
import sqlite3
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------- Configuration ----------
HUB_HOST = os.getenv("HUB_HOST", "localhost")
HUB_PORT = int(os.getenv("HUB_PORT", 8000))
JACKTRIP_BIN = os.getenv("JACKTRIP_BIN", "jacktrip")
JACKTRIP_BASE_PORT = int(os.getenv("JACKTRIP_BASE_PORT", 4464))
JACKTRIP_PORT_RANGE = int(os.getenv("JACKTRIP_PORT_RANGE", 100))

# Single room mode configuration
SINGLE_ROOM_MODE = os.getenv("SINGLE_ROOM_MODE", "true").lower() in ("true", "1", "yes")
BAND_NAME = os.getenv("BAND_NAME", "The Band")

# SSL/TLS Configuration
SSL_CERTFILE = os.getenv("SSL_CERTFILE", None)  # Path to SSL certificate
SSL_KEYFILE = os.getenv("SSL_KEYFILE", None)    # Path to SSL private key
USE_SSL = SSL_CERTFILE and SSL_KEYFILE

# Database and in-memory stores
DB_PATH = Path(__file__).parent / "hub.db"
CERTS_PATH = Path(__file__).parent / "certs"

# Single persistent room for the band
DEFAULT_ROOM_ID = None  # ID of the default room in single room mode
ACTIVE_PARTICIPANTS = set()  # Set of currently connected user_ids

# Multi-room support (legacy - used in both single and multi-room mode)
ROOMS = {}  # room_id -> Room object
JACKTRIP_PROCS = {}  # room_id -> {"port": int, "process": Popen, "created_at": str}

# ---------- Models ----------
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user_id: str
    username: str
    is_owner: bool
    has_patchbay_access: bool

class JoinResponse(BaseModel):
    hub_host: str
    jacktrip_port: int
    jacktrip_flags: List[str] = []
    participant_count: int

class UserInfo(BaseModel):
    id: str
    username: str
    is_owner: bool
    has_patchbay_access: bool
    is_connected: bool  # Currently in the room

class SetPermissionRequest(BaseModel):
    user_id: str
    has_patchbay_access: bool

class HealthResponse(BaseModel):
    status: str
    participant_count: int
    jacktrip_running: bool

class RoomListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    participant_count: int
    max_participants: int
    created_at: str

class RoomCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    max_participants: int = 4

class Room(BaseModel):
    id: str
    name: str
    description: Optional[str]
    creator_id: str
    jacktrip_port: int
    max_participants: int
    participants: List[str]
    created_at: str

class RoomJoinResponse(BaseModel):
    room_id: str
    room_name: str
    hub_host: str
    jacktrip_port: int
    jacktrip_flags: List[str]

class RoomJoinRequest(BaseModel):
    sample_rate: Optional[int] = None  # Client's sample rate
    buffer_size: Optional[int] = None  # Client's buffer size

class HubSettings(BaseModel):
    sample_rate: int
    buffer_size: int

class UpdateSettingsRequest(BaseModel):
    sample_rate: int
    buffer_size: int

# ---------- Database Setup ----------
def init_database():
    """Initialize SQLite database for users"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            is_owner BOOLEAN DEFAULT 0,
            has_patchbay_access BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    
    # Sessions/tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Hub settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hub_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        )
    """)
    
    # Initialize default settings if not present
    cursor.execute("SELECT COUNT(*) FROM hub_settings WHERE key = 'sample_rate'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO hub_settings (key, value, updated_at, updated_by)
            VALUES ('sample_rate', '48000', ?, 'system')
        """, (datetime.utcnow().isoformat(),))
    
    cursor.execute("SELECT COUNT(*) FROM hub_settings WHERE key = 'buffer_size'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO hub_settings (key, value, updated_at, updated_by)
            VALUES ('buffer_size', '256', ?, 'system')
        """, (datetime.utcnow().isoformat(),))
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

# ---------- Auth helpers ----------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_user(username: str, password: str, email: Optional[str] = None) -> str:
    """Create a new user and return user_id. First user becomes owner with patchbay access."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    created_at = datetime.utcnow().isoformat()
    
    # Check if this is the first user (becomes owner)
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    is_owner = (user_count == 0)
    has_patchbay_access = is_owner  # Owner always has patchbay access
    
    try:
        cursor.execute(
            "INSERT INTO users (id, username, password_hash, email, is_owner, has_patchbay_access, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, password_hash, email, is_owner, has_patchbay_access, created_at)
        )
        conn.commit()
        if is_owner:
            print(f"Created owner account: {username}")
        return user_id
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[str]:
    """Authenticate user and return user_id if valid"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row and verify_password(password, row[1]):
        return row[0]
    return None

def create_session(user_id: str) -> str:
    """Create a new session token for user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    token = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    cursor.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, created_at)
    )
    conn.commit()
    conn.close()
    
    return token

def get_user_from_token(token: str) -> Optional[str]:
    """Get user_id from session token"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None

def get_user_info(user_id: str) -> Optional[Dict]:
    """Get user information including permissions"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT username, is_owner, has_patchbay_access FROM users WHERE id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": user_id,
            "username": row[0],
            "is_owner": bool(row[1]),
            "has_patchbay_access": bool(row[2])
        }
    return None

def set_user_patchbay_access(user_id: str, has_access: bool):
    """Grant or revoke patchbay access for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET has_patchbay_access = ? WHERE id = ?",
        (has_access, user_id)
    )
    conn.commit()
    conn.close()

def get_hub_setting(key: str) -> Optional[str]:
    """Get a hub setting value"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM hub_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_hub_setting(key: str, value: str, user_id: str):
    """Set a hub setting value"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO hub_settings (key, value, updated_at, updated_by)
        VALUES (?, ?, ?, ?)
    """, (key, value, datetime.utcnow().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ", 1)[1]
    user_id = get_user_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

# ---------- JackTrip management ----------
def allocate_port() -> int:
    """Find an available port for JackTrip"""
    used_ports = {info["port"] for info in JACKTRIP_PROCS.values()}
    for offset in range(JACKTRIP_PORT_RANGE):
        candidate = JACKTRIP_BASE_PORT + offset
        if candidate not in used_ports:
            return candidate
    raise RuntimeError("No free JackTrip ports available")

def start_jacktrip_server(room_id: str) -> int:
    """Start a JackTrip server process for a room"""
    port = allocate_port()
    # JackTrip server mode: -S (server), -B (bind port), -q (queue/buffer), -p 5 (no auto patching)
    cmd = [JACKTRIP_BIN, "-S", "-B", str(port), "-q", "4", "-p", "5"]
    
    try:
        proc = Popen(cmd)
        JACKTRIP_PROCS[room_id] = {
            "port": port,
            "process": proc,
            "created_at": datetime.utcnow().isoformat()
        }
        print(f"Started JackTrip server for room {room_id} on port {port}")
        return port
    except Exception as e:
        print(f"Failed to start JackTrip: {e}")
        raise RuntimeError(f"Failed to start JackTrip server: {e}")

def stop_jacktrip_server(room_id: str):
    """Stop a JackTrip server process"""
    info = JACKTRIP_PROCS.get(room_id)
    if not info:
        return
    
    proc: Popen = info["process"]
    if proc.poll() is None:  # Process still running
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception as e:
            print(f"Error stopping JackTrip process: {e}")
            try:
                proc.kill()
            except:
                pass
    
    JACKTRIP_PROCS.pop(room_id, None)
    print(f"Stopped JackTrip server for room {room_id}")

def cleanup_dead_processes():
    """Clean up any dead JackTrip processes"""
    dead_rooms = []
    for room_id, info in JACKTRIP_PROCS.items():
        proc = info["process"]
        if proc.poll() is not None:  # Process has died
            dead_rooms.append(room_id)
    
    for room_id in dead_rooms:
        print(f"JackTrip process for room {room_id} died unexpectedly")
        JACKTRIP_PROCS.pop(room_id, None)
        # Also clean up the room
        if room_id in ROOMS:
            ROOMS.pop(room_id)

# ---------- FastAPI app ----------
app = FastAPI(
    title="JackTrip Hub Server",
    description="Anonymous JackTrip collaboration hub",
    version="0.1.0"
)

# Mount static files for patchbay UI
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize hub on startup"""
    global DEFAULT_ROOM_ID
    init_database()
    print(f"JackTrip Hub Server started")
    print(f"Hub host: {HUB_HOST}")
    print(f"JackTrip port range: {JACKTRIP_BASE_PORT}-{JACKTRIP_BASE_PORT + JACKTRIP_PORT_RANGE - 1}")
    
    if SINGLE_ROOM_MODE:
        print(f"\n🎵 Single Room Mode: {BAND_NAME}")
        # Create default room
        room_id = str(uuid.uuid4())
        port = allocate_port()
        DEFAULT_ROOM_ID = room_id
        
        # Start JackTrip server
        cmd = [JACKTRIP_BIN, "-S", "-B", str(port), "-q", "4", "-p", "5"]
        try:
            proc = Popen(cmd)
            JACKTRIP_PROCS[room_id] = {
                "port": port,
                "process": proc,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Create room object
            ROOMS[room_id] = Room(
                id=room_id,
                name=BAND_NAME,
                description="Default band collaboration room",
                creator_id="system",
                jacktrip_port=port,
                max_participants=16,
                participants=[],
                created_at=datetime.utcnow().isoformat()
            )
            
            # Wait for JackTrip to finish initial output, then print status
            import time
            time.sleep(2)
            
            print("\n" + "="*60)
            print(f"🎵 JACKDAW HUB READY")
            print("="*60)
            print(f"   Band: {BAND_NAME}")
            print(f"   Web Interface: https://{HUB_HOST}:8000")
            print(f"   JackTrip Port: {port}")
            print(f"   Mode: Single Room (No Auto-Patching)")
            print("="*60 + "\n")
        except Exception as e:
            print(f"✗ Failed to start default room: {e}")
    else:
        print("\n📂 Multi-Room Mode enabled")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("Shutting down hub, stopping all JackTrip servers...")
    for room_id in list(JACKTRIP_PROCS.keys()):
        stop_jacktrip_server(room_id)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve login page"""
    try:
        with open(Path(__file__).parent / "static" / "index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Login page not found</h1>"

@app.get("/patchbay", response_class=HTMLResponse)
async def patchbay():
    """Serve patchbay interface (client will check authentication via token)"""
    try:
        with open(Path(__file__).parent / "static" / "patchbay.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Patchbay interface not found</h1>"

@app.get("/rooms-ui", response_class=HTMLResponse)
async def rooms_page():
    """Serve room manager interface (legacy - redirects to patchbay in single room mode)"""
    if SINGLE_ROOM_MODE:
        return "<script>window.location.href = '/patchbay';</script>"
    try:
        with open(Path(__file__).parent / "static" / "rooms.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Room manager interface not found</h1>"

@app.get("/access-denied", response_class=HTMLResponse)
async def access_denied_page():
    """Serve access denied page for users without patchbay access"""
    try:
        with open(Path(__file__).parent / "static" / "access_denied.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Access denied - Patchbay access required</h1>"

@app.get("/settings", response_model=HubSettings)
async def get_settings(user_id: str = Depends(get_current_user_id)):
    """Get hub audio settings"""
    sample_rate = int(get_hub_setting("sample_rate") or "48000")
    buffer_size = int(get_hub_setting("buffer_size") or "256")
    return HubSettings(sample_rate=sample_rate, buffer_size=buffer_size)

@app.post("/settings")
async def update_settings(req: UpdateSettingsRequest, user_id: str = Depends(get_current_user_id)):
    """Update hub audio settings (owner only)"""
    user_info = get_user_info(user_id)
    if not user_info or not user_info["is_owner"]:
        raise HTTPException(status_code=403, detail="Only owner can update settings")
    
    set_hub_setting("sample_rate", str(req.sample_rate), user_id)
    set_hub_setting("buffer_size", str(req.buffer_size), user_id)
    
    return {"status": "ok", "sample_rate": req.sample_rate, "buffer_size": req.buffer_size}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health and status"""
    cleanup_dead_processes()
    total_participants = sum(len(room.participants) for room in ROOMS.values())
    return HealthResponse(
        status="ok",
        active_rooms=len(ROOMS),
        total_participants=total_participants
    )

@app.post("/auth/register", response_model=LoginResponse)
async def register(req: RegisterRequest):
    """Register a new user"""
    user_id = create_user(req.username, req.password, req.email)
    token = create_session(user_id)
    user_info = get_user_info(user_id)
    
    return LoginResponse(
        token=token,
        user_id=user_id,
        username=user_info["username"],
        is_owner=user_info["is_owner"],
        has_patchbay_access=user_info["has_patchbay_access"]
    )

@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate user and return token"""
    user_id = authenticate_user(req.username, req.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_session(user_id)
    user_info = get_user_info(user_id)
    return LoginResponse(
        token=token,
        user_id=user_id,
        username=user_info["username"],
        is_owner=user_info["is_owner"],
        has_patchbay_access=user_info["has_patchbay_access"]
    )

@app.get("/users", response_model=List[UserInfo])
async def list_users(user_id: str = Depends(get_current_user_id)):
    """List all users (owner only)"""
    user_info = get_user_info(user_id)
    if not user_info or not user_info["is_owner"]:
        raise HTTPException(status_code=403, detail="Only owner can list users")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, is_owner, has_patchbay_access FROM users ORDER BY created_at"
    )
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append(UserInfo(
            id=row[0],
            username=row[1],
            is_owner=bool(row[2]),
            has_patchbay_access=bool(row[3]),
            is_connected=(row[0] in ACTIVE_PARTICIPANTS)
        ))
    return users

@app.get("/rooms", response_model=List[RoomListItem])
async def list_rooms(user_id: str = Depends(get_current_user_id)):
    """List all active rooms"""
    cleanup_dead_processes()
    return [
        RoomListItem(
            id=room.id,
            name=room.name,
            description=room.description,
            participant_count=len(room.participants),
            max_participants=room.max_participants,
            created_at=room.created_at
        )
        for room in ROOMS.values()
    ]

@app.post("/users/{target_user_id}/permissions")
async def set_permissions(target_user_id: str, req: SetPermissionRequest, user_id: str = Depends(get_current_user_id)):
    """Grant or revoke patchbay access (owner only)"""
    user_info = get_user_info(user_id)
    if not user_info or not user_info["is_owner"]:
        raise HTTPException(status_code=403, detail="Only owner can manage permissions")
    
    # Can't change owner's permissions
    target_info = get_user_info(target_user_id)
    if not target_info:
        raise HTTPException(status_code=404, detail="User not found")
    if target_info["is_owner"]:
        raise HTTPException(status_code=400, detail="Cannot modify owner permissions")
    
    set_user_patchbay_access(target_user_id, req.has_patchbay_access)
    return {"success": True, "user_id": target_user_id, "has_patchbay_access": req.has_patchbay_access}

@app.get("/user/rooms", response_model=List[RoomListItem])
async def list_user_rooms(user_id: str = Depends(get_current_user_id)):
    """Get rooms the current user is participating in"""
    user_rooms = [
        RoomListItem(
            id=room.id,
            name=room.name,
            description=room.description,
            participant_count=len(room.participants),
            max_participants=room.max_participants,
            created_at=room.created_at
        )
        for room in ROOMS.values()
        if user_id in room.participants
    ]
    return user_rooms

@app.post("/rooms", response_model=Room)
async def create_room(
    req: RoomCreateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new room and start JackTrip server"""
    room_id = str(uuid.uuid4())
    
    # Start JackTrip server for this room
    try:
        port = start_jacktrip_server(room_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Create room object (no passphrase - all authenticated users can join)
    room = Room(
        id=room_id,
        name=req.name,
        description=req.description,
        max_participants=req.max_participants,
        participants=[user_id],
        created_at=datetime.utcnow().isoformat(),
        creator_id=user_id
    )
    ROOMS[room_id] = room
    
    print(f"Created room '{req.name}' (id={room_id[:8]}) by user {user_id[:8]} with JackTrip on port {port}")
    return room

@app.get("/rooms/{room_id}", response_model=Room)
async def get_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    """Get room details"""
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@app.post("/rooms/{room_id}/join", response_model=RoomJoinResponse)
async def join_room(
    room_id: str, 
    req: RoomJoinRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Join a room and get JackTrip connection details"""
    # In single room mode, use default room
    if SINGLE_ROOM_MODE:
        room_id = DEFAULT_ROOM_ID
    
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Any authenticated band member can join any room
    if user_id in room.participants:
        # Already in room, just return connection info
        pass
    else:
        if len(room.participants) >= room.max_participants:
            raise HTTPException(status_code=403, detail="Room is full")
        room.participants.append(user_id)
    
    # Get JackTrip connection info
    info = JACKTRIP_PROCS.get(room_id)
    if not info:
        raise HTTPException(
            status_code=500,
            detail="JackTrip server not found for room"
        )
    
    port = info["port"]
    # Client should use: jacktrip -C {hub_host} -p {port} -q 4
    flags = ["-q", "4"]
    
    print(f"User {user_id[:8]} joined room '{room.name}'")
    return RoomJoinResponse(
        room_id=room.id,
        room_name=room.name,
        hub_host=HUB_HOST,
        jacktrip_port=port,
        jacktrip_flags=flags,
    )

@app.post("/join", response_model=RoomJoinResponse)
async def join_default_room(req: RoomJoinRequest, user_id: str = Depends(get_current_user_id)):
    """Join the default room (single room mode only)
    
    If owner joins with sample_rate/buffer_size, hub settings are updated to match.
    """
    if not SINGLE_ROOM_MODE:
        raise HTTPException(status_code=404, detail="Endpoint only available in single room mode")
    
    if not DEFAULT_ROOM_ID:
        raise HTTPException(status_code=500, detail="Default room not initialized")
    
    # If owner is joining with settings, update hub to match and restart JACK/JackTrip
    user_info = get_user_info(user_id)
    if user_info and user_info["is_owner"]:
        settings_changed = False
        
        if req.sample_rate:
            current_rate = get_hub_setting("sample_rate")
            if current_rate != str(req.sample_rate):
                set_hub_setting("sample_rate", str(req.sample_rate), user_id)
                print(f"[Owner] Updated hub sample rate to {req.sample_rate}")
                settings_changed = True
        
        if req.buffer_size:
            current_buffer = get_hub_setting("buffer_size")
            if current_buffer != str(req.buffer_size):
                set_hub_setting("buffer_size", str(req.buffer_size), user_id)
                print(f"[Owner] Updated hub buffer size to {req.buffer_size}")
                settings_changed = True
        
        # If settings changed, restart JACK and JackTrip to apply them
        if settings_changed and DEFAULT_ROOM_ID:
            print(f"[Owner] Restarting JACK with new settings...")
            
            # Stop current JackTrip server
            stop_jacktrip_server(DEFAULT_ROOM_ID)
            
            # Restart JACK with new settings
            try:
                import subprocess as sp
                sp.run(["jack_control", "stop"], capture_output=True, timeout=5)
                import time
                time.sleep(1)
                
                if req.sample_rate:
                    sp.run(["jack_control", "dps", "rate", str(req.sample_rate)], 
                           capture_output=True, timeout=5)
                if req.buffer_size:
                    sp.run(["jack_control", "dps", "period", str(req.buffer_size)],
                           capture_output=True, timeout=5)
                
                sp.run(["jack_control", "start"], capture_output=True, timeout=10)
                time.sleep(2)
                
                # Restart JackTrip server
                port = start_jacktrip_server(DEFAULT_ROOM_ID)
                print(f"[Owner] JACK and JackTrip restarted successfully on port {port}")
            except Exception as e:
                print(f"[Owner] Warning: Could not restart JACK automatically: {e}")
                print(f"[Owner] Please restart the hub server to apply new settings")
    
    return await join_room(DEFAULT_ROOM_ID, req, user_id)

@app.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    """Leave a room"""
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if user_id in room.participants:
        room.participants.remove(user_id)
        print(f"User {user_id[:8]} left room '{room.name}'")
    
    # If room is empty, stop JackTrip and clean up
    if not room.participants:
        print(f"Room '{room.name}' is empty, stopping JackTrip")
        stop_jacktrip_server(room_id)
        ROOMS.pop(room_id, None)
    
    return {"status": "ok", "room_id": room_id}

@app.delete("/rooms/{room_id}")
async def delete_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a room (creator only)"""
    if SINGLE_ROOM_MODE:
        raise HTTPException(status_code=403, detail="Cannot delete default room in single room mode")
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.creator_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the room creator can delete it"
        )
    
    # Stop JackTrip and remove room
    stop_jacktrip_server(room_id)
    ROOMS.pop(room_id, None)
    
    print(f"Room '{room.name}' deleted by creator")
    return {"status": "ok", "room_id": room_id}

# ---------- JACK Patchbay API ----------

class JACKPort(BaseModel):
    name: str
    type: str  # "audio", "midi"
    direction: str  # "input", "output"
    connections: List[str]

class JACKGraph(BaseModel):
    clients: Dict[str, List[JACKPort]]
    connections: List[tuple]  # [(source, dest), ...]

def get_jack_graph() -> JACKGraph:
    """Get current JACK audio graph (audio ports only, no MIDI)"""
    try:
        # Get all ports with properties and connections
        result = subprocess.run(
            ['jack_lsp', '-c', '-p'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        clients = {}
        ports_dict = {}  # Track all ports by full name to avoid duplicates
        current_port = None
        current_properties = None
        current_connections = []
        
        for line in result.stdout.split('\n'):
            if not line:
                continue
            
            # Format with -c -p is:
            # port_name (no indent)
            # properties: output,physical,terminal, (tab indented)
            # connection (3 spaces)
            
            if line.startswith('\tproperties:'):
                # This is properties info
                if current_port:
                    current_properties = line.strip().replace('properties:', '').strip()
            elif line.startswith('   '):
                # This is a connection (3 spaces)
                current_connections.append(line.strip())
            else:
                # This is a port name (no indent)
                # Save previous port
                if current_port and current_properties:
                    # Skip MIDI ports based on properties
                    if 'midi' not in current_properties.lower():
                        client_name = current_port.split(':')[0]
                        
                        # Determine direction from JACK properties (the correct way)
                        # JACK semantics: "output" property = port outputs audio, "input" property = port accepts audio
                        if 'output' in current_properties.lower():
                            direction = "output"
                        elif 'input' in current_properties.lower():
                            direction = "input"
                        else:
                            # Fallback (should rarely happen)
                            direction = "output"
                        
                        if client_name not in clients:
                            clients[client_name] = []
                        
                        port_info = {
                            "name": current_port,
                            "type": "audio",
                            "direction": direction,
                            "connections": current_connections.copy()
                        }
                        clients[client_name].append(port_info)
                        ports_dict[current_port] = port_info
                
                current_port = line.strip()
                current_properties = None
                current_connections = []
        
        # Don't forget the last port
        if current_port and current_properties and 'midi' not in current_properties.lower():
            if current_port not in ports_dict:
                client_name = current_port.split(':')[0]
                
                # Determine direction from JACK properties
                if 'output' in current_properties.lower():
                    direction = "output"
                elif 'input' in current_properties.lower():
                    direction = "input"
                else:
                    direction = "output"
            
            if client_name not in clients:
                clients[client_name] = []
            
            port_info = {
                "name": current_port,
                "type": "audio",
                "direction": direction,
                "connections": current_connections
            }
            clients[client_name].append(port_info)
            ports_dict[current_port] = port_info
        
        # Filter out metadata/type description "clients" that aren't real JACK clients
        filtered_clients = {}
        for client_name, ports in clients.items():
            # Skip clients that are just type descriptions or MIDI-only
            if 'bit' in client_name.lower() and ('float' in client_name.lower() or 'raw' in client_name.lower()):
                continue
            # Skip a2j and other MIDI bridges
            if client_name.lower() in ['a2j', 'a2jmidid']:
                continue
            # Only include if client has audio ports
            if ports:
                filtered_clients[client_name] = ports
        
        # Build connection list - only from output ports to avoid duplicates
        # JACK only lists connections under output ports
        connections = []
        seen_connections = set()
        for client_ports in filtered_clients.values():
            for port in client_ports:
                # Only process connections from output ports
                if port["direction"] == "output":
                    for conn in port["connections"]:
                        # Create a canonical connection tuple to avoid duplicates
                        conn_key = (port["name"], conn)
                        if conn_key not in seen_connections:
                            connections.append(conn_key)
                            seen_connections.add(conn_key)
        
        return {"clients": filtered_clients, "connections": connections}
    
    except Exception as e:
        print(f"Error getting JACK graph: {e}")
        return {"clients": {}, "connections": []}

@app.get("/jack/graph")
async def get_graph(user_id: str = Depends(get_current_user_id)):
    """Get current JACK audio routing graph"""
    return get_jack_graph()

@app.post("/jack/connect")
async def connect_ports(
    source: str,
    dest: str,
    user_id: str = Depends(get_current_user_id)
):
    """Connect two JACK ports"""
    try:
        result = subprocess.run(
            ['jack_connect', source, dest],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"status": "ok", "source": source, "dest": dest}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Connection failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jack/disconnect")
async def disconnect_ports(
    source: str,
    dest: str,
    user_id: str = Depends(get_current_user_id)
):
    """Disconnect two JACK ports"""
    try:
        result = subprocess.run(
            ['jack_disconnect', source, dest],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return {"status": "ok", "source": source, "dest": dest}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Disconnection failed: {result.stderr}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket for real-time graph updates
active_connections: List[WebSocket] = []

@app.websocket("/ws/patchbay")
async def websocket_patchbay(websocket: WebSocket):
    """WebSocket endpoint for real-time JACK graph updates"""
    # Get token and room_id from query parameters
    token = websocket.query_params.get("token")
    room_id = websocket.query_params.get("room_id")
    
    # Validate token before accepting connection
    user_id = None
    if token:
        user_id = get_user_from_token(token)
    
    if not user_id:
        # Reject unauthorized connection
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Check if user has patchbay access
    user_info = get_user_info(user_id)
    if not user_info or not user_info["has_patchbay_access"]:
        await websocket.close(code=1008, reason="Patchbay access denied")
        return
    
    # Validate room_id
    if not room_id:
        await websocket.close(code=1008, reason="Room ID required")
        return
    
    room = ROOMS.get(room_id)
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return
    
    # Accept the connection
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial graph
        graph = get_jack_graph()
        await websocket.send_json({"type": "graph", "data": graph})
        
        # Keep connection alive and send updates
        while True:
            # Wait for client messages (connection/disconnection requests)
            data = await websocket.receive_json()
            
            if data["type"] == "connect":
                try:
                    subprocess.run(
                        ['jack_connect', data["source"], data["dest"]],
                        check=True,
                        capture_output=True
                    )
                    # Broadcast updated graph to all clients
                    graph = get_jack_graph()
                    for conn in active_connections:
                        try:
                            await conn.send_json({"type": "graph", "data": graph})
                        except:
                            pass
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data["type"] == "disconnect":
                try:
                    subprocess.run(
                        ['jack_disconnect', data["source"], data["dest"]],
                        check=True,
                        capture_output=True
                    )
                    # Broadcast updated graph
                    graph = get_jack_graph()
                    for conn in active_connections:
                        try:
                            await conn.send_json({"type": "graph", "data": graph})
                        except:
                            pass
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif data["type"] == "refresh":
                graph = get_jack_graph()
                await websocket.send_json({"type": "graph", "data": graph})
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
def generate_self_signed_cert():
    """Generate self-signed certificate for development"""
    CERTS_PATH.mkdir(exist_ok=True)
    cert_file = CERTS_PATH / "cert.pem"
    key_file = CERTS_PATH / "key.pem"
    
    if cert_file.exists() and key_file.exists():
        print(f"Using existing self-signed certificate")
        return str(cert_file), str(key_file)
    
    print("Generating self-signed certificate for development...")
    print("⚠️  WARNING: Self-signed certificates should only be used for development!")
    print("⚠️  For production, use proper certificates from Let's Encrypt or a CA")
    
    # Generate certificate using openssl
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", str(key_file),
        "-out", str(cert_file),
        "-days", "365",
        "-nodes",
        "-subj", f"/CN={HUB_HOST}"
    ], check=True)
    
    print(f"✓ Certificate generated at {cert_file}")
    return str(cert_file), str(key_file)

if __name__ == "__main__":
    import uvicorn
    
    # Determine SSL configuration
    if USE_SSL:
        # Use provided certificate files
        ssl_certfile = SSL_CERTFILE
        ssl_keyfile = SSL_KEYFILE
        protocol = "https"
        print(f"Using SSL certificate: {ssl_certfile}")
    else:
        # Generate self-signed certificate for development
        try:
            ssl_certfile, ssl_keyfile = generate_self_signed_cert()
            protocol = "https"
        except Exception as e:
            print(f"⚠️  Could not generate SSL certificate: {e}")
            print("⚠️  Starting server without SSL (HTTP only)")
            print("⚠️  WARNING: Credentials will be transmitted in plaintext!")
            ssl_certfile = None
            ssl_keyfile = None
            protocol = "http"
    
    print(f"\n{'='*60}")
    print(f"JackTrip Hub Server")
    print(f"{'='*60}")
    print(f"URL: {protocol}://{HUB_HOST}:{HUB_PORT}")
    if protocol == "https" and not USE_SSL:
        print(f"⚠️  Using self-signed certificate - browsers will show warnings")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=HUB_PORT,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile
    )
