from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.citations.llm import LLMService, run_llm
from app.citations.validator import validate_model_output
from app.config import Settings
from app.models import Citation, Claim, Query
from app.retrieval.qdrant_store import RetrievedChunk
from app.retrieval.retriever import Retriever


def answer_question(
    db: Session,
    *,
    workspace_id: str,
    user_id: str,
    question: str,
    document_ids: list[str] | None,
    retriever: Retriever,
    llm: LLMService,
    settings: Settings,
) -> Query:
    started = time.perf_counter()
    retrieved = retriever.search(question, workspace_id=workspace_id, document_ids=document_ids)
    parsed: dict
    try:
        parsed = run_llm(llm, question, retrieved)
    except Exception:
        parsed = {
            "abstain": True,
            "abstain_reason": "The synthesizer could not produce a structured answer",
            "answer": "The sources do not answer this.",
            "claims": [],
        }
    abstained, reason, answer, claims = validate_model_output(parsed, retrieved)
    latency_ms = int((time.perf_counter() - started) * 1000)

    query = Query(
        workspace_id=workspace_id,
        user_id=user_id,
        question=question,
        answer=answer,
        abstained=abstained,
        abstain_reason=reason,
        latency_ms=latency_ms,
        model_version=llm.model_version,
        prompt_version=settings.prompt_version,
        retrieval_version=settings.retrieval_version,
    )
    db.add(query)
    db.flush()

    by_index: dict[int, RetrievedChunk] = {i: c for i, c in enumerate(retrieved, start=1)}
    citation_index = 1
    for claim_data in claims:
        claim = Claim(
            query_id=query.id,
            claim_text=claim_data.claim_text,
            support_status="abstain" if abstained and claim_data.support_status != "supported" else claim_data.support_status,
        )
        if abstained and not claim_data.citation_indexes:
            claim.support_status = "abstain"
        db.add(claim)
        db.flush()
        for idx in claim_data.citation_indexes:
            chunk = by_index.get(idx)
            if chunk is None:
                continue
            db.add(
                Citation(
                    query_id=query.id,
                    claim_id=claim.id,
                    index=citation_index,
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    quote=chunk.text[:500],
                    heading=chunk.heading,
                )
            )
            citation_index += 1

    db.commit()
    db.refresh(query)
    return query
