import asyncio
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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
        await ensure_indexed()
        return await call_next(request)


app = contextslim_app.mcp.http_app(transport="streamable-http", stateless_http=True)
app.add_middleware(IndexingMiddleware)
