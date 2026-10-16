from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class UserOut(BaseModel):
    id: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def _ser_dt(self, v: datetime) -> str:
        return v.isoformat()


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    page_count: int | None
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def _ser_dt(self, v: datetime) -> str:
        return v.isoformat()


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    document_ids: list[str] | None = None


class ClaimOut(BaseModel):
    id: str
    claim_text: str
    support_status: str


class CitationOut(BaseModel):
    id: str
    claim_id: str
    index: int
    document_id: str | None
    filename: str
    page_number: int
    chunk_id: str | None
    quote: str
    heading: str | None


class AskOut(BaseModel):
    id: str
    question: str
    abstained: bool
    abstain_reason: str | None = None
    answer: str
    claims: list[ClaimOut]
    citations: list[CitationOut]
    latency_ms: int
    model_version: str
    prompt_version: str
    retrieval_version: str
