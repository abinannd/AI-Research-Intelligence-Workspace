from dataclasses import dataclass

from app.config import Settings, get_settings
from app.citations.llm import LLMService, build_llm
from app.documents.queue import IngestQueue, build_queue
from app.documents.storage import Storage, build_storage
from app.retrieval.embeddings import EmbeddingService, build_embeddings
from app.retrieval.qdrant_store import VectorStore, build_vector_store
from app.retrieval.retriever import Retriever

_storage: Storage | None = None
_queue: IngestQueue | None = None
_vectors: VectorStore | None = None
_embeddings: EmbeddingService | None = None
_llm: LLMService | None = None


@dataclass
class Runtime:
    settings: Settings
    storage: Storage
    queue: IngestQueue
    vectors: VectorStore
    embeddings: EmbeddingService
    llm: LLMService
    retriever: Retriever


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = build_storage(get_settings())
        _storage.ensure_ready()
    return _storage


def get_queue() -> IngestQueue:
    global _queue
    if _queue is None:
        _queue = build_queue(get_settings())
    return _queue


def get_vectors() -> VectorStore:
    global _vectors
    if _vectors is None:
        _vectors = build_vector_store(get_settings())
        _vectors.ensure_collection()
    return _vectors


def get_embeddings() -> EmbeddingService:
    global _embeddings
    if _embeddings is None:
        _embeddings = build_embeddings(get_settings())
    return _embeddings


def get_llm() -> LLMService:
    global _llm
    if _llm is None:
        _llm = build_llm(get_settings())
    return _llm


def get_runtime() -> Runtime:
    settings = get_settings()
    embeddings = get_embeddings()
    vectors = get_vectors()
    return Runtime(
        settings=settings,
        storage=get_storage(),
        queue=get_queue(),
        vectors=vectors,
        embeddings=embeddings,
        llm=get_llm(),
        retriever=Retriever(embeddings, vectors, settings.retrieval_top_k),
    )


def reset_runtime() -> None:
    global _storage, _queue, _vectors, _embeddings, _llm
    _storage = None
    _queue = None
    _vectors = None
    _embeddings = None
    _llm = None
