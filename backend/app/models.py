from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped[User] = relationship(back_populates="workspaces")
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    queries: Mapped[list["Query"]] = relationship(back_populates="workspace")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    abstained: Mapped[bool] = mapped_column(default=False)
    abstain_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="queries")
    claims: Mapped[list["Claim"]] = relationship(back_populates="query", cascade="all, delete-orphan")
    citations: Mapped[list["Citation"]] = relationship(back_populates="query", cascade="all, delete-orphan")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    support_status: Mapped[str] = mapped_column(String(32), nullable=False)

    query: Mapped[Query] = relationship(back_populates="claims")
    citations: Mapped[list["Citation"]] = relationship(back_populates="claim")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)

    query: Mapped[Query] = relationship(back_populates="citations")
    claim: Mapped[Claim] = relationship(back_populates="citations")
