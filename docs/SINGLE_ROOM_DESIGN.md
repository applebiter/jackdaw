# Single Room Band Collaboration - Design Document

## Overview
Transform the JackTrip hub from a multi-room system into a focused single-band collaboration tool where one persistent room serves all band members with granular permission controls.

## Key Requirements

### 1. Single Room Architecture
- **One persistent room** that starts automatically with the hub
- No room creation/deletion UI - the room just exists
- All authenticated band members connect to the same room
- JackTrip server process stays running as long as hub is up
- **New clients join with no audio connections** - prevents accidental feedback/routing
- Only authorized users can create initial audio routing

### 2. User Roles & Permissions

#### Owner (First User)
- First user to register becomes the permanent owner
- Full patchbay access (can route all audio connections)
- Can grant/revoke patchbay access to other members
- Cannot be demoted or removed
- Sees "Permissions" management UI

#### Band Members (Subsequent Users)
- Can authenticate and join the room
- Can use JackTrip to send/receive audio
- **By default: NO patchbay access** (audio only)
- Can be granted patchbay access by owner
- If granted access: can view and modify patchbay connections

### 3. Simplified Workflow

#### For Owner:
1. Start hub server → room auto-created, JackTrip server starts
2. Register first account → becomes owner
3. Login → see dashboard with:
   - Active band members list
   - Patchbay access (always available)
   - Permission controls (grant/revoke access to members)
4. Voice/web can control patchbay

#### For Band Members:
1. Register account → become member (not owner)
2. Login → see dashboard with:
   - Active band members list
   - "Join Session" button (starts JackTrip client)
   - Patchbay link (if granted access) or "Access Restricted" message
3. Join session → JackTrip client connects
   - **Client ports appear disconnected by default**
   - No automatic routing - engineer must explicitly connect channels
4. If granted patchbay access → can view/modify routing

## Audio Routing Behavior

### Default Connection Policy
When a JackTrip client connects to the hub:
- ❌ **NO automatic connections are made**
- Client's send ports appear disconnected
- Client's receive ports appear disconnected
- Owner/engineer must explicitly route audio

### Rationale
1. **Prevents Feedback** - New connections won't create feedback loops
2. **Controlled Routing** - Engineer decides who hears what
3. **Professional Workflow** - Matches live sound engineering practices
4. **Security** - Members can't accidentally route themselves to hear everything

### Engineer's Responsibility
The authorized engineer (owner + granted members) must:
1. Connect member's send ports to desired destinations
2. Connect desired sources to member's receive ports
3. Test audio before member goes live
4. Adjust monitoring mixes as needed

### Implementation
JackTrip hub server uses the `-p 5` flag (no auto patching mode), which disables all automatic audio routing when clients connect.

### Example Connection Flow
```
1. Member "vocalist" joins → ports appear:
   - vocalist:send_1 (disconnected)
   - vocalist:send_2 (disconnected)
   - vocalist:receive_1 (disconnected)
   - vocalist:receive_2 (disconnected)

2. Engineer connects:
   - vocalist:send_1 → drummer:receive_1 (vocalist to drummer's monitors)
   - vocalist:send_2 → drummer:receive_2
   - drummer:send_1 → vocalist:receive_1 (drummer to vocalist's monitors)
   - drummer:send_2 → vocalist:receive_2

3. Now both can hear each other
```

## Implementation Plan (Incremental Approach)

### Phase 1: Add Permission System
**Goal:** Add user permissions without breaking existing functionality

#### Database Changes
```sql
ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN has_patchbay_access BOOLEAN DEFAULT 0;
```

#### Backend Changes
- Add `is_owner` and `has_patchbay_access` fields to User model
- Update `create_user()`: first user gets `is_owner=true, has_patchbay_access=true`
- Update `LoginResponse` to include permission flags
- Add endpoints:
  - `GET /users` - List all users (owner only)
  - `POST /users/{user_id}/permissions` - Grant/revoke patchbay access (owner only)
- Update WebSocket patchbay check: allow if `user.has_patchbay_access == true`
- **No-auto-routing already implemented:** JackTrip hub uses `-p 5` flag for no auto-patching

#### Frontend Changes
- Add permissions UI to rooms.html (shown only to owner)
- Show patchbay link conditionally based on `has_patchbay_access`
- Show "Access Restricted" message if no patchbay access

### Phase 2: Single Room Mode (Config Option)
**Goal:** Add optional single-room mode alongside existing multi-room

#### Configuration
Add to `run_local_hub.sh`:
```bash
export SINGLE_ROOM_MODE="${SINGLE_ROOM_MODE:-true}"  # Enable by default
export BAND_NAME="${BAND_NAME:-The Band}"            # Default room name
```

#### Backend Changes
- Add `SINGLE_ROOM_MODE` config check in startup
- If enabled:
  - Create default room on startup with name from `BAND_NAME`
  - Store room_id globally (`DEFAULT_ROOM_ID`)
  - Disable `POST /rooms` endpoint (return 403 or hide)
  - `/join` endpoint: automatically join the default room
  - `/leave` endpoint: leave room but keep JackTrip server running
  
#### Frontend Changes
- If single room mode:
  - Hide "Create Room" button
  - Auto-show default room as "The Band Session"
  - Simplify UI: just show "Join Session" and members list
  - Skip room selection modal

### Phase 3: Voice Assistant Updates
**Goal:** Update voice plugin for single-room workflow

#### Plugin Changes
- Remove "create jam room" command (or make it no-op)
- Simplify "join jam room" → just "join session" (no name needed)
- "list jam rooms" → "list band members"
- Remove room name from status messages
- Update commands:
  - ✅ "join session" → connect to the default room
  - ✅ "leave session" → disconnect JackTrip
  - ✅ "who's here" → list active band members
  - ✅ "session status" → show connection status
  - ❌ Remove: "create jam room [name]"
  - ❌ Remove: "join jam room [name]"

### Phase 4: UI Simplification (Post Single-Room)
**Goal:** Remove multi-room artifacts from UI

- Remove room list
- Remove room creation modal
- Single dashboard showing:
  - Band name
  - Active members
  - Join/Leave button
  - Patchbay link (if permitted)
  - Permissions panel (if owner)

## API Endpoints (After Refactor)

### Authentication
- `POST /auth/register` - Create account (first user becomes owner)
- `POST /auth/login` - Login, returns permissions in response

### Session Management
- `POST /join` - Join the band session, returns JackTrip connection info
- `POST /leave` - Leave session (disconnect JackTrip client)
- `GET /members` - List currently connected band members

### Permissions (Owner Only)
- `GET /users` - List all registered users
- `POST /users/{user_id}/permissions` - Grant/revoke patchbay access
  ```json
  {
    "has_patchbay_access": true
  }
  ```

### Patchbay (Owner + Granted Members)
- `GET /ws/patchbay` - WebSocket for real-time JACK graph
  - Checks `user.has_patchbay_access` before accepting connection
  - Allows connections/disconnections if permitted

### Health
- `GET /health` - Server status

## Configuration Options

### Environment Variables
```bash
# Single room mode (required)
SINGLE_ROOM_MODE=true           # Enable single-room mode
BAND_NAME="The Band"            # Name shown in UI

# Existing config
HUB_HOST=karate                 # Hostname for JackTrip clients
JACKTRIP_BASE_PORT=4464         # JackTrip server port
SSL_CERTFILE=/path/to/cert.pem  # HTTPS certificate
SSL_KEYFILE=/path/to/key.pem    # HTTPS private key
```

## Migration Strategy

### For Existing Deployments
1. **Database Migration:**
   ```bash
   # Add new columns to existing database
   sqlite3 hub.db "ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT 0;"
   sqlite3 hub.db "ALTER TABLE users ADD COLUMN has_patchbay_access BOOLEAN DEFAULT 0;"
   
   # Set first user as owner
   sqlite3 hub.db "UPDATE users SET is_owner=1, has_patchbay_access=1 WHERE id=(SELECT id FROM users ORDER BY created_at LIMIT 1);"
   ```

2. **Config Update:**
   ```bash
   # Add to run_local_hub.sh
   export SINGLE_ROOM_MODE=true
   export BAND_NAME="My Band"
   ```

3. **Restart hub** - default room auto-creates

### Backward Compatibility
- If `SINGLE_ROOM_MODE=false`: behaves like current multi-room system
- Allows gradual migration
- Old deployments continue working unchanged

## Security Considerations

### Permission Checks
- All patchbay operations verify `has_patchbay_access` flag
- Owner permissions checked for user management endpoints
- WebSocket connections validate permissions on connect

### Owner Protection
- Cannot delete or demote the owner account
- Owner flag is immutable after creation
- If owner loses access, requires database manual intervention (by design)

## Testing Plan

### Unit Tests
- [ ] First user becomes owner
- [ ] Subsequent users don't become owner
- [ ] Owner can grant patchbay access
- [ ] Owner can revoke patchbay access
- [ ] Non-owner cannot manage permissions
- [ ] Patchbay WebSocket rejects non-permitted users
- [ ] New JackTrip clients appear with no connections

### Integration Tests
- [ ] Owner can access patchbay immediately
- [ ] Member cannot access patchbay without permission
- [ ] Member can access patchbay after permission granted
- [ ] Multiple members can join same room
- [ ] JackTrip server stays up when members leave
- [ ] New client ports appear disconnected
- [ ] Engineer can manually route new client audio

### User Acceptance Tests
1. **Owner Workflow:**
   - [ ] First registration makes me owner
   - [ ] I can access patchbay
   - [ ] I can see permissions panel
   - [ ] I can grant access to band member
   - [ ] Band member can now access patchbay

2. **Member Workflow:**
   - [ ] I register and join
   - [ ] I cannot access patchbay (restricted)
   - [ ] Owner grants me access
   - [ ] I can now access patchbay

3. **Voice Commands:**
   - [ ] "join session" connects to band room
   - [ ] "who's here" lists active members
   - [ ] "session status" shows my connection status

## Implementation Timeline

### Phase 1: Permissions (2-3 hours)
- Database schema update
- Backend permission logic
- Frontend permissions UI
- Testing

### Phase 2: Single Room Mode (2-3 hours)
- Config and startup logic
- Auto-create default room
- Conditional endpoint disabling
- UI adjustments

### Phase 3: Voice Updates (1-2 hours)
- Update plugin commands
- Test voice workflows
- Update help text

### Phase 4: UI Cleanup (1-2 hours)
- Simplify dashboard
- Remove multi-room artifacts
- Polish UX

**Total Estimated Time:** 6-10 hours

## Open Questions

1. **Room Persistence:** Should the default room survive hub restarts?
   - **Proposal:** Room recreated on startup, participants cleared (fresh session each time)

2. **Owner Transfer:** Should owner be transferable?
   - **Proposal:** No, requires manual database edit (prevents accidents)

3. **Multiple Owners:** Should we support multiple owners?
   - **Proposal:** No, single owner keeps permissions simple

4. **Member Limit:** Should there be a max participants?
   - **Proposal:** Keep configurable (default 8), but UI shows unlimited

5. **Voice Patchbay Access:** Can voice commands control patchbay?
   - **Proposal:** Not in first version (patchbay is visual), add later if needed

## Success Metrics

- ✅ Owner can grant patchbay access in < 30 seconds
- ✅ Member can join session without any room selection
- ✅ Only permitted users can access patchbay
- ✅ Voice commands work without mentioning room names
- ✅ Zero config changes needed for typical band use case
