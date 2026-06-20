# ContextSlim MCP Router Server

ContextSlim is an MCP-native tool routing layer that prevents context bloat by dynamically exposing only the most relevant MCP tools to the active agent.

## Quick Start

```bash
pip install -r requirements.txt
python -m contextslim.app
```

## Deployment

### Render

1. Push this repo to GitHub
2. In Render, create a new Web Service
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` or use:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m contextslim.app`

### Vercel

1. Push this repo to GitHub
2. In Vercel, import the repo
3. Vercel will auto-detect `vercel.json`
4. Requires **Pro plan** (Hobby plan has 50MB function limit; Python deps exceed this)
5. Uses Streamable HTTP transport (no persistent SSE connections)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXTSLIM_DB_PATH` | `contextslim/database/contextslim.db` | SQLite database path |
| `CONTEXTSLIM_SERVERS_PATH` | `contextslim/mcp_servers/config.json` | MCP server config path |
| `CONTEXTSLIM_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CONTEXTSLIM_API_KEY` | `` | Optional API key |
| `CONTEXTSLIM_TOP_K` | `20` | Max tools to return per search |
| `CONTEXTSLIM_REFRESH_INTERVAL` | `300` | Index refresh interval in seconds |
| `PORT` | `8000` | HTTP server port |

## MCP Tools

- `search_available_tools` - Semantic search across indexed tools
- `activate_tool_subset` - Get schemas for specific servers
- `explain_routing_decision` - Explain why a tool was selected
- `refresh_catalog` - Re-index all MCP servers
- `get_stats` - Get catalog and analytics stats

## MCP Resources

- `resources://tool-catalog` - List all indexed tools
