import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log_search(
        self,
        query: str,
        tool_candidates: int,
        tools_returned: int,
        tool_selected: Optional[str] = None,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO analytics (query, tool_candidates, tools_returned, tool_selected)
            VALUES (?, ?, ?, ?)
            """,
            (query, tool_candidates, tools_returned, tool_selected),
        )
        self._log_audit(conn, user_id, user_email, session_id, "search", {
            "query": query, "candidates": tool_candidates, "returned": tools_returned
        })
        conn.commit()
        conn.close()

    def log_tool_usage(
        self,
        tool_id: str,
        success: bool = True,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO usage_stats (tool_id, usage_count, success_count, last_used)
            VALUES (?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tool_id) DO UPDATE SET
                usage_count = usage_count + 1,
                success_count = success_count + ?,
                last_used = CURRENT_TIMESTAMP
            """,
            (tool_id, 1 if success else 0, 1 if success else 0),
        )
        self._log_audit(conn, user_id, user_email, session_id, "tool_usage", {
            "tool_id": tool_id, "success": success
        })
        conn.commit()
        conn.close()

    def _log_audit(
        self,
        conn: sqlite3.Connection,
        user_id: Optional[str],
        user_email: Optional[str],
        session_id: Optional[str],
        action: str,
        details: dict,
    ):
        conn.execute(
            """
            INSERT INTO audit_log (user_id, user_email, session_id, action, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, user_email, session_id, action, str(details)),
        )

    def get_usage_frequency(self, tool_id: str) -> float:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT usage_count FROM usage_stats WHERE tool_id = ?",
            (tool_id,),
        ).fetchone()
        conn.close()
        return row["usage_count"] if row else 0.0

    def get_success_rate(self, tool_id: str) -> float:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT usage_count, success_count FROM usage_stats WHERE tool_id = ?",
            (tool_id,),
        ).fetchone()
        conn.close()
        if row and row["usage_count"] > 0:
            return row["success_count"] / row["usage_count"]
        return 0.0

    def get_max_usage(self) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(usage_count) FROM usage_stats"
        ).fetchone()
        conn.close()
        return row[0] or 1

    def get_recent_searches(self, limit: int = 10) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM analytics ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_audit_log(
        self,
        limit: int = 20,
        user_email: Optional[str] = None,
        action: Optional[str] = None,
    ) -> list[dict]:
        conn = self._get_conn()
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if user_email:
            query += " AND user_email = ?"
            params.append(user_email)
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_usage(
        self, user_email: str
    ) -> dict:
        conn = self._get_conn()
        searches = conn.execute(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE user_email = ? AND action = 'search'",
            (user_email,),
        ).fetchone()
        tool_uses = conn.execute(
            "SELECT COUNT(*) as cnt FROM audit_log WHERE user_email = ? AND action = 'tool_usage'",
            (user_email,),
        ).fetchone()
        last_active = conn.execute(
            "SELECT MAX(timestamp) as ts FROM audit_log WHERE user_email = ?",
            (user_email,),
        ).fetchone()
        conn.close()
        return {
            "user_email": user_email,
            "total_searches": searches["cnt"] if searches else 0,
            "total_tool_uses": tool_uses["cnt"] if tool_uses else 0,
            "last_active": last_active["ts"] if last_active and last_active["ts"] else None,
        }
