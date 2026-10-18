import os
from collections.abc import Generator

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings, reset_settings
from app.database import Base, get_db, reset_engine
from app.main import create_app
from app.models import User, Workspace
from app.runtime import reset_runtime
from app.security import create_access_token, hash_password


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("QUEUE_BACKEND", "inline")
    monkeypatch.setenv("LLM_BACKEND", "stub")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-32-chars-long-12345")
    monkeypatch.setenv("MINIO_SECURE", "false")
    reset_settings()
    reset_engine()
    reset_runtime()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        reset_engine()
        reset_runtime()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pdf_generator():
    """Generates valid and invalid in-memory PDF bytes for tests."""

    def _generate(
        pages: int = 1,
        title: str = "Test Research Paper",
        body_text: str = "This is a verified test document paragraph for citation testing.",
        scanned: bool = False,
    ) -> bytes:
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page(width=595, height=842)
            if not scanned:
                page.insert_text(
                    (50, 72),
                    f"{title} - Page {i + 1}",
                    fontsize=16,
                )
                page.insert_text(
                    (50, 120),
                    f"{body_text} This is sentence two on page {i + 1} with verifiable evidence.",
                    fontsize=10,
                )
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    return _generate


@pytest.fixture
def auth_user(db_session: Session) -> tuple[User, str, dict[str, str]]:
    """Creates a test user and returns (user, token, auth_headers)."""
    user = User(
        email="researcher@test.local",
        password_hash=hash_password("SecretPassword123!"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token({"sub": user.id})
    headers = {"Authorization": f"Bearer {token}"}
    return user, token, headers


@pytest.fixture
def test_workspace(db_session: Session, auth_user: tuple[User, str, dict[str, str]]) -> Workspace:
    """Creates a workspace owned by the auth_user."""
    user, _, _ = auth_user
    ws = Workspace(
        name="Quantum Computing Lab",
        user_id=user.id,
    )
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)
    return ws
