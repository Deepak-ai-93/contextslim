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
    ):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO analytics (query, tool_candidates, tools_returned, tool_selected)
            VALUES (?, ?, ?, ?)
            """,
            (query, tool_candidates, tools_returned, tool_selected),
        )
        conn.commit()
        conn.close()

    def log_tool_usage(self, tool_id: str, success: bool = True):
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
        conn.commit()
        conn.close()

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
