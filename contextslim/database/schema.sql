CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY,
    server_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    description TEXT,
    schema_json TEXT,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query TEXT,
    tool_candidates INTEGER DEFAULT 0,
    tools_returned INTEGER DEFAULT 0,
    tool_selected TEXT,
    success BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS usage_stats (
    tool_id TEXT PRIMARY KEY,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_used TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    user_email TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    tools_used INTEGER DEFAULT 0,
    searches_made INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    user_email TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    success BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_tools_server ON tools(server_name);
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(tool_name);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_email);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
