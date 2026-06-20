# ContextSlim MCP Router Server

## Overview

ContextSlim is an MCP-native tool routing layer that prevents context bloat by dynamically exposing only the most relevant MCP tools to the active agent.

Instead of sending hundreds of tool schemas from dozens of MCP servers into every LLM request, ContextSlim acts as an intelligent MCP gateway that:

* Indexes all available tools
* Semantically searches tool descriptions
* Returns only the most relevant tool subset
* Reduces token consumption
* Improves tool selection accuracy
* Provides future analytics and governance capabilities

---

# Problem

Modern MCP deployments often include:

* GitHub
* Slack
* Notion
* Gmail
* Linear
* Jira
* Databases
* Internal APIs

This can result in:

* Hundreds of available tools
* Large schema payloads
* Increased token costs
* Slower inference
* Wrong tool selection by agents

Most MCP clients currently expose every tool to the model on every session.

ContextSlim solves this by dynamically filtering tools before they reach the agent.

---

# MVP Goals

### Phase 1

Build a FastMCP server that:

1. Loads tool metadata from multiple MCP servers
2. Creates a searchable tool catalog
3. Supports semantic tool discovery
4. Returns only relevant tool groups
5. Tracks routing decisions

No dashboard.

No billing.

No authentication beyond a simple API key.

---

# Architecture

```text
Agent
  │
  ▼
ContextSlim Router MCP
  │
  ├── GitHub MCP
  ├── Slack MCP
  ├── Notion MCP
  ├── Linear MCP
  └── Internal MCPs
```

---

# Tech Stack

## Server

* FastMCP
* Python 3.12+

## Storage

* SQLite

## Vector Search

Option A (MVP)

* sqlite-vec
* Model2Vec

Option B

* SentenceTransformers
* FAISS

---

# Project Structure

```text
contextslim/
│
├── app.py
├── config.py
├── catalog.py
├── embeddings.py
├── router.py
├── registry.py
│
├── database/
│   ├── schema.sql
│   └── contextslim.db
│
├── models/
│   ├── tool.py
│   └── server.py
│
├── services/
│   ├── indexing_service.py
│   ├── search_service.py
│   └── analytics_service.py
│
├── mcp_servers/
│   └── config.json
│
└── README.md
```

---

# Tool Catalog Schema

```sql
CREATE TABLE tools (
    id TEXT PRIMARY KEY,
    server_name TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    description TEXT,
    schema_json TEXT,
    embedding BLOB,
    created_at TIMESTAMP
);
```

---

# MCP Resources

## Resource

```text
resources://tool-catalog
```

Returns all indexed tools.

Example:

```json
[
  {
    "server": "github",
    "tool": "create_issue"
  },
  {
    "server": "slack",
    "tool": "send_message"
  }
]
```

---

# MCP Tools

## search_available_tools

### Description

Search the catalog using semantic similarity.

### Input

```json
{
  "query": "create bug ticket"
}
```

### Output

```json
[
  {
    "server": "github",
    "tool": "create_issue",
    "score": 0.95
  }
]
```

---

## activate_tool_subset

### Description

Return schemas for a selected set of servers or tools.

### Input

```json
{
  "servers": [
    "github",
    "linear"
  ]
}
```

### Output

```json
{
  "active_tools": [
    {
      "tool": "create_issue"
    },
    {
      "tool": "update_issue"
    }
  ]
}
```

---

## explain_routing_decision

### Description

Explain why a tool was selected.

### Input

```json
{
  "query": "open bug ticket"
}
```

### Output

```json
{
  "matched_tool": "github.create_issue",
  "reason": "High similarity to issue creation workflows"
}
```

---

# Tool Ranking Strategy

## Inputs

Tool ranking score should combine:

### Semantic Similarity

Weight:

```text
60%
```

### Historical Usage

Weight:

```text
20%
```

### Tool Success Rate

Weight:

```text
20%
```

---

# Ranking Formula

```text
score =
0.6 * semantic_similarity +
0.2 * usage_frequency +
0.2 * success_rate
```

---

# Indexing Pipeline

## Startup

1. Read MCP config
2. Discover connected servers
3. Fetch tool schemas
4. Generate embeddings
5. Store catalog

---

## Refresh

Run every:

```text
5 minutes
```

Or manually:

```bash
contextslim refresh
```

---

# Analytics Events

Track:

```json
{
  "timestamp": "...",
  "query": "...",
  "tool_candidates": 142,
  "tools_returned": 5,
  "tool_selected": "github.create_issue"
}
```

---

# Future Features

## Token Savings Dashboard

Metrics:

* Total requests
* Tool schemas removed
* Estimated tokens saved
* Estimated API cost savings

---

## RBAC

Restrict tools by:

* User
* Team
* Organization

Example:

```json
{
  "user": "intern",
  "blocked_tools": [
    "production_database"
  ]
}
```

---

## Enterprise Audit Logs

Track:

* Who used what tool
* Which MCP server was accessed
* Timestamp
* Success/failure

---

# FastMCP MVP API

Required Tools:

* search_available_tools
* activate_tool_subset
* explain_routing_decision

Required Resources:

* resources://tool-catalog

Required Services:

* catalog indexing
* semantic search
* analytics logging

---

# Success Metrics

## Technical

* Tool retrieval < 100ms
* Support 1000+ tools
* SQLite only
* Local-first deployment

## Business

* 50 beta users
* 10 paying customers
* 70%+ average tool reduction
* Measurable token savings

---

# Vision

ContextSlim becomes the routing and observability layer for MCP infrastructure.

Today:

* Tool filtering

Tomorrow:

* MCP governance
* Access control
* Analytics
* Compliance
* Agent observability

The long-term goal is to become the control plane for large-scale MCP deployments.
