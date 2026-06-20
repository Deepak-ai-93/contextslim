import sqlite3
import json
from pathlib import Path
from typing import Optional

import numpy as np


class ToolCatalog:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).parent / "database" / "schema.sql"
        conn = sqlite3.connect(self.db_path)
        with open(schema_path) as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert_tool(
        self,
        tool_id: str,
        server_name: str,
        tool_name: str,
        description: Optional[str] = None,
        schema_json: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ):
        conn = self._get_conn()
        embedding_blob = (
            np.array(embedding, dtype=np.float32).tobytes()
            if embedding
            else None
        )
        conn.execute(
            """
            INSERT INTO tools (id, server_name, tool_name, description, schema_json, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                description = excluded.description,
                schema_json = excluded.schema_json,
                embedding = excluded.embedding,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                tool_id,
                server_name,
                tool_name,
                description,
                schema_json,
                embedding_blob,
            ),
        )
        conn.commit()
        conn.close()

    def get_all_tools(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, server_name, tool_name, description FROM tools ORDER BY server_name, tool_name"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_tool_count(self) -> int:
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
        conn.close()
        return count

    def get_all_embeddings(self) -> tuple[list[str], np.ndarray]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, embedding FROM tools WHERE embedding IS NOT NULL"
        ).fetchall()
        conn.close()
        ids = []
        embeddings = []
        for r in rows:
            if r["embedding"]:
                ids.append(r["id"])
                embeddings.append(
                    np.frombuffer(r["embedding"], dtype=np.float32)
                )
        if embeddings:
            return ids, np.array(embeddings)
        return [], np.array([])

    def get_tool_by_id(self, tool_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM tools WHERE id = ?", (tool_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_tools_by_server(self, server_name: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM tools WHERE server_name = ?", (server_name,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def clear_all(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM tools")
        conn.commit()
        conn.close()
