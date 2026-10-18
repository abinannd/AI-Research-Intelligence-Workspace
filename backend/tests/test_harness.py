import io
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import documents as documents_api
from app.config import Settings
from app.citations.validator import validate_model_output
from app.models import Document, User, Workspace
from app.parsing.chunking import chunk_pages
from app.parsing.pdf import PageText, PdfValidationError, parse_pdf, validate_pdf_bytes
from app.retrieval.embeddings import HashEmbeddingService
from app.retrieval.qdrant_store import MemoryVectorStore, RetrievedChunk


class RecordingStorage:
    def __init__(self) -> None:
        self.put_calls: list[tuple[str, bytes, str]] = []

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        self.put_calls.append((key, data, content_type))


class RecordingQueue:
    def __init__(self) -> None:
        self.document_ids: list[str] = []

    def enqueue_ingest(self, document_id: str) -> None:
        self.document_ids.append(document_id)


def _configure_upload_dependencies(monkeypatch: pytest.MonkeyPatch, max_bytes: int):
    storage = RecordingStorage()
    queue = RecordingQueue()
    monkeypatch.setattr(documents_api, "get_settings", lambda: Settings(max_pdf_bytes=max_bytes))
    monkeypatch.setattr(documents_api, "get_storage", lambda: storage)
    monkeypatch.setattr(documents_api, "get_queue", lambda: queue)
    return storage, queue


def _create_authenticated_workspace(client: TestClient) -> tuple[str, dict[str, str]]:
    signup = client.post(
        "/api/auth/signup",
        json={"email": "upload-researcher@lab.org", "password": "StrongPassword999!"},
    )
    assert signup.status_code == 200
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    workspace = client.post("/api/workspaces", json={"name": "Upload test"}, headers=headers)
    assert workspace.status_code == 200
    return workspace.json()["id"], headers


class TrackingStream(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.read_sizes: list[int] = []
        self.bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        chunk = super().read(size)
        self.bytes_returned += len(chunk)
        return chunk


def test_health_check(client: TestClient) -> None:
    """Verifies that the FastAPI test client can query /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sqlite_in_memory_fixtures(
    db_session: Session,
    auth_user: tuple[User, str, dict[str, str]],
    test_workspace: Workspace,
) -> None:
    """Verifies in-memory SQLite table schema, user fixture, and workspace persistence."""
    user, _, _ = auth_user
    assert user.id is not None
    assert test_workspace.user_id == user.id

    fetched = db_session.get(Workspace, test_workspace.id)
    assert fetched is not None
    assert fetched.name == "Quantum Computing Lab"


def test_auth_signup_and_me(client: TestClient) -> None:
    """Verifies signup and /api/auth/me token authentication flow."""
    signup_payload = {
        "email": "new_researcher@lab.org",
        "password": "StrongPassword999!",
    }
    signup_res = client.post("/api/auth/signup", json=signup_payload)
    assert signup_res.status_code == 200
    token_data = signup_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "new_researcher@lab.org"


def test_pdf_generator_and_parsing(pdf_generator) -> None:
    """Verifies the in-memory PDF generator creates valid multi-page PDFs readable by PyMuPDF."""
    pdf_bytes = pdf_generator(pages=3, title="Neural Graph Attention")
    assert pdf_bytes.startswith(b"%PDF")

    # Validate byte cap and page cap
    page_count = validate_pdf_bytes(pdf_bytes, "graph_attention.pdf", max_bytes=20_000_000, max_pages=80)
    assert page_count == 3

    # Parse and extract text
    parsed = parse_pdf(pdf_bytes)
    assert parsed.page_count == 3
    assert len(parsed.pages) == 3
    assert "Neural Graph Attention" in parsed.pages[0].text
    assert parsed.pages[0].likely_scanned is False


def test_pdf_validation_rejections(pdf_generator) -> None:
    """Verifies PDF validator rejects non-PDF, oversized, and corrupted streams."""
    # Non-PDF extension
    with pytest.raises(PdfValidationError, match="Only PDF files are accepted"):
        validate_pdf_bytes(b"%PDF-1.4 test", "document.docx", max_bytes=1000, max_pages=10)

    # Corrupt / non-PDF header
    with pytest.raises(PdfValidationError, match="File is not a valid PDF"):
        validate_pdf_bytes(b"NOT_A_PDF_FILE", "paper.pdf", max_bytes=1000, max_pages=10)

    # Exceeds max bytes
    valid_pdf = pdf_generator(pages=1)
    with pytest.raises(PdfValidationError, match="exceeds size limit"):
        validate_pdf_bytes(valid_pdf, "paper.pdf", max_bytes=10, max_pages=10)

    # Exceeds max pages
    multi_page_pdf = pdf_generator(pages=5)
    with pytest.raises(PdfValidationError, match="exceeds page limit"):
        validate_pdf_bytes(multi_page_pdf, "paper.pdf", max_bytes=10_000_000, max_pages=2)


def test_read_upload_with_limit_reads_incrementally_and_stops_after_one_excess_byte() -> None:
    stream = TrackingStream(b"x" * (128 * 1024 + 1))

    with pytest.raises(HTTPException, match="PDF exceeds size limit of 128000 bytes"):
        documents_api._read_upload_with_limit(stream, 128_000)

    assert stream.bytes_returned == 128_001
    assert all(0 < size <= documents_api._UPLOAD_READ_CHUNK_BYTES for size in stream.read_sizes)


def test_upload_pdf_below_size_limit_preserves_upload_behavior(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pdf_generator,
) -> None:
    pdf_bytes = pdf_generator()
    storage, queue = _configure_upload_dependencies(monkeypatch, len(pdf_bytes) + 1)
    workspace_id, headers = _create_authenticated_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    assert storage.put_calls[0][1] == pdf_bytes
    assert queue.document_ids == [response.json()["id"]]


def test_upload_pdf_exactly_at_size_limit_is_accepted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pdf_generator,
) -> None:
    pdf_bytes = pdf_generator()
    storage, queue = _configure_upload_dependencies(monkeypatch, len(pdf_bytes))
    workspace_id, headers = _create_authenticated_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    assert storage.put_calls[0][1] == pdf_bytes
    assert queue.document_ids == [response.json()["id"]]


def test_upload_pdf_over_limit_by_one_byte_stops_before_storage_and_queue(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pdf_generator,
) -> None:
    pdf_bytes = pdf_generator()
    storage, queue = _configure_upload_dependencies(monkeypatch, len(pdf_bytes) - 1)
    workspace_id, headers = _create_authenticated_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == f"PDF exceeds size limit of {len(pdf_bytes) - 1} bytes"
    assert storage.put_calls == []
    assert queue.document_ids == []


def test_upload_invalid_pdf_keeps_existing_validation_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage, queue = _configure_upload_dependencies(monkeypatch, 1024)
    workspace_id, headers = _create_authenticated_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        headers=headers,
        files={"file": ("paper.pdf", b"NOT_A_PDF_FILE", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File is not a valid PDF"
    assert storage.put_calls == []
    assert queue.document_ids == []


def test_scanned_pdf_flagging(pdf_generator) -> None:
    """Verifies that PDFs with no text are flagged as likely_scanned."""
    scanned_bytes = pdf_generator(pages=1, scanned=True)
    parsed = parse_pdf(scanned_bytes)
    assert len(parsed.pages) == 1
    assert parsed.pages[0].likely_scanned is True


def test_chunking_and_heading_attribution() -> None:
    """Verifies chunk_pages splits text with sliding windows and preserves page numbers."""
    pages = [
        PageText(
            page_number=1,
            text="First sentence of section one. Second sentence of section one. Third sentence.\n\nFourth sentence.",
            headings=["Section 1: Introduction"],
            likely_scanned=False,
        )
    ]
    chunks = chunk_pages(pages, size=100, overlap=20)
    assert len(chunks) >= 1
    assert chunks[0].page_number == 1
    assert chunks[0].heading == "Section 1: Introduction"
    assert len(chunks[0].text) > 0


def test_in_memory_vector_store_tenant_isolation() -> None:
    """Verifies MemoryVectorStore enforces workspace-level tenant isolation."""
    store = MemoryVectorStore(dim=64)
    embedder = HashEmbeddingService(dim=64)

    # Workspace A data
    vec_a = embedder.embed_documents(["Quantum teleportation protocol analysis"])[0]
    store.upsert([
        {
            "id": "chunk-a1",
            "vector": vec_a,
            "payload": {
                "workspace_id": "ws-alpha",
                "document_id": "doc-a1",
                "chunk_id": "chunk-a1",
                "filename": "quantum.pdf",
                "page_number": 1,
                "text": "Quantum teleportation protocol analysis",
            },
        }
    ])

    # Workspace B data
    vec_b = embedder.embed_documents(["Organic chemistry synthesis reaction"])[0]
    store.upsert([
        {
            "id": "chunk-b1",
            "vector": vec_b,
            "payload": {
                "workspace_id": "ws-beta",
                "document_id": "doc-b1",
                "chunk_id": "chunk-b1",
                "filename": "chemistry.pdf",
                "page_number": 1,
                "text": "Organic chemistry synthesis reaction",
            },
        }
    ])

    # Search from Workspace A for chemistry text: MUST NOT return Workspace B chunks
    query_vec = embedder.embed_query("chemistry synthesis")
    results = store.search(query_vec, workspace_id="ws-alpha", document_ids=None, limit=5)
    doc_ids = {r.document_id for r in results}
    assert "doc-b1" not in doc_ids


def test_citation_validator_grounding() -> None:
    """Verifies citation validator distinguishes supported vs unsupported claims and abstains when missing."""
    retrieved = [
        RetrievedChunk(
            chunk_id="chunk-1",
            workspace_id="ws-alpha",
            document_id="doc-1",
            filename="paper.pdf",
            page_number=3,
            heading="Methods",
            text="The experimental error rate was measured at 0.042.",
            score=0.95,
        )
    ]

    # 1. Valid supported claim
    model_output_valid = {
        "abstain": False,
        "answer": "The error rate is 0.042 [1].",
        "claims": [
            {
                "claim_text": "The error rate is 0.042.",
                "citation_indexes": [1],
            }
        ],
    }
    abstained, reason, answer, claims = validate_model_output(model_output_valid, retrieved)
    assert abstained is False
    assert len(claims) == 1
    assert claims[0].support_status == "supported"
    assert claims[0].citation_indexes == [1]

    # 2. Hallucinated citation index ([99] does not exist in retrieved set)
    model_output_hallucinated = {
        "abstain": False,
        "answer": "",
        "claims": [
            {
                "claim_text": "The result is 99% confident.",
                "citation_indexes": [99],
            }
        ],
    }
    abstained, reason, answer, claims = validate_model_output(model_output_hallucinated, retrieved)
    assert abstained is True
    assert "Citations were not in the retrieved set" in str(reason)
    assert answer == "The sources do not answer this."
    assert claims[0].support_status == "unsupported"

    # 3. Explicit abstain from synthesizer
    model_output_abstain = {
        "abstain": True,
        "abstain_reason": "Insufficient evidence in context",
        "answer": "The sources do not answer this.",
        "claims": [],
    }
    abstained, reason, answer, claims = validate_model_output(model_output_abstain, retrieved)
    assert abstained is True
    assert reason == "Insufficient evidence in context"
    assert answer == "The sources do not answer this."
