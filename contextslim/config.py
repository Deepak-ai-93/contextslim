import os
from pathlib import Path


class Config:
    def __init__(self):
        base = Path(__file__).parent
        self.db_path = os.getenv(
            "CONTEXTSLIM_DB_PATH",
            str(base / "database" / "contextslim.db"),
        )
        self.mcp_servers_path = os.getenv(
            "CONTEXTSLIM_SERVERS_PATH",
            str(base / "mcp_servers" / "config.json"),
        )
        self.embedding_model = os.getenv(
            "CONTEXTSLIM_EMBEDDING_MODEL",
            "all-MiniLM-L6-v2",
        )
        self.api_key = os.getenv("CONTEXTSLIM_API_KEY", "")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.refresh_interval = int(
            os.getenv("CONTEXTSLIM_REFRESH_INTERVAL", "300")
        )
        self.top_k = int(os.getenv("CONTEXTSLIM_TOP_K", "20"))
