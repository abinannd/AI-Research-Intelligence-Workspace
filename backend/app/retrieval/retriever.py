from app.retrieval.embeddings import EmbeddingService
from app.retrieval.qdrant_store import RetrievedChunk, VectorStore


class Retriever:
    def __init__(self, embeddings: EmbeddingService, store: VectorStore, top_k: int) -> None:
        self.embeddings = embeddings
        self.store = store
        self.top_k = top_k

    def search(
        self,
        question: str,
        workspace_id: str,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        vector = self.embeddings.embed_query(question)
        return self.store.search(
            vector=vector,
            workspace_id=workspace_id,
            document_ids=document_ids,
            limit=self.top_k,
        )
