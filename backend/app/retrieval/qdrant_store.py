from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock

from app.config import Settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    workspace_id: str
    document_id: str
    filename: str
    page_number: int
    heading: str | None
    text: str
    score: float


class VectorStore(ABC):
    @abstractmethod
    def ensure_collection(self) -> None: ...

    @abstractmethod
    def upsert(self, points: list[dict]) -> None: ...

    @abstractmethod
    def search(
        self,
        vector: list[float],
        workspace_id: str,
        document_ids: list[str] | None,
        limit: int,
    ) -> list[RetrievedChunk]: ...

    @abstractmethod
    def delete_document(self, workspace_id: str, document_id: str) -> None: ...


class MemoryVectorStore(VectorStore):
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._points: dict[str, dict] = {}
        self._lock = Lock()

    def ensure_collection(self) -> None:
        return None

    def upsert(self, points: list[dict]) -> None:
        with self._lock:
            for p in points:
                self._points[str(p["id"])] = p

    def search(
        self,
        vector: list[float],
        workspace_id: str,
        document_ids: list[str] | None,
        limit: int,
    ) -> list[RetrievedChunk]:
        def dot(a: list[float], b: list[float]) -> float:
            return sum(x * y for x, y in zip(a, b, strict=False))

        scored: list[RetrievedChunk] = []
        with self._lock:
            for p in self._points.values():
                payload = p["payload"]
                if payload.get("workspace_id") != workspace_id:
                    continue
                if document_ids is not None and payload.get("document_id") not in document_ids:
                    continue
                score = dot(vector, p["vector"])
                scored.append(
                    RetrievedChunk(
                        chunk_id=payload["chunk_id"],
                        workspace_id=payload["workspace_id"],
                        document_id=payload["document_id"],
                        filename=payload.get("filename") or "",
                        page_number=int(payload.get("page_number") or 1),
                        heading=payload.get("heading"),
                        text=payload.get("text") or "",
                        score=score,
                    )
                )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:limit]

    def delete_document(self, workspace_id: str, document_id: str) -> None:
        with self._lock:
            remove = [
                pid
                for pid, p in self._points.items()
                if p["payload"].get("document_id") == document_id
                and p["payload"].get("workspace_id") == workspace_id
            ]
            for pid in remove:
                self._points.pop(pid, None)


class QdrantVectorStore(VectorStore):
    def __init__(self, settings: Settings) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
        self.dim = settings.embedding_dim

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def upsert(self, points: list[dict]) -> None:
        from qdrant_client.models import PointStruct

        structs = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
        if structs:
            self.client.upsert(collection_name=self.collection, points=structs)

    def search(
        self,
        vector: list[float],
        workspace_id: str,
        document_ids: list[str] | None,
        limit: int,
    ) -> list[RetrievedChunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        must = [FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
        if document_ids:
            must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        out: list[RetrievedChunk] = []
        for hit in results:
            payload = hit.payload or {}
            if payload.get("workspace_id") != workspace_id:
                continue
            out.append(
                RetrievedChunk(
                    chunk_id=str(payload.get("chunk_id") or hit.id),
                    workspace_id=str(payload.get("workspace_id")),
                    document_id=str(payload.get("document_id")),
                    filename=str(payload.get("filename") or ""),
                    page_number=int(payload.get("page_number") or 1),
                    heading=payload.get("heading"),
                    text=str(payload.get("text") or ""),
                    score=float(hit.score or 0),
                )
            )
        return out

    def delete_document(self, workspace_id: str, document_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

        self.client.delete(
            collection_name=self.collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
                        FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                    ]
                )
            ),
        )


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.vector_backend == "qdrant":
        return QdrantVectorStore(settings)
    return MemoryVectorStore(settings.embedding_dim)
