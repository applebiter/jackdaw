#!/usr/bin/env python3
"""Simple CLI to inspect recent conversations from the local SQLite store.

Usage examples:

  python inspect_conversations.py --db conversations.sqlite3 --sessions
  python inspect_conversations.py --db conversations.sqlite3 --messages --limit 20
"""

import argparse
import sqlite3
from pathlib import Path


def list_sessions(conn: sqlite3.Connection, limit: int) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, hostname, session_id, created_at, last_activity, is_active
        FROM conversation_sessions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    if not rows:
        print("No sessions found.")
        return

    for row in rows:
        print(
            f"[{row[0]}] host={row[1]} session={row[2]} "
            f"created={row[3]} last={row[4]} active={row[5]}"
        )


def list_messages(conn: sqlite3.Connection, limit: int) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, hostname, session_id, role, substr(content, 1, 80) AS preview,
               tokens, created_at
        FROM messages
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    if not rows:
        print("No messages found.")
        return

    for row in rows:
        print(
            f"[{row[0]}] host={row[1]} role={row[3]} tokens={row[5]} "
            f"at={row[6]}\n    {row[4]}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect sessions and messages in the local conversation SQLite DB.",
    )
    parser.add_argument(
        "--db",
        default="conversations.sqlite3",
        help="Path to SQLite DB file (default: conversations.sqlite3)",
    )
    parser.add_argument(
        "--sessions",
        action="store_true",
        help="List recent sessions.",
    )
    parser.add_argument(
        "--messages",
        action="store_true",
        help="List recent messages.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of rows to show (default: 10)",
    )

    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    try:
        if args.sessions:
            list_sessions(conn, args.limit)
        if args.messages:
            if args.sessions:
                print("")
            list_messages(conn, args.limit)
        if not args.sessions and not args.messages:
            print("Nothing to do: specify --sessions and/or --messages.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
