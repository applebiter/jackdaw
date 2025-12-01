# LLM Enhancement Architecture

## Overview

This document describes the architecture for two major enhancements to the LLM plugin:
1. **RAG (Retrieval-Augmented Generation)** - Enable the LLM to answer questions about your music library using vector search
2. **Tool Calling** - Enable the LLM to control the voice assistant by calling registered tools/functions

## 1. RAG Implementation

### 1.1 Purpose

Enable natural language queries about the music library:
- "What jazz albums do I have from the 70s?"
- "Find tracks with piano solos"
- "What's in my collection by Miles Davis?"
- "Show me upbeat songs for a workout"

### 1.2 Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  RAGManager         │
│  - embed_query()    │
│  - search()         │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  ChromaDB           │
│  Vector Store       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Retrieved Context  │
│  (Top K documents)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Query          │
│  (with context)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Response       │
└─────────────────────┘
```

### 1.3 Components

#### RAGManager Class (`rag_manager.py`)

```python
class RAGManager:
    """Manages vector embeddings and retrieval for music library."""
    
    def __init__(self, db_path, collection_name="music_library"):
        """
        Initialize RAG manager.
        
        Args:
            db_path: Path to SQLite music library database
            collection_name: ChromaDB collection name
        """
        
    def index_library(self, force_rebuild=False):
        """
        Index all music library metadata into vector store.
        
        Args:
            force_rebuild: If True, rebuild entire index from scratch
        """
        
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for query text.
        
        Args:
            query: Natural language query
            
        Returns:
            Embedding vector
        """
        
    def search(self, query: str, k: int = 5) -> List[dict]:
        """
        Search for relevant documents.
        
        Args:
            query: Natural language query
            k: Number of results to return
            
        Returns:
            List of documents with metadata and relevance scores
        """
        
    def format_context(self, results: List[dict]) -> str:
        """
        Format search results for LLM context injection.
        
        Args:
            results: Search results from search()
            
        Returns:
            Formatted context string
        """
```

#### Database Schema Integration

Use existing `music_library.sqlite3` schema:
- `albums` table: id, title, artist, year, genre
- `tracks` table: id, album_id, title, track_number, duration, file_path

Each document in vector store contains:
```python
{
    "id": "album_123",
    "type": "album",  # or "track"
    "text": "Album: Kind of Blue by Miles Davis (1959), Genre: Jazz",
    "metadata": {
        "album_id": 123,
        "title": "Kind of Blue",
        "artist": "Miles Davis",
        "year": 1959,
        "genre": "Jazz",
        "track_count": 5
    }
}
```

### 1.4 Chunking Strategy

**Album-level chunks:**
- One document per album
- Text: "{album_title} by {artist}, released {year}, genre {genre}"
- Includes track listing in metadata

**Track-level chunks:**
- One document per track
- Text: "{track_title} by {artist} from {album_title}, {duration}s, genre {genre}"
- Includes file path for playback

**Combined approach:**
- Index both album and track documents
- Album documents for high-level queries
- Track documents for specific song searches

### 1.5 Embedding Model

Use Ollama's `nomic-embed-text` model:
- Fast and efficient (137M parameters)
- Supports up to 8192 context length
- Good for semantic search
- Local inference (no external API)

Alternative: `mxbai-embed-large` for higher quality (335M parameters)

### 1.6 Vector Store Configuration

**ChromaDB Settings:**
```python
{
    "persist_directory": "./chroma_db",
    "collection_name": "music_library",
    "distance_metric": "cosine",  # cosine similarity
    "embedding_function": OllamaEmbeddings("nomic-embed-text")
}
```

**Retrieval Parameters:**
- `k = 5`: Return top 5 most relevant documents
- `score_threshold = 0.7`: Only return if similarity > 0.7
- `max_context_length = 2000`: Limit injected context to prevent overflow

### 1.7 Context Injection

Modify LLM prompt to include retrieved context:

```python
def build_rag_prompt(query: str, context: str, conversation_history: str) -> str:
    """Build prompt with RAG context."""
    return f"""You are a helpful voice assistant with access to the user's music library.

MUSIC LIBRARY CONTEXT:
{context}

CONVERSATION HISTORY:
{conversation_history}

USER QUERY: {query}

Answer the user's query using the music library context provided. If the context doesn't contain relevant information, say so. Be conversational and friendly."""
```

### 1.8 Index Update Strategy

**Initial indexing:**
- Run on first use or when database is empty
- Show progress in GUI or log

**Incremental updates:**
- Detect changes by comparing album/track counts
- Re-index only new or modified entries
- Option to force full rebuild

**Trigger points:**
- After music scanner completes
- Manual "Rebuild Index" button in music scanner GUI
- Automatic check on assistant startup (if database modified)

### 1.9 Implementation Phases

**Phase 1: Core RAG (2-3 hours)**
- Install ChromaDB (`pip install chromadb`)
- Create `rag_manager.py` with basic indexing
- Implement search and context formatting
- Unit tests for embedding and retrieval

**Phase 2: LLM Integration (1-2 hours)**
- Modify `llm_query_processor.py` to detect music queries
- Add RAG context injection
- Test with various query types

**Phase 3: GUI Integration (1 hour)**
- Add "Rebuild Music Index" button to music scanner
- Show indexing progress
- Display index statistics (document count, last updated)

**Phase 4: Optimization (1-2 hours)**
- Tune retrieval parameters (k, threshold)
- Improve chunking strategy based on results
- Add caching for common queries

**Total estimated time: 5-8 hours**

### 1.10 Testing Plan

**Test Queries:**
1. "What albums do I have by [artist]?"
2. "Find jazz albums from the 1960s"
3. "What's the longest track in my collection?"
4. "Show me all albums with [word] in the title"
5. "What genres do I listen to most?"

**Success Criteria:**
- 90%+ accuracy for artist/album queries
- Returns relevant results for genre+year queries
- Handles misspellings gracefully
- Response time < 3 seconds

---

## 2. Tool Calling Implementation

### 2.1 Purpose

Enable the LLM to control the voice assistant by calling functions:
- "Play some jazz" → `search_music(genre="jazz")` + `play_tracks()`
- "What's currently playing?" → `get_playback_status()`
- "Skip to next track" → `next_track()`
- "Set volume to 70%" → `set_volume(70)`

### 2.2 Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Query          │
│  (with tool defs)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Response       │
│  - text OR          │
│  - function_call    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  ToolExecutor       │
│  - validate_call()  │
│  - execute()        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Plugin Method      │
│  (actual execution) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Function Result    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Query (2nd)    │
│  (with result)      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Final Response     │
└─────────────────────┘
```

### 2.3 Components

#### ToolRegistry Class (`tool_registry.py`)

```python
class Tool:
    """Represents a callable tool."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        function: callable,
        requires_confirmation: bool = False
    ):
        """
        Define a tool.
        
        Args:
            name: Function name (e.g., "search_music")
            description: What the tool does
            parameters: JSON Schema for parameters
            function: Actual callable
            requires_confirmation: If True, ask user before executing
        """
        
    def to_openai_format(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolRegistry:
    """Registry of available tools for LLM."""
    
    def __init__(self):
        self.tools = {}
        
    def register(self, tool: Tool):
        """Register a new tool."""
        
    def get_tool_definitions(self) -> List[dict]:
        """Get all tools in OpenAI format for LLM."""
        
    def execute(self, tool_name: str, arguments: dict) -> dict:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of tool to call
            arguments: Parameters dict
            
        Returns:
            {
                "success": True/False,
                "result": result data or error message,
                "requires_followup": bool
            }
        """
```

#### ToolExecutor Class (in `llm_query_processor.py`)

```python
class ToolExecutor:
    """Handles tool execution and multi-turn conversations."""
    
    def __init__(self, registry: ToolRegistry, plugin_loader):
        self.registry = registry
        self.plugin_loader = plugin_loader
        
    def process_function_call(self, function_call: dict) -> dict:
        """
        Process a function call from LLM.
        
        Args:
            function_call: {
                "name": "tool_name",
                "arguments": "{json_string}"
            }
            
        Returns:
            Execution result
        """
        
    def handle_multi_turn(
        self,
        query: str,
        max_iterations: int = 3
    ) -> str:
        """
        Handle multi-turn conversation with tool calls.
        
        Args:
            query: User's original query
            max_iterations: Max tool call rounds
            
        Returns:
            Final response text
        """
```

### 2.4 Tool Definitions

#### Music Search Tool

```python
{
    "name": "search_music",
    "description": "Search the music library by artist, album, genre, or year",
    "parameters": {
        "type": "object",
        "properties": {
            "artist": {
                "type": "string",
                "description": "Artist name to search for"
            },
            "album": {
                "type": "string",
                "description": "Album title to search for"
            },
            "genre": {
                "type": "string",
                "description": "Genre to filter by (e.g., Jazz, Rock, Classical)"
            },
            "year": {
                "type": "integer",
                "description": "Year to filter by"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 10
            }
        }
    },
    "function": lambda **kwargs: music_player_plugin.search_library(**kwargs)
}
```

#### Playback Control Tools

```python
{
    "name": "play_tracks",
    "description": "Play a list of tracks by their IDs",
    "parameters": {
        "type": "object",
        "properties": {
            "track_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of track IDs to play"
            },
            "shuffle": {
                "type": "boolean",
                "description": "Whether to shuffle the playlist",
                "default": False
            }
        },
        "required": ["track_ids"]
    }
}

{
    "name": "get_playback_status",
    "description": "Get current playback status (playing/paused, current track, volume)",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

{
    "name": "pause_playback",
    "description": "Pause current playback",
    "parameters": {"type": "object", "properties": {}}
}

{
    "name": "resume_playback",
    "description": "Resume paused playback",
    "parameters": {"type": "object", "properties": {}}
}

{
    "name": "next_track",
    "description": "Skip to next track",
    "parameters": {"type": "object", "properties": {}}
}

{
    "name": "previous_track",
    "description": "Go to previous track",
    "parameters": {"type": "object", "properties": {}}
}

{
    "name": "set_volume",
    "description": "Set playback volume",
    "parameters": {
        "type": "object",
        "properties": {
            "volume": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Volume level (0-100)"
            }
        },
        "required": ["volume"]
    }
}
```

#### System Query Tools

```python
{
    "name": "get_time",
    "description": "Get current time",
    "parameters": {"type": "object", "properties": {}}
}

{
    "name": "get_date",
    "description": "Get current date",
    "parameters": {"type": "object", "properties": {}}
}
```

### 2.5 Model Selection

**Compatible Ollama Models:**
- `llama3.1:8b` - Best balance (supports tool calling)
- `mistral-nemo:12b` - Larger, more accurate
- `qwen2.5:7b` - Fast, good tool calling support

**Recommended:** Start with `llama3.1:8b` for testing.

### 2.6 Conversation Flow

**Example: "Play some jazz"**

1. **User:** "Play some jazz"

2. **LLM (1st call):**
   ```json
   {
     "function_call": {
       "name": "search_music",
       "arguments": "{\"genre\": \"Jazz\", \"limit\": 10}"
     }
   }
   ```

3. **Tool Execution:**
   ```python
   result = music_player.search_library(genre="Jazz", limit=10)
   # Returns: [{"track_id": 42, "title": "So What", ...}, ...]
   ```

4. **LLM (2nd call with result):**
   ```json
   {
     "function_call": {
       "name": "play_tracks",
       "arguments": "{\"track_ids\": [42, 43, 44], \"shuffle\": true}"
     }
   }
   ```

5. **Tool Execution:**
   ```python
   music_player.play_tracks([42, 43, 44], shuffle=True)
   # Returns: {"success": True, "message": "Playing 3 tracks"}
   ```

6. **LLM (final response):**
   "I've started playing 3 jazz tracks from your library in shuffle mode."

### 2.7 Security and Safety

**Confirmation Required:**
- System commands (restart, shutdown)
- File operations
- Network requests

**Auto-execute:**
- Music search and playback
- Volume control
- Status queries
- Time/date queries

**Validation:**
- Parameter type checking
- Range validation (e.g., volume 0-100)
- Sanitize string inputs
- Rate limiting (max 10 tool calls per query)

**Error Handling:**
```python
def execute_tool(name: str, args: dict) -> dict:
    try:
        # Validate
        if name not in registry.tools:
            return {"success": False, "error": "Unknown tool"}
            
        # Type check
        validated_args = validate_args(args, tool.parameters)
        
        # Execute with timeout
        result = tool.function(**validated_args)
        
        return {"success": True, "result": result}
        
    except ValidationError as e:
        return {"success": False, "error": f"Invalid arguments: {e}"}
    except TimeoutError:
        return {"success": False, "error": "Tool execution timed out"}
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"success": False, "error": "Tool execution failed"}
```

### 2.8 Integration with Existing Plugins

**Plugin API Extensions:**

Add to `plugin_base.py`:
```python
class VoiceAssistantPlugin:
    def get_tools(self) -> List[Tool]:
        """
        Return list of tools this plugin provides.
        
        Returns:
            List of Tool objects for registration
        """
        return []
```

Each plugin can register its own tools:
```python
# plugins/music_player.py
class MusicPlayerPlugin(VoiceAssistantPlugin):
    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="search_music",
                description="Search music library",
                parameters={...},
                function=self.search_library
            ),
            Tool(
                name="play_tracks",
                description="Play tracks",
                parameters={...},
                function=self.play_tracks_by_ids
            ),
            # ... more tools
        ]
```

### 2.9 Implementation Phases

**Phase 1: Core Infrastructure (2-3 hours)**
- Create `tool_registry.py` with Tool and ToolRegistry classes
- Create basic ToolExecutor in `llm_query_processor.py`
- Unit tests for tool registration and execution

**Phase 2: Tool Definitions (2 hours)**
- Define all music-related tools
- Define system query tools
- Add plugin API extensions
- Implement music_player plugin tools

**Phase 3: LLM Integration (2-3 hours)**
- Modify LLM query flow to pass tool definitions
- Implement function call parsing
- Implement multi-turn conversation loop
- Handle errors and fallbacks

**Phase 4: Testing (2 hours)**
- Test each tool individually
- Test multi-turn workflows
- Test error cases
- Test with different LLM models

**Phase 5: Polish (1-2 hours)**
- Add confirmation prompts for dangerous tools
- Improve error messages
- Add logging and debugging
- Update documentation

**Total estimated time: 9-12 hours**

### 2.10 Testing Plan

**Test Cases:**

1. **Single Tool Call:**
   - "What's playing?" → get_playback_status()
   - "Pause" → pause_playback()

2. **Multi-Tool Workflow:**
   - "Play some Miles Davis" → search_music() → play_tracks()
   - "Find rock albums and play one" → search_music() → play_tracks()

3. **Error Handling:**
   - Invalid parameters → error response
   - Tool not found → graceful fallback
   - Tool execution failure → error message

4. **Edge Cases:**
   - No search results → "I couldn't find any tracks"
   - Ambiguous query → clarifying question
   - Max iterations reached → stop and respond

**Success Criteria:**
- 95%+ success rate for basic commands
- Graceful handling of errors
- Response time < 5 seconds for single tool
- Response time < 10 seconds for multi-tool

---

## 3. Combined System Architecture

### 3.1 Query Routing

Determine which system to use:

```python
def route_query(query: str) -> str:
    """Determine if query needs RAG, tools, or plain LLM."""
    
    # Music information queries → RAG
    if any(word in query.lower() for word in [
        "what", "find", "show", "list", "which", "how many"
    ]) and "music" related:
        return "rag"
    
    # Action commands → Tools
    if any(word in query.lower() for word in [
        "play", "pause", "skip", "stop", "set volume"
    ]):
        return "tools"
    
    # Everything else → Plain LLM
    return "plain"
```

### 3.2 Unified Flow

```
User Query
    │
    ▼
Route Query
    │
    ├─[information]──▶ RAG Search ──▶ LLM with Context
    │
    ├─[action]───────▶ LLM with Tools ──▶ Execute Tools
    │
    └─[other]────────▶ Plain LLM
    │
    ▼
Response
```

### 3.3 Configuration

Add to `voice_assistant_config.json`:

```json
{
  "llm": {
    "model": "llama3.1:8b",
    "temperature": 0.7,
    "tool_calling_enabled": true,
    "rag_enabled": true,
    "max_tool_iterations": 3
  },
  "rag": {
    "embedding_model": "nomic-embed-text",
    "collection_name": "music_library",
    "top_k": 5,
    "score_threshold": 0.7,
    "auto_rebuild": false
  },
  "tools": {
    "require_confirmation": [
      "system_command",
      "file_operation"
    ],
    "enabled_plugins": [
      "music_player",
      "timemachine"
    ]
  }
}
```

---

## 4. Implementation Checklist

### 4.1 RAG Implementation

- [ ] Install ChromaDB (`pip install chromadb`)
- [ ] Create `rag_manager.py` with RAGManager class
- [ ] Implement `index_library()` method
- [ ] Implement `embed_query()` using Ollama
- [ ] Implement `search()` method
- [ ] Implement `format_context()` method
- [ ] Add database change detection
- [ ] Modify `llm_query_processor.py` to use RAG
- [ ] Add "Rebuild Index" button to music scanner GUI
- [ ] Add progress display for indexing
- [ ] Write unit tests
- [ ] Test with various queries
- [ ] Optimize retrieval parameters
- [ ] Update documentation

### 4.2 Tool Calling Implementation

- [ ] Create `tool_registry.py` with Tool and ToolRegistry classes
- [ ] Implement tool registration system
- [ ] Implement OpenAI format conversion
- [ ] Define music search tools
- [ ] Define playback control tools
- [ ] Define system query tools
- [ ] Add `get_tools()` method to plugin base class
- [ ] Implement music_player plugin tools
- [ ] Create ToolExecutor in `llm_query_processor.py`
- [ ] Implement function call parsing
- [ ] Implement multi-turn conversation loop
- [ ] Add parameter validation
- [ ] Add confirmation system for dangerous tools
- [ ] Add rate limiting
- [ ] Add comprehensive error handling
- [ ] Write unit tests
- [ ] Test each tool individually
- [ ] Test multi-turn workflows
- [ ] Update documentation

### 4.3 Integration

- [ ] Implement query routing logic
- [ ] Add configuration options
- [ ] Test RAG + tool calling combination
- [ ] Update `README.md` with new features
- [ ] Create `LLM_ENHANCEMENTS.md` usage guide
- [ ] Add examples to `QUICK_REFERENCE.md`

---

## 5. Expected Outcomes

### 5.1 RAG System

**User Experience:**
- Natural language questions about music library
- Accurate answers based on actual collection
- Fast response times (< 3 seconds)
- Works offline (no external API)

**Example Interactions:**
```
User: "What jazz albums from the 60s do I have?"
Assistant: "You have 3 jazz albums from the 1960s: Kind of Blue by Miles Davis (1959), 
           A Love Supreme by John Coltrane (1965), and Time Out by Dave Brubeck (1959)."

User: "Find tracks with piano"
Assistant: "I found 47 tracks featuring piano, including So What by Miles Davis,
           Take Five by Dave Brubeck, and Clair de Lune by Claude Debussy."
```

### 5.2 Tool Calling System

**User Experience:**
- Natural language commands for actions
- Multi-step workflows handled automatically
- Confirmation for dangerous operations
- Clear feedback on what was done

**Example Interactions:**
```
User: "Play some upbeat rock music"
Assistant: [Searches library] [Finds 12 rock tracks] [Starts playback]
           "I've started playing 12 rock tracks from your library in shuffle mode."

User: "What's playing and turn it up a bit"
Assistant: [Gets status] [Increases volume]
           "Currently playing 'Sweet Child O' Mine' by Guns N' Roses. 
           I've increased the volume to 75%."
```

### 5.3 Combined Benefits

- **Smarter Assistant:** Can answer questions AND take actions
- **Better UX:** Natural conversation instead of rigid commands
- **Extensible:** Easy to add new tools via plugin system
- **Powerful Queries:** Combine search with playback ("find jazz from the 70s and play it")

---

## 6. Future Enhancements

### 6.1 Advanced RAG Features

- **Semantic similarity:** "Find songs similar to X"
- **Mood-based search:** "Play something relaxing"
- **Cross-reference:** "What else do I have from this era?"
- **Playlist generation:** "Create a workout playlist"

### 6.2 Advanced Tool Features

- **Tool chaining:** Automatic multi-step workflows
- **Conditional logic:** "If I have X, play it, otherwise play Y"
- **Scheduled actions:** "Play alarm at 7am"
- **External tools:** Weather, news, calendar integration

### 6.3 Hybrid Queries

- **Smart routing:** Automatically detect when both RAG and tools are needed
- **Context passing:** Use RAG results as tool parameters
- **Iterative refinement:** "Play that last artist I asked about"

---

## 7. Resource Requirements

### 7.1 Storage

- **ChromaDB:** ~100MB for 10,000 tracks
- **Embeddings:** ~500KB per 1,000 documents
- **Total:** ~150MB for medium library

### 7.2 Memory

- **ChromaDB:** ~200MB RAM
- **Ollama embedding:** ~500MB RAM
- **LLM model:** ~5GB RAM (llama3.1:8b)
- **Total:** ~6GB RAM (reasonable for modern systems)

### 7.3 Performance

- **Indexing:** ~1 second per 100 tracks
- **Query embedding:** ~100ms
- **Vector search:** ~50ms
- **LLM generation:** ~1-3 seconds
- **Tool execution:** ~100-500ms
- **Total query time:** 2-5 seconds

---

## 8. Dependencies

### 8.1 New Python Packages

```
chromadb>=0.4.0       # Vector database
sentence-transformers # For embeddings (if not using Ollama)
```

### 8.2 Ollama Models

```bash
# Embedding model
ollama pull nomic-embed-text

# LLM with tool calling
ollama pull llama3.1:8b
```

---

## 9. Risks and Mitigations

### 9.1 Risks

1. **LLM hallucinates tools:** Calls non-existent functions
   - *Mitigation:* Strict validation, return error for unknown tools

2. **Infinite loop:** LLM keeps calling tools without responding
   - *Mitigation:* Max iteration limit (3), timeout per tool

3. **RAG returns irrelevant results:** Low similarity scores
   - *Mitigation:* Threshold filtering, fallback to "I don't know"

4. **Performance degradation:** Large library = slow search
   - *Mitigation:* Optimize chunk size, limit top_k, add caching

5. **Breaking changes:** Ollama API updates
   - *Mitigation:* Pin versions, test before upgrading

### 9.2 Fallback Strategy

If systems fail, fall back gracefully:
- RAG fails → use plain LLM without context
- Tool calling fails → interpret as text command
- Both fail → basic voice command matching (existing system)

---

## 10. Success Metrics

### 10.1 RAG Performance

- **Accuracy:** 90% of queries return relevant results
- **Response time:** < 3 seconds
- **User satisfaction:** Positive feedback on answers

### 10.2 Tool Calling Performance

- **Success rate:** 95% of commands execute correctly
- **Response time:** < 5 seconds for single tool
- **Error rate:** < 5% of calls fail

### 10.3 System Stability

- **Uptime:** No crashes from new features
- **Memory:** Stays under 1GB additional RAM
- **CPU:** < 50% average during operation

---

*Document Version: 1.0*  
*Last Updated: November 30, 2025*  
*Author: GitHub Copilot*
