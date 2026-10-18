from typing import BinaryIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.documents.service import create_document, delete_document, get_owned_document, list_documents, retry_document
from app.models import User
from app.runtime import get_queue, get_storage, get_vectors
from app.schemas import DocumentOut
from app.security import get_current_user

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])
_UPLOAD_READ_CHUNK_BYTES = 64 * 1024


def _read_upload_with_limit(stream: BinaryIO, max_bytes: int) -> bytes:
    data = bytearray()
    if max_bytes < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF exceeds size limit of {max_bytes} bytes",
        )

    while True:
        remaining = max_bytes - len(data)
        chunk = stream.read(min(_UPLOAD_READ_CHUNK_BYTES, remaining + 1))
        if not chunk:
            return bytes(data)
        if len(chunk) > remaining:
            data.clear()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF exceeds size limit of {max_bytes} bytes",
            )
        data.extend(chunk)


@router.get("", response_model=list[DocumentOut])
def get_documents(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in list_documents(db, user, workspace_id)]


@router.post("", response_model=DocumentOut)
def post_document(
    workspace_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    try:
        settings = get_settings()
        data = _read_upload_with_limit(file.file, settings.max_pdf_bytes)
        filename = file.filename or "upload.pdf"
        doc = create_document(
            db,
            user,
            workspace_id,
            filename,
            data,
            settings,
            get_storage(),
            get_queue(),
        )
        return DocumentOut.model_validate(doc)
    finally:
        file.file.close()


@router.post("/{document_id}/retry", response_model=DocumentOut)
def post_retry(
    workspace_id: str,
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = retry_document(db, user, workspace_id, document_id, get_queue())
    return DocumentOut.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(
    workspace_id: str,
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    delete_document(db, user, workspace_id, document_id, get_storage(), get_vectors())
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/file")
def get_file(
    workspace_id: str,
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc = get_owned_document(db, user, workspace_id, document_id)
    try:
        data = get_storage().get(doc.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing in storage") from exc
    return Response(content=data, media_type="application/pdf")
