-- ============================================================
-- Migration 001 — Create conversations table
-- Sprint 1 infrastructure prep for Sprint 6 multi-turn support
-- ============================================================
-- Run this on Supabase SQL Editor or via psql.

CREATE TABLE IF NOT EXISTS conversations (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID            NOT NULL,
    role            VARCHAR(20)     NOT NULL
                        CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT            NOT NULL,
    metadata        JSONB           DEFAULT '{}',
    created_at      TIMESTAMPTZ     DEFAULT now()
);

-- Fast lookups by session (all messages in a conversation)
CREATE INDEX IF NOT EXISTS idx_conversations_session
    ON conversations (session_id);

-- Chronological ordering within a session
CREATE INDEX IF NOT EXISTS idx_conversations_created
    ON conversations (session_id, created_at);

-- Grant SELECT to the read-only user used by M1 agent
GRANT SELECT ON conversations TO erp_readonly;

COMMENT ON TABLE conversations IS
    'Multi-turn conversation history. Created in Sprint 1, used from Sprint 6.';
