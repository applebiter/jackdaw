# Multi-Host Voice Assistant Implementation Summary

## Current Storage Design

### 1. Local SQLite Conversation Store ✅
- **Per-host database:** each machine keeps its own conversations in a local SQLite file (default: `conversations.sqlite3`).
- **Tables:**
  - `conversation_sessions` – tracks active sessions per hostname.
  - `messages` – stores all user queries and assistant responses with token estimates.
- **Behavior:**
  - One active session per host at a time.
  - Sessions identified by `(hostname, session_id)`.
  - Sessions auto-rolled based on inactivity timeout.
  - Conversation history trimmed by a max token budget.

### 2. Configuration (voice_assistant_config.json) ✅

```json
"database": {
  "enabled": true,
  "backend": "sqlite",
  "path": "conversations.sqlite3"
},
"session": {
  "strategy": "single_active",
  "inactivity_timeout_minutes": 30,
  "max_context_tokens": 30000
}
```

### 3. LLM Query Processor Updates ✅

**Key features in `llm_query_processor.py`:**
- Uses `LocalConversationStore` (SQLite) instead of PostgreSQL.
- Retrieves or creates a per-host session based on inactivity timeout.
- Loads bounded conversation history before each query.
- Stores both query and response after each LLM call.
- Enforces `max_context_tokens` budget when building context.
- Graceful fallback: if SQLite init fails or `database.enabled` is `false`, runs without history.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JACK Audio Network                        │
│                   (Networked via JackTrip)                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │  Host A │          │  Host B │          │  Host C │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                    │                     │
        │  local SQLite      │   local SQLite      │   local SQLite
        │  conversations.db  │   conversations.db  │   conversations.db
        │                    │                     │
        └────────────────────┴─────────────────────┴─────────────
```

Each host is fully independent for conversation storage; no remote DB is required.

## How It Works (Per Host)

1. **Voice command** triggers text capture (e.g., "[wake word], start recording").
2. **Query captured** and written to `llm_query.txt`.
3. **LLM processor** on the same host:
   - Opens/initializes its local SQLite file.
   - Gets or creates an active session for its hostname.
   - Loads previous messages within the `max_context_tokens` budget.
   - Builds a prompt with history + new user query.
   - Sends the prompt to Ollama.
   - Stores both user query and assistant response back into SQLite.
4. **TTS** speaks the response through JACK.
5. **Next query** on that host automatically includes prior context until the token budget or inactivity timeout causes a new session.

### Session Management Details
- One active session per host (`is_active = 1`).
- When a new interaction arrives:
  - If an existing session has `last_activity` within the timeout window, it is reused.
  - Otherwise, old sessions for that host are marked inactive and a new `session_id` (UUID) is created.
- `last_activity` is updated whenever a message is added.

### History and Token Budgeting
- Each message gets a rough token estimate: `≈ 1.3 × word_count`.
- When building history for a request:
  - Messages are scanned newest-first.
  - Messages are included until the cumulative token count would exceed `max_context_tokens`.
  - The resulting set is then ordered oldest-first and fed to the LLM.

## Developer Notes

### Inspecting Conversations

Use `sqlite3` to inspect conversations on a host:

```bash
sqlite3 conversations.sqlite3 'SELECT hostname, session_id, created_at, last_activity, is_active FROM conversation_sessions ORDER BY id DESC LIMIT 5;'

sqlite3 conversations.sqlite3 "SELECT role, substr(content,1,80) AS preview, tokens, created_at FROM messages ORDER BY id DESC LIMIT 10;"
```

### Files Most Relevant to Storage

- `llm_query_processor.py`
  - Contains `LocalConversationStore` and all session/history logic.
- `voice_assistant_config.json`
  - Controls whether history is enabled and where the SQLite file lives.
- `test_local_conversation_store.py`
  - Quick smoke test for the SQLite-backed store.

Legacy PostgreSQL-specific files (`schema.sql`, `setup_database.sh`, `test_database.py`) are no longer required for normal operation but are kept for reference.
