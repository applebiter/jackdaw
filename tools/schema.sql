-- Voice Assistant Multi-Host Conversation Database Schema
-- Run this on the karate (192.168.32.11) PostgreSQL server

-- Create database (if not exists)
-- Run as postgres user: CREATE DATABASE voice_assistant;

-- Connect to voice_assistant database before running below

-- Conversation sessions table
-- Each host maintains one active session at a time
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID DEFAULT gen_random_uuid(),
    hostname TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(hostname, session_id)
);

-- Create index for faster lookups of active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_hostname_active 
    ON conversation_sessions(hostname, is_active, last_activity DESC);

-- Messages table
-- Stores all user queries and assistant responses
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    hostname TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (hostname, session_id) 
        REFERENCES conversation_sessions(hostname, session_id) 
        ON DELETE CASCADE
);

-- Create index for faster message retrieval
CREATE INDEX IF NOT EXISTS idx_messages_session 
    ON messages(hostname, session_id, created_at ASC);

-- Create index for role-based queries
CREATE INDEX IF NOT EXISTS idx_messages_role 
    ON messages(role, created_at DESC);

-- Function to get or create active session for a host
CREATE OR REPLACE FUNCTION get_active_session(host_name TEXT, timeout_minutes INTEGER DEFAULT 30)
RETURNS UUID AS $$
DECLARE
    active_session_id UUID;
    cutoff_time TIMESTAMP;
BEGIN
    -- Calculate inactivity cutoff time
    cutoff_time := NOW() - (timeout_minutes || ' minutes')::INTERVAL;
    
    -- Try to find an active session that hasn't timed out
    SELECT session_id INTO active_session_id
    FROM conversation_sessions
    WHERE hostname = host_name
      AND is_active = TRUE
      AND last_activity > cutoff_time
    ORDER BY last_activity DESC
    LIMIT 1;
    
    -- If no active session found, mark old ones inactive and create new one
    IF active_session_id IS NULL THEN
        -- Mark any old sessions as inactive
        UPDATE conversation_sessions
        SET is_active = FALSE
        WHERE hostname = host_name AND is_active = TRUE;
        
        -- Create new session
        INSERT INTO conversation_sessions (hostname)
        VALUES (host_name)
        RETURNING session_id INTO active_session_id;
    ELSE
        -- Update last activity time
        UPDATE conversation_sessions
        SET last_activity = NOW()
        WHERE session_id = active_session_id;
    END IF;
    
    RETURN active_session_id;
END;
$$ LANGUAGE plpgsql;

-- Function to add a message and return token count
CREATE OR REPLACE FUNCTION add_message(
    host_name TEXT,
    sess_id UUID,
    msg_role TEXT,
    msg_content TEXT
)
RETURNS INTEGER AS $$
DECLARE
    token_count INTEGER;
BEGIN
    -- Rough token estimate: words * 1.3
    token_count := CEIL(array_length(string_to_array(msg_content, ' '), 1) * 1.3);
    
    -- Insert message
    INSERT INTO messages (session_id, hostname, role, content, tokens)
    VALUES (sess_id, host_name, msg_role, msg_content, token_count);
    
    -- Update session activity
    UPDATE conversation_sessions
    SET last_activity = NOW()
    WHERE session_id = sess_id AND hostname = host_name;
    
    RETURN token_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get conversation history within token limit
CREATE OR REPLACE FUNCTION get_conversation_history(
    host_name TEXT,
    sess_id UUID,
    max_tokens INTEGER DEFAULT 30000
)
RETURNS TABLE(role TEXT, content TEXT, tokens INTEGER, created_at TIMESTAMP) AS $$
DECLARE
    running_total INTEGER := 0;
BEGIN
    RETURN QUERY
    WITH ordered_messages AS (
        SELECT m.role, m.content, m.tokens, m.created_at,
               SUM(m.tokens) OVER (ORDER BY m.created_at DESC) as cumulative_tokens
        FROM messages m
        WHERE m.hostname = host_name
          AND m.session_id = sess_id
        ORDER BY m.created_at DESC
    )
    SELECT om.role, om.content, om.tokens, om.created_at
    FROM ordered_messages om
    WHERE om.cumulative_tokens <= max_tokens
    ORDER BY om.created_at ASC;  -- Return in chronological order
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to sysadmin user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sysadmin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sysadmin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO sysadmin;

-- Example queries for monitoring:
-- 
-- -- View active sessions for all hosts
-- SELECT hostname, session_id, created_at, last_activity
-- FROM conversation_sessions
-- WHERE is_active = TRUE
-- ORDER BY hostname;
--
-- -- View recent messages across all hosts
-- SELECT m.hostname, m.role, LEFT(m.content, 50) as preview, m.created_at
-- FROM messages m
-- ORDER BY m.created_at DESC
-- LIMIT 20;
--
-- -- Count messages per host
-- SELECT hostname, COUNT(*) as message_count
-- FROM messages
-- GROUP BY hostname
-- ORDER BY message_count DESC;
