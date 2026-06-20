import logging
import os
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        return float(np.dot(np.array(a), np.array(b)))

    @staticmethod
    def create(provider: str = "local", model_name: str = "all-MiniLM-L6-v2") -> "EmbeddingService":
        if provider == "openai":
            return OpenAIEmbedding()
        return LocalEmbedding(model_name)


class LocalEmbedding(EmbeddingService):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            logger.info("Loading local embedding model: %s", self.model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


class OpenAIEmbedding(EmbeddingService):
    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or ""

    def embed(self, text: str) -> list[float]:
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"input": text, "model": self.model},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"input": texts, "model": self.model},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda x: x["index"])
        return [d["embedding"] for d in data]
