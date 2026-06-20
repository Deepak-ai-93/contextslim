import logging
import traceback
from typing import Optional

from contextslim.catalog import ToolCatalog
from contextslim.embeddings import EmbeddingService
from contextslim.registry import MCPServerRegistry
from contextslim.models.server import MCPServerConfig

logger = logging.getLogger(__name__)

DEMO_TOOLS = [
    {
        "server": "github",
        "tools": [
            {"name": "create_issue", "description": "Create a new GitHub issue in a repository"},
            {"name": "search_issues", "description": "Search and list GitHub issues using query filters"},
            {"name": "list_pull_requests", "description": "List pull requests for a repository"},
            {"name": "create_pull_request", "description": "Create a new pull request"},
            {"name": "get_repository", "description": "Get repository details and metadata"},
            {"name": "list_commits", "description": "List commits in a repository branch"},
            {"name": "create_review", "description": "Create a pull request review"},
            {"name": "merge_pull_request", "description": "Merge a pull request"},
        ],
    },
    {
        "server": "slack",
        "tools": [
            {"name": "send_message", "description": "Send a message to a Slack channel"},
            {"name": "create_channel", "description": "Create a new Slack channel"},
            {"name": "list_channels", "description": "List all channels in the workspace"},
            {"name": "get_message_history", "description": "Get message history for a channel"},
            {"name": "add_reaction", "description": "Add a reaction emoji to a message"},
            {"name": "upload_file", "description": "Upload a file to a Slack channel"},
        ],
    },
    {
        "server": "linear",
        "tools": [
            {"name": "create_issue", "description": "Create a new Linear issue"},
            {"name": "update_issue", "description": "Update an existing Linear issue"},
            {"name": "search_issues", "description": "Search Linear issues by query"},
            {"name": "get_issue", "description": "Get details of a specific Linear issue"},
            {"name": "list_teams", "description": "List all teams in Linear"},
            {"name": "create_project", "description": "Create a new Linear project"},
        ],
    },
    {
        "server": "notion",
        "tools": [
            {"name": "query_database", "description": "Query a Notion database for pages"},
            {"name": "create_page", "description": "Create a new page in Notion"},
            {"name": "update_page", "description": "Update an existing Notion page"},
            {"name": "get_page", "description": "Get the contents of a Notion page"},
            {"name": "search", "description": "Search across all Notion content"},
        ],
    },
    {
        "server": "filesystem",
        "tools": [
            {"name": "read_file", "description": "Read the contents of a file"},
            {"name": "write_file", "description": "Write content to a file"},
            {"name": "list_directory", "description": "List files and directories"},
            {"name": "search_files", "description": "Search for files matching a pattern"},
        ],
    },
]


class IndexingService:
    def __init__(
        self,
        catalog: ToolCatalog,
        embeddings: EmbeddingService,
        registry: MCPServerRegistry,
    ):
        self.catalog = catalog
        self.embeddings = embeddings
        self.registry = registry

    async def index_all(self):
        servers = self.registry.get_servers()
        indexed_count = 0
        failed_servers = []

        if not servers:
            logger.info(
                "No MCP servers configured, indexing demo tools"
            )
            self._index_demo_tools()
            return

        for server in servers:
            try:
                tools = await self._fetch_tools_from_server(server)
                for tool in tools:
                    self._index_tool(server.name, tool)
                    indexed_count += 1
                logger.info(
                    "Indexed %d tools from %s", len(tools), server.name
                )
            except Exception:
                logger.error(
                    "Failed to index server %s: %s",
                    server.name,
                    traceback.format_exc(),
                )
                failed_servers.append(server.name)

        logger.info(
            "Indexing complete: %d tools indexed, %d servers failed",
            indexed_count,
            len(failed_servers),
        )

    def _index_demo_tools(self):
        self.catalog.clear_all()
        texts = []
        tool_index = []
        for server_data in DEMO_TOOLS:
            server_name = server_data["server"]
            for tool in server_data["tools"]:
                texts.append(f"{tool['name']}: {tool['description']}")
                tool_index.append((server_name, tool))
        embeddings = self.embeddings.embed_batch(texts)
        for (server_name, tool), embedding in zip(tool_index, embeddings):
            self._index_tool(server_name, {
                "name": tool["name"],
                "description": tool["description"],
                "schema_json": '{"type":"object","properties":{}}',
            }, embedding=embedding)
        count = self.catalog.get_tool_count()
        logger.info("Indexed %d demo tools", count)

    def _index_tool(
        self,
        server_name: str,
        tool_data: dict,
        embedding: Optional[list[float]] = None,
    ):
        tool_name = tool_data.get("name", "unknown")
        description = tool_data.get("description") or ""
        schema_json = tool_data.get("schema_json") or "{}"
        tool_id = f"{server_name}.{tool_name}"
        if embedding is None:
            text_for_embedding = f"{tool_name}: {description}"
            embedding = self.embeddings.embed(text_for_embedding)
        self.catalog.upsert_tool(
            tool_id=tool_id,
            server_name=server_name,
            tool_name=tool_name,
            description=description,
            schema_json=schema_json,
            embedding=embedding,
        )

    async def _fetch_tools_from_server(
        self, server: MCPServerConfig
    ) -> list[dict]:
        if server.transport == "stdio" and server.command:
            return await self._connect_stdio(server)
        elif server.transport == "sse" and server.url:
            return await self._connect_sse(server)
        logger.warning(
            "Unknown transport %s for server %s",
            server.transport,
            server.name,
        )
        return []

    async def _connect_stdio(
        self, server: MCPServerConfig
    ) -> list[dict]:
        try:
            from mcp import ClientSession
            from mcp.client.stdio import (
                stdio_client,
                StdioServerParameters,
            )

            params = StdioServerParameters(
                command=server.command,
                args=server.args or [],
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [
                        {
                            "name": t.name,
                            "description": t.description or "",
                            "schema_json": (
                                t.inputSchema.model_dump_json()
                                if hasattr(t.inputSchema, "model_dump_json")
                                else str(t.inputSchema)
                            ),
                        }
                        for t in result.tools
                    ]
        except ImportError:
            logger.warning(
                "mcp client not available, cannot connect to stdio server %s",
                server.name,
            )
            return []

    async def _connect_sse(
        self, server: MCPServerConfig
    ) -> list[dict]:
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            async with sse_client(
                url=server.url,
                headers=(
                    {"Authorization": f"Bearer {server.api_key}"}
                    if server.api_key
                    else {}
                ),
            ) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [
                        {
                            "name": t.name,
                            "description": t.description or "",
                            "schema_json": (
                                t.inputSchema.model_dump_json()
                                if hasattr(t.inputSchema, "model_dump_json")
                                else str(t.inputSchema)
                            ),
                        }
                        for t in result.tools
                    ]
        except ImportError:
            logger.warning(
                "mcp client not available, cannot connect to SSE server %s",
                server.name,
            )
            return []
