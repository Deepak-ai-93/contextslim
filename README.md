# ContextSlim MCP Router Server

**ContextSlim** is an MCP-native tool routing layer that prevents context bloat by dynamically exposing only the most relevant MCP tools to the active agent.

Instead of sending hundreds of tool schemas from dozens of MCP servers into every LLM request, ContextSlim acts as an intelligent MCP gateway that indexes all available tools, semantically searches descriptions, and returns only the most relevant subset — reducing token consumption and improving tool selection accuracy.

---

## Architecture

```text
Agent (Claude Desktop, Cursor, etc.)
  │
  ▼
ContextSlim Router (this server)
  │
  ├── search_available_tools   ← semantic search
  ├── activate_tool_subset     ← get schemas for selected servers
  └── explain_routing_decision ← understand why a tool matched
  │
  ├──▶ GitHub MCP Server
  ├──▶ Slack MCP Server
  ├──▶ Notion MCP Server
  ├──▶ Linear MCP Server
  └──▶ Internal MCP Servers
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (SSE transport, default port 8000)
python -m contextslim.app
```

By default, ContextSlim starts with **29 demo tools** across GitHub, Slack, Linear, Notion, and Filesystem — so you can test immediately without configuring any downstream MCP servers.

---

## How to Use as an MCP Server

### MCP Clients (Claude Desktop, Cursor, Windsurf, etc.)

Add ContextSlim as an MCP server in your client's MCP config:

**Local (stdio) mode:**
```json
{
  "mcpServers": {
    "contextslim": {
      "command": "python",
      "args": ["-m", "contextslim.app"]
    }
  }
}
```

**Remote (SSE) mode — Render deployment:**
```json
{
  "mcpServers": {
    "contextslim": {
      "url": "https://your-app.onrender.com/sse"
    }
  }
}
```

**Remote (Streamable HTTP) mode — Vercel deployment:**
```json
{
  "mcpServers": {
    "contextslim": {
      "url": "https://your-app.vercel.app/mcp"
    }
  }
}
```

### Usage Pattern

Once connected, your agent can call ContextSlim's tools to discover and route to the right downstream tools:

1. **Search** — `search_available_tools(query: "create a bug ticket")` → returns ranked tools
2. **Activate** — `activate_tool_subset(servers: ["github", "linear"])` → returns full schemas
3. **Explain** — `explain_routing_decision(query: "send slack notification")` → shows scoring breakdown

---

## MCP Tools

### `search_available_tools`

Semantically search the tool catalog. Returns ranked results with relevance scores.

**Input:**
```json
{
  "query": "create bug ticket"
}
```

**Output:**
```json
[
  {
    "server": "linear",
    "tool": "create_issue",
    "score": 0.3455,
    "description": "Create a new Linear issue"
  },
  {
    "server": "github",
    "tool": "create_issue",
    "score": 0.3043,
    "description": "Create a new GitHub issue in a repository"
  }
]
```

### `activate_tool_subset`

Get full schemas for a selected set of servers. Use this after searching to load the actual tool definitions.

**Input:**
```json
{
  "servers": ["github", "slack"]
}
```

**Output:**
```json
{
  "active_tools": [
    {
      "tool": "create_issue",
      "server": "github",
      "description": "Create a new GitHub issue",
      "schema": { ... }
    }
  ],
  "server_count": 2,
  "tool_count": 14
}
```

### `explain_routing_decision`

Understand why a particular tool was selected for a query.

**Input:**
```json
{
  "query": "open bug ticket"
}
```

**Output:**
```json
{
  "matched_tool": "linear.create_issue",
  "reason": "Highest combined score (0.2318) - semantic match for 'open bug ticket' with tool 'create_issue'",
  "score": 0.2318,
  "semantic_similarity": 0.2318,
  "usage_frequency": 0,
  "success_rate": 0
}
```

### `refresh_catalog`

Re-index all downstream MCP servers and update embeddings.

**Input:** None

**Output:**
```json
{
  "status": "ok",
  "tools_indexed": 29
}
```

### `get_stats`

Get catalog statistics and recent search history.

**Input:** None

**Output:**
```json
{
  "total_tools": 29,
  "recent_searches": [ ... ]
}
```

---

## MCP Resources

### `resources://tool-catalog`

Returns the full list of all indexed tools.

```json
[
  {
    "id": "github.create_issue",
    "server_name": "github",
    "tool_name": "create_issue",
    "description": "Create a new GitHub issue in a repository"
  }
]
```

---

## Tool Ranking Formula

Results are scored using a weighted combination:

```text
score = 0.6 × semantic_similarity
      + 0.2 × usage_frequency
      + 0.2 × success_rate
```

| Component | Weight | Source |
|-----------|--------|--------|
| Semantic similarity | 60% | Sentence-transformer or OpenAI embedding cosine similarity |
| Usage frequency | 20% | Historical tool invocation count (normalized) |
| Success rate | 20% | Ratio of successful invocations to total |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXTSLIM_EMBEDDING_PROVIDER` | `local` | `local` (sentence-transformers) or `openai` (API) |
| `CONTEXTSLIM_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model name |
| `OPENAI_API_KEY` | — | Required when provider is `openai` |
| `CONTEXTSLIM_DB_PATH` | `contextslim/database/contextslim.db` | SQLite database path |
| `CONTEXTSLIM_SERVERS_PATH` | `contextslim/mcp_servers/config.json` | Downstream MCP server config |
| `CONTEXTSLIM_TOP_K` | `20` | Max tools returned per search |
| `CONTEXTSLIM_REFRESH_INTERVAL` | `300` | Index refresh interval in seconds |
| `CONTEXTSLIM_API_KEY` | — | Optional API key for incoming requests |
| `PORT` | `8000` | HTTP server port |

---

## Connecting Downstream MCP Servers

Edit `contextslim/mcp_servers/config.json` to connect real downstream MCP servers:

```json
[
  {
    "name": "github",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"]
  },
  {
    "name": "slack",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"]
  },
  {
    "name": "internal-api",
    "transport": "sse",
    "url": "https://internal.example.com/mcp",
    "api_key": "sk-..."
  }
]
```

Supported transports:
- `stdio` — spawn a local subprocess (command + args)
- `sse` — connect to a remote SSE endpoint (url + optional api_key)

When no servers are configured, ContextSlim indexes **29 demo tools** automatically.

---

## Deployment

### Render (recommended)

1. Push this repo to GitHub
2. Create a **Web Service** on Render
3. Connect your GitHub repo
4. Auto-detects `render.yaml`, or configure:
   - **Build Command:** `pip install -r requirements-render.txt && python -c "from contextslim.embeddings import EmbeddingService; EmbeddingService.create('local', 'all-MiniLM-L6-v2').embed('warmup')"`
   - **Start Command:** `python -m contextslim.app`
5. Uses local sentence-transformers embeddings (cached after first deploy)

### Vercel

1. Push this repo to GitHub
2. Import repo in Vercel dashboard
3. Auto-detects `vercel.json`
4. Set environment variables in Vercel dashboard:
   - `OPENAI_API_KEY` — required (uses OpenAI Embeddings API, not local ML)
5. Uses Streamable HTTP transport (`/mcp` endpoint)

> **Note:** Vercel uses OpenAI embeddings via API (`requirements.txt` is lightweight). The Hobby plan works since bundle is under 50MB.

---

## Indexing Pipeline

On startup (and every `CONTEXTSLIM_REFRESH_INTERVAL` seconds), ContextSlim:

1. Reads `mcp_servers/config.json`
2. Connects to each downstream MCP server via stdio or SSE
3. Lists all available tools using the MCP protocol
4. Generates embeddings for each tool's name + description
5. Stores tools + embeddings in SQLite
6. Falls back to demo tools if no servers are configured

Manually refresh: `refresh_catalog` tool.

---

## Development

```bash
# Install with local ML deps
pip install -r requirements-render.txt

# Run locally
python -m contextslim.app

# Test search
python -c "
import asyncio
from contextslim.app import catalog, indexing_service, search_service
asyncio.run(indexing_service.index_all())
print(search_service.search('create issue'))
"
```

---

## Project Structure

```text
contextslim/
├── app.py                  # FastMCP server (tools, resources, startup)
├── config.py               # Environment-based configuration
├── catalog.py              # SQLite-backed tool catalog
├── embeddings.py           # Embedding providers (local + OpenAI)
├── registry.py             # Downstream MCP server registry
├── database/
│   └── schema.sql          # SQLite schema
├── models/
│   ├── tool.py             # ToolMetadata, ToolSearchResult
│   └── server.py           # MCPServerConfig
├── services/
│   ├── indexing_service.py # Indexing pipeline + demo tools
│   ├── search_service.py   # Semantic search + ranking
│   └── analytics_service.py# Usage tracking + analytics
├── mcp_servers/
│   └── config.json         # Downstream server configurations
api/
└── index.py                # Vercel serverless entry point
```

---

## License

MIT
