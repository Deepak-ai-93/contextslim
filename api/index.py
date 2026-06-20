import asyncio
import logging
import os

from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

os.environ["CONTEXTSLIM_EMBEDDING_PROVIDER"] = "openai"
os.environ["CONTEXTSLIM_DB_PATH"] = "/tmp/contextslim.db"

from contextslim import app as contextslim_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel")


async def root(request):
    return JSONResponse({
        "service": "ContextSlim Router",
        "status": "ok",
        "mcp_endpoint": "/mcp",
        "docs": "https://github.com/Deepak-ai-93/contextslim",
    })


app = contextslim_app.mcp.http_app(transport="streamable-http")
app.add_route("/", root)
app.add_route("/health", root)
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
