from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: str
    email: str
    name: str
    role: str = "user"
    created_at: Optional[str] = None
    last_active: Optional[str] = None


class AuditEntry(BaseModel):
    id: int
    timestamp: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    success: bool = True
