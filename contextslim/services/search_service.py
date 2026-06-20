import json
import logging
from typing import Optional

import numpy as np

from contextslim.catalog import ToolCatalog
from contextslim.embeddings import EmbeddingService
from contextslim.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        catalog: ToolCatalog,
        embeddings: EmbeddingService,
        analytics: AnalyticsService,
        top_k: int = 20,
    ):
        self.catalog = catalog
        self.embeddings = embeddings
        self.analytics = analytics
        self.top_k = top_k

    def get_all_tools(self) -> list[dict]:
        return self.catalog.get_all_tools()

    def search(self, query: str) -> list[dict]:
        query_embedding = self.embeddings.embed(query)
        tool_ids, tool_embeddings = self.catalog.get_all_embeddings()

        if len(tool_ids) == 0:
            logger.warning("No indexed tools to search")
            self.analytics.log_search(query, 0, 0)
            return []

        scores = np.dot(tool_embeddings, np.array(query_embedding))

        ranked_indices = np.argsort(scores)[::-1]
        top_k = min(self.top_k, len(ranked_indices))

        results = []
        for i in ranked_indices[:top_k]:
            tool_id = tool_ids[i]
            semantic_score = float(scores[i])
            usage_freq = self.analytics.get_usage_frequency(tool_id)
            success_rate = self.analytics.get_success_rate(tool_id)
            max_usage = max(self.analytics.get_max_usage(), 1)

            normalized_usage = min(usage_freq / max_usage, 1.0)
            combined_score = (
                0.6 * semantic_score
                + 0.2 * normalized_usage
                + 0.2 * success_rate
            )

            tool_data = self.catalog.get_tool_by_id(tool_id)
            if tool_data:
                results.append(
                    {
                        "server": tool_data["server_name"],
                        "tool": tool_data["tool_name"],
                        "score": round(combined_score, 4),
                        "description": tool_data.get("description", ""),
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)

        self.analytics.log_search(query, len(tool_ids), len(results))
        return results

    def activate_subset(self, servers: list[str]) -> dict:
        all_tools = []
        for server in servers:
            tools = self.catalog.get_tools_by_server(server)
            for t in tools:
                all_tools.append(
                    {
                        "tool": t["tool_name"],
                        "server": t["server_name"],
                        "description": t.get("description", ""),
                        "schema": (
                            json.loads(t["schema_json"])
                            if t.get("schema_json")
                            else {}
                        ),
                    }
                )
        return {"active_tools": all_tools, "server_count": len(servers), "tool_count": len(all_tools)}

    def explain_decision(self, query: str) -> dict:
        query_lower = query.lower()
        results = self.search(query)
        if not results:
            return {
                "matched_tool": None,
                "reason": f"No tools found matching query: {query}",
                "semantic_similarity": 0,
                "usage_frequency": 0,
                "success_rate": 0,
            }

        best = results[0]
        tool_id = f"{best['server']}.{best['tool']}"
        usage_freq = self.analytics.get_usage_frequency(tool_id)
        success_rate = self.analytics.get_success_rate(tool_id)

        return {
            "matched_tool": f"{best['server']}.{best['tool']}",
            "reason": f"Highest combined score ({best['score']}) - semantic match for '{query}' with tool '{best['tool']}'",
            "score": best["score"],
            "semantic_similarity": best["score"],
            "usage_frequency": usage_freq,
            "success_rate": success_rate,
        }
