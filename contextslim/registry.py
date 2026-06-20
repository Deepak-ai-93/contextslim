import json
import logging
from pathlib import Path
from typing import Optional

from contextslim.models.server import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPServerRegistry:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.servers: list[MCPServerConfig] = []
        self._load_config()

    def _load_config(self):
        path = Path(self.config_path)
        if not path.exists():
            logger.warning(
                "MCP servers config not found at %s, using empty registry",
                self.config_path,
            )
            self.servers = []
            return
        with open(path) as f:
            data = json.load(f)
        self.servers = [MCPServerConfig(**s) for s in data]
        logger.info(
            "Loaded %d MCP server configurations", len(self.servers)
        )

    def get_servers(self) -> list[MCPServerConfig]:
        return self.servers

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        for s in self.servers:
            if s.name == name:
                return s
        return None

    def add_server(self, config: MCPServerConfig):
        self.servers = [s for s in self.servers if s.name != config.name]
        self.servers.append(config)
        self._save_config()

    def remove_server(self, name: str):
        self.servers = [s for s in self.servers if s.name != name]
        self._save_config()

    def _save_config(self):
        path = Path(self.config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [s.model_dump() for s in self.servers]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
