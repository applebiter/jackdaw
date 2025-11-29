#!/bin/bash
# Quick test script for JackTrip hub functionality

echo "JackTrip Hub Quick Test"
echo "======================="
echo ""

HUB_URL="${HUB_URL:-http://localhost:8000}"

echo "Testing hub at: $HUB_URL"
echo ""

# Test 1: Check hub health
echo "1. Checking hub health..."
HEALTH=$(curl -s "$HUB_URL/health")
if [ $? -eq 0 ]; then
    echo "✓ Hub is responding"
    echo "  Status: $HEALTH"
else
    echo "✗ Hub is not responding. Is it running?"
    echo "  Start with: cd tools/jacktrip_hub && ./run_local_hub.sh"
    exit 1
fi
echo ""

# Test 2: Authenticate
echo "2. Authenticating..."
AUTH_RESPONSE=$(curl -s -X POST "$HUB_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"demo","password":"demo"}')

TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo "✓ Authentication successful"
    echo "  Token: ${TOKEN:0:16}..."
else
    echo "✗ Authentication failed"
    echo "  Response: $AUTH_RESPONSE"
    exit 1
fi
echo ""

# Test 3: List rooms
echo "3. Listing rooms..."
ROOMS=$(curl -s -H "Authorization: Bearer $TOKEN" "$HUB_URL/rooms")
ROOM_COUNT=$(echo "$ROOMS" | grep -o '"id"' | wc -l)
echo "✓ Found $ROOM_COUNT active room(s)"
if [ "$ROOM_COUNT" -gt 0 ]; then
    echo "  Rooms: $ROOMS"
fi
echo ""

# Test 4: Create a test room
echo "4. Creating test room..."
CREATE_RESPONSE=$(curl -s -X POST "$HUB_URL/rooms" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Test Room","max_participants":4}')

ROOM_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$ROOM_ID" ]; then
    echo "✓ Room created successfully"
    echo "  Room ID: $ROOM_ID"
else
    echo "✗ Failed to create room"
    echo "  Response: $CREATE_RESPONSE"
    exit 1
fi
echo ""

# Test 5: Join the room
echo "5. Joining room..."
JOIN_RESPONSE=$(curl -s -X POST "$HUB_URL/rooms/$ROOM_ID/join" \
    -H "Authorization: Bearer $TOKEN")

HUB_HOST=$(echo "$JOIN_RESPONSE" | grep -o '"hub_host":"[^"]*"' | cut -d'"' -f4)
JACK_PORT=$(echo "$JOIN_RESPONSE" | grep -o '"jacktrip_port":[0-9]*' | cut -d':' -f2)

if [ -n "$HUB_HOST" ] && [ -n "$JACK_PORT" ]; then
    echo "✓ Joined room successfully"
    echo "  Hub host: $HUB_HOST"
    echo "  JackTrip port: $JACK_PORT"
    echo "  Connect with: jacktrip -C $HUB_HOST -p $JACK_PORT -q 4"
else
    echo "✗ Failed to join room"
    echo "  Response: $JOIN_RESPONSE"
fi
echo ""

# Test 6: Leave the room
echo "6. Leaving room..."
LEAVE_RESPONSE=$(curl -s -X POST "$HUB_URL/rooms/$ROOM_ID/leave" \
    -H "Authorization: Bearer $TOKEN")

if echo "$LEAVE_RESPONSE" | grep -q '"status":"ok"'; then
    echo "✓ Left room successfully"
else
    echo "✗ Failed to leave room"
    echo "  Response: $LEAVE_RESPONSE"
fi
echo ""

echo "======================="
echo "All tests completed!"
echo ""
echo "Next steps:"
echo "  1. Enable jacktrip_client plugin in voice_assistant_config.json"
echo "  2. Say: 'create jam room test'"
echo "  3. Say: 'list jam rooms'"
echo "  4. Say: 'join jam room test'"
