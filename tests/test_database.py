#!/usr/bin/env python3
"""
Test script to verify database integration
"""

import json
import psycopg2
import socket

# Load config
with open('voice_assistant_config.json', 'r') as f:
    config = json.load(f)

hostname = socket.gethostname()
db_config = config['database']

print(f"Testing database integration for host: {hostname}")
print(f"Connecting to: {db_config['host']}:{db_config['port']}/{db_config['database']}")

try:
    # Connect to database
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    print("✅ Connected to database")
    
    # Get or create session
    with conn.cursor() as cur:
        cur.execute("SELECT get_active_session(%s, %s)", (hostname, 30))
        session_id = cur.fetchone()[0]
        print(f"✅ Session ID: {session_id}")
        conn.commit()
    
    # Add test message
    with conn.cursor() as cur:
        cur.execute(
            "SELECT add_message(%s, %s, %s, %s)",
            (hostname, session_id, 'user', 'Test query from Python')
        )
        conn.commit()
        print("✅ Added test user message")
    
    # Add test response
    with conn.cursor() as cur:
        cur.execute(
            "SELECT add_message(%s, %s, %s, %s)",
            (hostname, session_id, 'assistant', 'Test response from assistant')
        )
        conn.commit()
        print("✅ Added test assistant message")
    
    # Retrieve conversation history
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role, content FROM get_conversation_history(%s, %s, %s)",
            (hostname, session_id, 30000)
        )
        history = cur.fetchall()
        print(f"\n📚 Retrieved {len(history)} messages from history:")
        for role, content in history:
            print(f"   {role}: {content}")
    
    conn.close()
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
