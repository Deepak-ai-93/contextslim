import asyncio
import json
import logging

from fastmcp import FastMCP

from contextslim.config import Config
from contextslim.catalog import ToolCatalog
from contextslim.embeddings import EmbeddingService
from contextslim.registry import MCPServerRegistry
from contextslim.services.indexing_service import IndexingService
from contextslim.services.search_service import SearchService
from contextslim.services.analytics_service import AnalyticsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("contextslim")

config = Config()

catalog = ToolCatalog(config.db_path)
embeddings = EmbeddingService(config.embedding_model)
registry = MCPServerRegistry(config.mcp_servers_path)
analytics = AnalyticsService(config.db_path)

indexing_service = IndexingService(catalog, embeddings, registry)
search_service = SearchService(catalog, embeddings, analytics, top_k=config.top_k)

mcp = FastMCP("ContextSlim Router")


@mcp.resource("resources://tool-catalog")
def get_tool_catalog() -> str:
    tools = search_service.get_all_tools()
    return json.dumps(tools, indent=2)


@mcp.tool()
def search_available_tools(query: str) -> str:
    results = search_service.search(query)
    return json.dumps(results, indent=2)


@mcp.tool()
def activate_tool_subset(servers: list[str]) -> str:
    result = search_service.activate_subset(servers)
    return json.dumps(result, indent=2)


@mcp.tool()
def explain_routing_decision(query: str) -> str:
    result = search_service.explain_decision(query)
    return json.dumps(result, indent=2)


@mcp.tool()
def refresh_catalog() -> str:
    asyncio.run(indexing_service.index_all())
    count = catalog.get_tool_count()
    return json.dumps({"status": "ok", "tools_indexed": count})


@mcp.tool()
def get_stats() -> str:
    tool_count = catalog.get_tool_count()
    recent = analytics.get_recent_searches(5)
    return json.dumps({
        "total_tools": tool_count,
        "recent_searches": recent,
    }, indent=2, default=str)


async def main():
    logger.info("Indexing tools...")
    await indexing_service.index_all()
    logger.info("Starting ContextSlim Router on %s:%s", config.host, config.port)
    await mcp.run_http_async(
        transport="sse",
        host=config.host,
        port=config.port,
    )


if __name__ == "__main__":
    asyncio.run(main())
