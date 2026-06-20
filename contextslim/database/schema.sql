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

CREATE INDEX IF NOT EXISTS idx_tools_server ON tools(server_name);
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(tool_name);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp);
