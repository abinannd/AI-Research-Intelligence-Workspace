from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.documents.service import create_document, delete_document, get_owned_document, list_documents, retry_document
from app.models import User
from app.runtime import get_queue, get_storage, get_vectors
from app.config import get_settings
from app.schemas import DocumentOut
from app.security import get_current_user

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])


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
    data = file.file.read()
    filename = file.filename or "upload.pdf"
    doc = create_document(
        db,
        user,
        workspace_id,
        filename,
        data,
        get_settings(),
        get_storage(),
        get_queue(),
    )
    return DocumentOut.model_validate(doc)


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
