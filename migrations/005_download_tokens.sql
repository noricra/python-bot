-- Migration 005: Download Tokens Table
-- Date: 2025-12-31
-- Purpose: Persistent token storage for download links (replace in-memory dict)

CREATE TABLE IF NOT EXISTS download_tokens (
    token UUID PRIMARY KEY,
    user_id BIGINT NOT NULL,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT
);

-- Index for cleanup expired tokens
CREATE INDEX IF NOT EXISTS idx_download_tokens_expires_at ON download_tokens(expires_at);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_download_tokens_user_id ON download_tokens(user_id);

-- Index for rate limiting queries
CREATE INDEX IF NOT EXISTS idx_download_tokens_user_created ON download_tokens(user_id, created_at);

-- Table for rate limiting
CREATE TABLE IF NOT EXISTS download_rate_limits (
    user_id BIGINT PRIMARY KEY,
    tokens_generated_count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_token_at TIMESTAMP
);

-- Index for rate limit cleanup
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON download_rate_limits(window_start);

-- Comments
COMMENT ON TABLE download_tokens IS 'Persistent storage for one-time download tokens';
COMMENT ON COLUMN download_tokens.token IS 'UUID token used in download URL';
COMMENT ON COLUMN download_tokens.used_at IS 'When token was used (one-time use)';
COMMENT ON COLUMN download_tokens.expires_at IS 'Token expiration (5 minutes after creation)';

COMMENT ON TABLE download_rate_limits IS 'Rate limiting for download token generation';
COMMENT ON COLUMN download_rate_limits.window_start IS 'Start of current rate limit window (1 hour)';
