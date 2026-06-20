import asyncio
import json
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

os.environ["CONTEXTSLIM_EMBEDDING_PROVIDER"] = "openai"
os.environ["CONTEXTSLIM_DB_PATH"] = "/tmp/contextslim.db"

from contextslim import app as contextslim_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel")

_indexed = False


async def ensure_indexed():
    global _indexed
    if not _indexed:
        logger.info("Indexing tools on cold start...")
        await contextslim_app.indexing_service.index_all()
        _indexed = True
        logger.info("Indexing complete")


class IndexingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in ("/", "/health"):
            await ensure_indexed()
        return await call_next(request)


async def root(request: Request):
    return JSONResponse({
        "service": "ContextSlim Router",
        "status": "ok",
        "mcp_endpoint": "/mcp",
        "docs": "https://github.com/Deepak-ai-93/contextslim",
    })


app = contextslim_app.mcp.http_app(transport="streamable-http", stateless_http=True)
app.add_route("/", root)
app.add_route("/health", root)
app.add_middleware(IndexingMiddleware)
