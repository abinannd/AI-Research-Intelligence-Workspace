from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.documents.queue import IngestQueue
from app.documents.storage import Storage
from app.models import Document, User
from app.parsing.pdf import PdfValidationError, validate_pdf_bytes
from app.retrieval.qdrant_store import VectorStore
from app.workspaces.service import get_owned_workspace


def list_documents(db: Session, user: User, workspace_id: str) -> list[Document]:
    get_owned_workspace(db, user, workspace_id)
    return (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .all()
    )


def get_owned_document(db: Session, user: User, workspace_id: str, document_id: str) -> Document:
    get_owned_workspace(db, user, workspace_id)
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == workspace_id)
        .one_or_none()
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def create_document(
    db: Session,
    user: User,
    workspace_id: str,
    filename: str,
    data: bytes,
    settings: Settings,
    storage: Storage,
    queue: IngestQueue,
) -> Document:
    get_owned_workspace(db, user, workspace_id)
    try:
        page_count = validate_pdf_bytes(data, filename, settings.max_pdf_bytes, settings.max_pdf_pages)
    except PdfValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    doc = Document(
        workspace_id=workspace_id,
        filename=filename,
        status="queued",
        page_count=page_count,
        storage_key="pending",
    )
    db.add(doc)
    db.flush()
    key = f"{workspace_id}/{doc.id}/{filename}"
    storage.put(key, data, content_type="application/pdf")
    doc.storage_key = key
    db.commit()
    db.refresh(doc)
    queue.enqueue_ingest(doc.id)
    db.refresh(doc)
    return doc


def retry_document(db: Session, user: User, workspace_id: str, document_id: str, queue: IngestQueue) -> Document:
    doc = get_owned_document(db, user, workspace_id, document_id)
    if doc.status not in {"failed", "ocr_needed", "queued"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retry is only available for queued, failed, or Needs OCR documents",
        )
    doc.status = "queued"
    doc.error_message = None
    db.commit()
    db.refresh(doc)
    queue.enqueue_ingest(doc.id)
    db.refresh(doc)
    return doc


def delete_document(
    db: Session,
    user: User,
    workspace_id: str,
    document_id: str,
    storage: Storage,
    vectors: VectorStore,
) -> None:
    doc = get_owned_document(db, user, workspace_id, document_id)
    try:
        storage.delete(doc.storage_key)
    except Exception:
        pass
    try:
        vectors.delete_document(workspace_id, document_id)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
