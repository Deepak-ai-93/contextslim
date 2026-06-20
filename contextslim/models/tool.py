from pydantic import BaseModel
from typing import Optional


class ToolMetadata(BaseModel):
    id: str
    server_name: str
    tool_name: str
    description: Optional[str] = None
    input_schema: Optional[str] = None
    embedding: Optional[list[float]] = None


class ToolSearchResult(BaseModel):
    server: str
    tool: str
    score: float
    description: Optional[str] = None
