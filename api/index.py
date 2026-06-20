import asyncio
import json
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

os.environ["CONTEXTSLIM_EMBEDDING_PROVIDER"] = "openai"
os.environ["CONTEXTSLIM_DB_PATH"] = "/tmp/contextslim.db"

from contextslim import app as contextslim_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel")


class MCPClientTracker(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            if request.method == "POST" and request.url.path == "/mcp":
                body = await request.body()
                data = json.loads(body)
                if data.get("method") == "initialize":
                    params = data.get("params", {})
                    client_info = params.get("clientInfo", {})
                    name = client_info.get("name", "unknown")
                    version = client_info.get("version", "unknown")
                    protocol = params.get("protocolVersion", "unknown")
                    ip = request.client.host if request.client else "unknown"
                    logger.info("MCP client connected: %s v%s (protocol: %s, ip: %s)", name, version, protocol, ip)
                    contextslim_app.analytics.log_audit(
                        action="mcp_connect",
                        details={
                            "client_name": name,
                            "client_version": version,
                            "protocol_version": protocol,
                            "ip": ip,
                        },
                    )
        except Exception:
            pass
        return await call_next(request)


async def root(request: Request):
    return JSONResponse({
        "service": "ContextSlim Router",
        "status": "ok",
        "mcp_endpoint": "/mcp",
        "docs": "https://github.com/Deepak-ai-93/contextslim",
    })


app = contextslim_app.mcp.http_app(transport="streamable-http")
app.add_route("/", root)
app.add_route("/health", root)
app.add_middleware(MCPClientTracker)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


async def _index_on_start():
    try:
        logger.info("Indexing tools on cold start...")
        await contextslim_app.indexing_service.index_all()
        logger.info("Indexing complete")
    except Exception as e:
        logger.error("Indexing failed: %s", e)


try:
    asyncio.run(_index_on_start())
except RuntimeError:
    pass
