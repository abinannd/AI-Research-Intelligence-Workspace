from abc import ABC, abstractmethod

from redis import Redis
from rq import Queue

from app.config import Settings


class IngestQueue(ABC):
    @abstractmethod
    def enqueue_ingest(self, document_id: str) -> None: ...


class NoopQueue(IngestQueue):
    def enqueue_ingest(self, document_id: str) -> None:
        return None


class InlineQueue(IngestQueue):
    def enqueue_ingest(self, document_id: str) -> None:
        from workers.jobs import ingest_document

        ingest_document(document_id)


class RedisRQQueue(IngestQueue):
    def __init__(self, settings: Settings) -> None:
        self._queue = Queue("ingest", connection=Redis.from_url(settings.redis_url))

    def enqueue_ingest(self, document_id: str) -> None:
        self._queue.enqueue("workers.jobs.ingest_document", document_id, job_timeout=1800)


def build_queue(settings: Settings) -> IngestQueue:
    if settings.queue_backend == "rq":
        return RedisRQQueue(settings)
    if settings.queue_backend == "inline":
        return InlineQueue()
    return NoopQueue()
