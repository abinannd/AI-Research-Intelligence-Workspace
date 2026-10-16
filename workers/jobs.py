from __future__ import annotations

from app.database import get_sessionmaker
from app.models import Chunk, Document
from app.parsing.chunking import chunk_pages
from app.parsing.pdf import parse_pdf
from app.runtime import get_embeddings, get_storage, get_vectors


def _set_status(db, doc: Document, status: str, error: str | None = None) -> None:
    doc.status = status
    doc.error_message = error
    db.commit()
    db.refresh(doc)


def ingest_document(document_id: str) -> None:
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        _set_status(db, doc, "parsing")
        try:
            data = get_storage().get(doc.storage_key)
            parsed = parse_pdf(data)
            doc.page_count = parsed.page_count
            db.commit()
        except Exception as exc:
            _set_status(db, doc, "failed", f"Parse failed: {exc}")
            return

        text_pages = [p for p in parsed.pages if not p.likely_scanned]
        if not text_pages:
            _set_status(db, doc, "ocr_needed", "Pages look scanned or empty; OCR is out of scope for MVP")
            return

        drafts = chunk_pages(parsed.pages)
        if not drafts:
            _set_status(db, doc, "ocr_needed", "No extractable text after chunking")
            return

        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        db.commit()
        chunks: list[Chunk] = []
        for draft in drafts:
            chunk = Chunk(
                document_id=doc.id,
                workspace_id=doc.workspace_id,
                page_number=draft.page_number,
                heading=draft.heading,
                text=draft.text,
            )
            db.add(chunk)
            chunks.append(chunk)
        db.commit()
        for chunk in chunks:
            db.refresh(chunk)

        _set_status(db, doc, "indexing")
        try:
            get_vectors().delete_document(doc.workspace_id, doc.id)
            embeddings = get_embeddings().embed_documents([c.text for c in chunks])
            points = []
            for chunk, vector in zip(chunks, embeddings, strict=True):
                points.append(
                    {
                        "id": chunk.id,
                        "vector": vector,
                        "payload": {
                            "workspace_id": doc.workspace_id,
                            "document_id": doc.id,
                            "chunk_id": chunk.id,
                            "filename": doc.filename,
                            "page_number": chunk.page_number,
                            "heading": chunk.heading,
                            "text": chunk.text,
                        },
                    }
                )
            get_vectors().upsert(points)
        except Exception as exc:
            _set_status(db, doc, "failed", f"Indexing failed: {exc}")
            return

        _set_status(db, doc, "ready")
    except Exception as exc:
        try:
            doc = db.get(Document, document_id)
            if doc is not None:
                _set_status(db, doc, "failed", str(exc))
        except Exception:
            db.rollback()
    finally:
        db.close()
