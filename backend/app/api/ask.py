from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.citations.qa import answer_question
from app.config import get_settings
from app.database import get_db
from app.models import Document, Query, User
from app.runtime import get_llm, get_runtime
from app.schemas import AskIn, AskOut, CitationOut, ClaimOut
from app.security import get_current_user
from app.workspaces.service import get_owned_workspace

router = APIRouter(prefix="/api/workspaces/{workspace_id}", tags=["ask"])


def _serialize(query: Query) -> AskOut:
    claims = [
        ClaimOut(id=c.id, claim_text=c.claim_text, support_status=c.support_status)
        for c in sorted(query.claims, key=lambda x: x.id)
    ]
    citations = [
        CitationOut(
            id=ct.id,
            claim_id=ct.claim_id,
            index=ct.index,
            document_id=ct.document_id,
            filename=ct.filename,
            page_number=ct.page_number,
            chunk_id=ct.chunk_id,
            quote=ct.quote,
            heading=ct.heading,
        )
        for ct in sorted(query.citations, key=lambda x: x.index)
    ]
    return AskOut(
        id=query.id,
        question=query.question,
        abstained=query.abstained,
        abstain_reason=query.abstain_reason,
        answer=query.answer,
        claims=claims,
        citations=citations,
        latency_ms=query.latency_ms,
        model_version=query.model_version,
        prompt_version=query.prompt_version,
        retrieval_version=query.retrieval_version,
    )


@router.post("/ask", response_model=AskOut)
def ask(
    workspace_id: str,
    body: AskIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskOut:
    get_owned_workspace(db, user, workspace_id)
    q = db.query(Document).filter(Document.workspace_id == workspace_id, Document.status == "ready")
    ready = q.all()
    ready_ids = {d.id for d in ready}
    if not ready_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ask is locked until at least one PDF is Ready",
        )
    document_ids = body.document_ids
    if document_ids:
        missing = [did for did in document_ids if did not in ready_ids]
        owned = {
            d.id
            for d in db.query(Document).filter(Document.workspace_id == workspace_id, Document.id.in_(document_ids)).all()
        }
        if len(owned) != len(set(document_ids)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in this workspace")
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected documents are not Ready",
            )
    runtime = get_runtime()
    query = answer_question(
        db,
        workspace_id=workspace_id,
        user_id=user.id,
        question=body.question.strip(),
        document_ids=document_ids,
        retriever=runtime.retriever,
        llm=get_llm(),
        settings=get_settings(),
    )
    query = (
        db.query(Query)
        .options(selectinload(Query.claims), selectinload(Query.citations))
        .filter(Query.id == query.id)
        .one()
    )
    return _serialize(query)
