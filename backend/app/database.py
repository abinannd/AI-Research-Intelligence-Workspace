from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        kwargs: dict = {}
        if settings.database_url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = StaticPool
        _engine = create_engine(settings.database_url, **kwargs)
        if settings.database_url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _fk_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
