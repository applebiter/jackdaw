#!/usr/bin/env python3
"""
LLM Query Processor
Continuously polls for query files and sends them to Ollama for processing
Maintains conversation history in PostgreSQL database for multi-host setup
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import sys
from datetime import datetime
import socket
import sqlite3
import uuid


class LocalConversationStore:
    """SQLite-backed conversation store for per-host sessions and messages."""

    def __init__(self, db_path: str, hostname: str):
        self.db_path = str(db_path)
        self.hostname = hostname
        # check_same_thread=False because processor loop may evolve later;
        # current usage is single-threaded but this keeps it flexible.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    hostname TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
                    content TEXT NOT NULL,
                    tokens INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_hostname_active
                    ON conversation_sessions(hostname, is_active, last_activity DESC)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(hostname, session_id, created_at ASC)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_role
                    ON messages(role, created_at DESC)
                """
            )

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def get_or_create_session(self, inactivity_timeout_minutes: int) -> str:
        """Return an active session_id for this host, creating a new one if needed."""
        timeout_expr = f"-{int(inactivity_timeout_minutes)} minutes"
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT session_id FROM conversation_sessions
            WHERE hostname = ? AND is_active = 1
              AND last_activity > datetime('now', ?)
            ORDER BY last_activity DESC
            LIMIT 1
            """,
            (self.hostname, timeout_expr),
        )
        row = cur.fetchone()
        if row and row["session_id"]:
            session_id = row["session_id"]
            with self.conn:
                self.conn.execute(
                    "UPDATE conversation_sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,),
                )
            return session_id

        # No active session: mark old ones inactive and create a new session
        with self.conn:
            self.conn.execute(
                "UPDATE conversation_sessions SET is_active = 0 WHERE hostname = ? AND is_active = 1",
                (self.hostname,),
            )
            session_id = str(uuid.uuid4())
            self.conn.execute(
                "INSERT INTO conversation_sessions (session_id, hostname) VALUES (?, ?)",
                (session_id, self.hostname),
            )
        return session_id

    def _estimate_tokens(self, content: str) -> int:
        words = [w for w in content.split() if w]
        return int(len(words) * 1.3 + 0.5)

    def add_message(self, session_id: str, role: str, content: str) -> int:
        """Insert a message and update session last_activity. Returns token estimate."""
        token_count = self._estimate_tokens(content)
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO messages (session_id, hostname, role, content, tokens)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, self.hostname, role, content, token_count),
            )
            self.conn.execute(
                "UPDATE conversation_sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ? AND hostname = ?",
                (session_id, self.hostname),
            )
        return token_count

    def get_conversation_history(self, session_id: str, max_tokens: int) -> List[Tuple[str, str]]:
        """Return (role, content) pairs within token budget for this session."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT role, content, tokens, created_at
            FROM messages
            WHERE hostname = ? AND session_id = ?
            ORDER BY created_at DESC
            """,
            (self.hostname, session_id),
        )
        rows = cur.fetchall()
        running = 0
        selected: List[sqlite3.Row] = []
        for row in rows:
            running += row["tokens"] or 0
            if running > max_tokens:
                break
            selected.append(row)
        selected.reverse()
        return [(r["role"], r["content"]) for r in selected]


class LLMQueryProcessor:
    """Polls for query files and processes them through Ollama with conversation history"""

    def __init__(self, config_path: str = "voice_assistant_config.json"):
        """
        Initialize the query processor
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self.load_config(config_path)
        self.running = False
        
        # Get hostname for this instance
        self.hostname = socket.gethostname()
        
        # Extract config values
        self.ollama_host = self.config["ollama"]["host"]
        self.ollama_model = self.config["ollama"]["model"]
        self.ollama_options = self.config["ollama"].get("options", {})
        
        self.query_file = Path(self.config["files"]["query_file"])
        self.response_file = Path(self.config["files"]["response_file"])
        
        self.poll_interval = self.config["polling"]["interval_seconds"]
        self.delete_after_read = self.config["polling"]["delete_query_after_read"]
        
        # Database / conversation store configuration (now local SQLite per host)
        self.db_config = self.config.get("database", {})
        self.db_enabled = self.db_config.get("enabled", False)
        self.db_backend = self.db_config.get("backend", "sqlite")
        self.session_config = self.config.get("session", {})
        self.max_context_tokens = self.session_config.get("max_context_tokens", 30000)
        self.inactivity_timeout = self.session_config.get("inactivity_timeout_minutes", 30)

        self.session_id: Optional[str] = None
        self.store: Optional[LocalConversationStore] = None

        if self.db_enabled and self.db_backend == "sqlite":
            db_path_cfg = self.db_config.get("path", "conversations.sqlite3")
            db_path = Path(db_path_cfg).expanduser()
            try:
                self.store = LocalConversationStore(str(db_path), self.hostname)
                print(f"✅ Local conversation store: {db_path}")
            except Exception as e:
                print(f"❌ Failed to initialize local SQLite store: {e}")
                print("   Continuing without conversation history...")
                self.db_enabled = False
                self.store = None
        elif self.db_enabled:
            print("⚠️  Database backend enabled but not 'sqlite'; disabling history.")
            self.db_enabled = False
        
        # Track last modification time to avoid reprocessing
        self.last_mtime: Optional[float] = None
        
        print(f"LLM Query Processor initialized")
        print(f"Hostname: {self.hostname}")
        print(f"Ollama: {self.ollama_host} (model: {self.ollama_model})")
        print(f"Query file: {self.query_file}")
        print(f"Response file: {self.response_file}")
        if self.db_enabled and self.store is not None:
            print(f"Database: SQLite local store (conversation history ENABLED, max {self.max_context_tokens} tokens)")
        else:
            print("Database: DISABLED (no conversation history)")
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file '{config_path}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)
    
    def get_or_create_session(self) -> Optional[uuid.UUID]:
        """Get or create active session for this host via local store"""
        if not self.db_enabled or self.store is None:
            return None

        try:
            return self.store.get_or_create_session(self.inactivity_timeout)
        except Exception as e:
            print(f"⚠️  Error getting session: {e}")
            return None
    
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """Get conversation history for current session within token limit."""
        if not self.db_enabled or self.store is None or not self.session_id:
            return []

        try:
            return self.store.get_conversation_history(self.session_id, self.max_context_tokens)
        except Exception as e:
            print(f"⚠️  Error fetching history: {e}")
            return []
    
    def add_message(self, role: str, content: str):
        """Add a message to the local store for current session."""
        if not self.db_enabled or self.store is None or not self.session_id:
            return

        try:
            self.store.add_message(self.session_id, role, content)
        except Exception as e:
            print(f"⚠️  Error adding message: {e}")
            
    def read_query_file(self) -> Optional[str]:
        """
        Read and parse the query file, extracting non-commented text
        
        Returns:
            Query text or None if file doesn't exist or is empty
        """
        if not self.query_file.exists():
            return None
            
        # Check if file has been modified since last read
        current_mtime = self.query_file.stat().st_mtime
        if self.last_mtime is not None and current_mtime <= self.last_mtime:
            return None  # File hasn't changed
            
        self.last_mtime = current_mtime
        
        try:
            with open(self.query_file, 'r') as f:
                lines = f.readlines()
            
            # Filter out commented lines (lines starting with #)
            query_lines = [line.strip() for line in lines 
                          if line.strip() and not line.strip().startswith('#')]
            
            if not query_lines:
                return None
                
            query_text = ' '.join(query_lines)
            return query_text
            
        except Exception as e:
            print(f"Error reading query file: {e}")
            return None
            
    def send_to_ollama(self, query: str) -> Optional[str]:
        """
        Send query to Ollama with conversation history and get response
        
        Args:
            query: The query text to send
            
        Returns:
            Response text or None on error
        """
        # Get or create session
        if self.db_enabled:
            self.session_id = self.get_or_create_session()
            if self.session_id:
                print(f"📝 Session: {self.session_id}")
        
        # Build prompt with system-style instructions and conversation history
        system_instructions = (
            "You are a real-time voice assistant running under a tight latency budget. "
            "By default, respond concisely in 1–3 sentences or a very short bullet list. "
            "Only provide long, detailed explanations when the user explicitly asks for a "
            "detailed or extended answer in this turn."
        )

        prompt = query
        history_context = ""
        
        if self.db_enabled and self.session_id:
            history = self.get_conversation_history()
            if history:
                print(f"📚 Loading {len(history)} previous messages from history")
                # Build context from history
                history_lines = []
                for role, content in history:
                    if role == 'user':
                        history_lines.append(f"User: {content}")
                    elif role == 'assistant':
                        history_lines.append(f"Assistant: {content}")
                
                history_context = "\n".join(history_lines)
                prompt = (
                    f"System: {system_instructions}\n\n"
                    f"{history_context}\nUser: {query}\nAssistant:"
                )
            else:
                prompt = f"System: {system_instructions}\n\nUser: {query}\nAssistant:"
        else:
            prompt = f"System: {system_instructions}\n\nUser: {query}\nAssistant:"
        
        url = f"{self.ollama_host}/api/generate"
        
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": self.ollama_options
        }
        
        try:
            print(f"\n📤 Sending query to Ollama ({self.ollama_model})...")
            print(f"Query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get('response', '')
            
            print(f"✅ Received response ({len(response_text)} chars)")
            
            # Save to database
            if self.db_enabled and self.session_id:
                self.add_message('user', query)
                self.add_message('assistant', response_text)
                print(f"💾 Saved to conversation history")
            
            return response_text
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Error: Could not connect to Ollama at {self.ollama_host}")
            print(f"   Make sure Ollama is running: 'ollama serve'")
            return None
        except requests.exceptions.Timeout:
            print(f"⏱️  Error: Request timed out after 120 seconds")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            if e.response.status_code == 404:
                print(f"   Model '{self.ollama_model}' not found.")
                print(f"   Pull it with: ollama pull {self.ollama_model}")
            return None
        except Exception as e:
            print(f"❌ Error communicating with Ollama: {e}")
            return None
            
    def write_response_file(self, query: str, response: str):
        """
        Write the LLM response to file
        
        Args:
            query: Original query
            response: LLM response
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.response_file, 'w') as f:
                f.write(f"# Response generated at {timestamp}\n")
                f.write(f"# Query: {query}\n")
                f.write(f"#" + "="*70 + "\n\n")
                f.write(response)
                f.write("\n")
            
            print(f"💾 Response saved to: {self.response_file.absolute()}")
            
        except Exception as e:
            print(f"❌ Error writing response file: {e}")
            
    def process_query(self):
        """Process a query if available"""
        # Read query file
        query = self.read_query_file()
        
        if query is None:
            return  # No new query
            
        print(f"\n{'='*70}")
        print(f"🔍 New query detected!")
        
        # Send to Ollama
        response = self.send_to_ollama(query)
        
        if response:
            # Write response
            self.write_response_file(query, response)
            
            # Delete query file if configured
            if self.delete_after_read:
                try:
                    self.query_file.unlink()
                    print(f"🗑️  Query file deleted")
                except Exception as e:
                    print(f"⚠️  Could not delete query file: {e}")
        
        print(f"{'='*70}\n")
        
    def run(self):
        """Run the processor loop"""
        self.running = True
        print(f"\n🚀 LLM Query Processor running...")
        print(f"📂 Watching: {self.query_file.absolute()}")
        print(f"⏱️  Poll interval: {self.poll_interval}s")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                self.process_query()
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user")
        finally:
            self.stop()
            
    def stop(self):
        """Stop the processor"""
        self.running = False

        # Close local conversation store
        if self.store is not None:
            self.store.close()
            print("Local conversation store closed")

        print("LLM Query Processor stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LLM Query Processor - Polls for queries and sends to Ollama"
    )
    parser.add_argument(
        '--config',
        default='voice_assistant_config.json',
        help='Path to config file (default: voice_assistant_config.json)'
    )
    
    args = parser.parse_args()
    
    processor = LLMQueryProcessor(config_path=args.config)
    processor.run()


if __name__ == "__main__":
    main()
