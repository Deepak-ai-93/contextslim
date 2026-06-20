from pydantic import BaseModel
from typing import Optional


class MCPServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: Optional[str] = None
    args: Optional[list[str]] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
