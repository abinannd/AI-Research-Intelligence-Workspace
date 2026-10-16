import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from redis import Redis
from rq import Queue, Worker

from app.config import get_settings
from app.database import Base, get_engine
from app.runtime import get_runtime


def main() -> None:
    Base.metadata.create_all(bind=get_engine())
    get_runtime()
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    queues = [Queue("ingest", connection=redis)]
    Worker(queues, connection=redis).work(with_scheduler=False)


if __name__ == "__main__":
    main()
