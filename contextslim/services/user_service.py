import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db_path: str, admin_api_key: str = ""):
        self.db_path = db_path
        self.admin_api_key = admin_api_key

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def identify_user(self, email: str, name: str) -> dict:
        conn = self._get_conn()
        user_id = str(uuid.uuid4())
        try:
            conn.execute(
                """
                INSERT INTO users (id, email, name, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(email) DO UPDATE SET
                    name = excluded.name,
                    last_active = CURRENT_TIMESTAMP
                """,
                (user_id, email, name),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, email, name, role FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            conn.close()
            return dict(row) if row else {"email": email, "name": name, "role": "user"}
        except Exception as e:
            conn.close()
            return {"email": email, "name": name, "error": str(e)}

    def create_session(self, user_email: str) -> str:
        conn = self._get_conn()
        session_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO sessions (id, user_email)
            VALUES (?, ?)
            """,
            (session_id, user_email),
        )
        conn.commit()
        conn.close()
        return session_id

    def list_users(self, admin_key: str) -> list[dict]:
        if self.admin_api_key and admin_key != self.admin_api_key:
            return []
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, email, name, role, created_at, last_active FROM users ORDER BY last_active DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_by_email(self, email: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, email, name, role, created_at, last_active FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def verify_admin(self, admin_key: str) -> bool:
        if not self.admin_api_key:
            return True
        return admin_key == self.admin_api_key
