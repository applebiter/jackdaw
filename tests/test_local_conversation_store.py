#!/usr/bin/env python3
"""Quick sanity test for the local SQLite conversation store used by llm_query_processor.

Run with:
  python test_local_conversation_store.py
"""

from pathlib import Path
from time import sleep
from llm_query_processor import LocalConversationStore
import socket


def main() -> None:
    hostname = socket.gethostname()
    db_path = Path("conversations_test.sqlite3")

    print(f"Using test DB: {db_path}")
    store = LocalConversationStore(str(db_path), hostname)

    # Create/get a session
    session_id = store.get_or_create_session(inactivity_timeout_minutes=30)
    print(f"Session ID: {session_id}")

    # Add a few alternating user/assistant messages
    store.add_message(session_id, "user", "Hello, how are you?")
    store.add_message(session_id, "assistant", "I'm fine, thanks for asking.")
    store.add_message(session_id, "user", "Please summarize this short conversation.")

    history = store.get_conversation_history(session_id, max_tokens=30000)
    print("History messages:")
    for role, content in history:
        print(f"  {role}: {content}")

    store.close()
    print("Done.")


if __name__ == "__main__":
    main()
