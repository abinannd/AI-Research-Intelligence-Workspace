from __future__ import annotations

import hashlib
import struct
from abc import ABC, abstractmethod

from app.config import Settings

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class EmbeddingService(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    @property
    def version(self) -> str:
        return "unknown"


class HashEmbeddingService(EmbeddingService):
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    @property
    def version(self) -> str:
        return "hash-v1"

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self.dim:
            seed = hashlib.sha256(seed).digest()
            for i in range(0, len(seed), 4):
                if len(values) >= self.dim:
                    break
                (n,) = struct.unpack(">I", seed[i : i + 4])
                values.append((n / 2**32) * 2 - 1)
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(BGE_QUERY_PREFIX + text)


class SentenceTransformerEmbeddingService(EmbeddingService):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    @property
    def version(self) -> str:
        return self.model_name

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        return model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        return model.encode([BGE_QUERY_PREFIX + text], normalize_embeddings=True)[0].tolist()


def build_embeddings(settings: Settings) -> EmbeddingService:
    if settings.embedding_backend == "st":
        return SentenceTransformerEmbeddingService(settings.embedding_model)
    return HashEmbeddingService(settings.embedding_dim)
