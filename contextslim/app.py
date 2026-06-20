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
from contextslim.services.user_service import UserService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("contextslim")

config = Config()

catalog = ToolCatalog(config.db_path)
embeddings = EmbeddingService.create(config.embedding_provider, config.embedding_model)
registry = MCPServerRegistry(config.mcp_servers_path)
analytics = AnalyticsService(config.db_path)
user_service = UserService(config.db_path, config.admin_api_key)

indexing_service = IndexingService(catalog, embeddings, registry)
search_service = SearchService(catalog, embeddings, analytics, top_k=config.top_k)

mcp = FastMCP("ContextSlim Router")


@mcp.resource("resources://tool-catalog")
def get_tool_catalog() -> str:
    tools = search_service.get_all_tools()
    return json.dumps(tools, indent=2)


@mcp.tool()
def search_available_tools(
    query: str,
    user_email: str = "",
) -> str:
    results = search_service.search(query)
    if user_email:
        analytics.log_search(
            query, len(catalog.get_all_embeddings()[0]),
            len(results), user_email=user_email,
        )
    return json.dumps(results, indent=2)


@mcp.tool()
def activate_tool_subset(
    servers: list[str],
    user_email: str = "",
) -> str:
    result = search_service.activate_subset(servers)
    if user_email:
        analytics.log_tool_usage(
            f"activate_subset:{','.join(servers)}",
            user_email=user_email,
        )
    return json.dumps(result, indent=2)


@mcp.tool()
def explain_routing_decision(
    query: str,
    user_email: str = "",
) -> str:
    result = search_service.explain_decision(query)
    if user_email:
        analytics.log_search(
            query, 0, 1,
            tool_selected=result.get("matched_tool"),
            user_email=user_email,
        )
    return json.dumps(result, indent=2)


@mcp.tool()
async def refresh_catalog() -> str:
    await indexing_service.index_all()
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


@mcp.tool()
def identify_user(email: str, name: str) -> str:
    user = user_service.identify_user(email, name)
    return json.dumps(user, indent=2)


@mcp.tool()
def list_users(admin_key: str = "") -> str:
    users = user_service.list_users(admin_key)
    if not users:
        return json.dumps({"error": "Unauthorized or no users found", "users": []}, indent=2)
    return json.dumps({"users": users}, indent=2, default=str)


@mcp.tool()
def get_user_usage_report(
    email: str,
    admin_key: str = "",
) -> str:
    if not user_service.verify_admin(admin_key):
        return json.dumps({"error": "Unauthorized — provide valid admin_key"})
    usage = analytics.get_user_usage(email)
    user = user_service.get_user_by_email(email)
    if user:
        usage["name"] = user["name"]
        usage["role"] = user["role"]
    return json.dumps(usage, indent=2, default=str)


@mcp.tool()
def get_audit_log(
    limit: int = 20,
    user_email: str = "",
    action: str = "",
    admin_key: str = "",
) -> str:
    if not user_service.verify_admin(admin_key):
        return json.dumps({"error": "Unauthorized — provide valid admin_key"})
    logs = analytics.get_audit_log(
        limit=limit,
        user_email=user_email if user_email else None,
        action=action if action else None,
    )
    return json.dumps({"audit_log": logs}, indent=2, default=str)


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
