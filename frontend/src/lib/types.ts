export type DocumentStatus =
  | "queued"
  | "parsing"
  | "indexing"
  | "ready"
  | "failed"
  | "ocr_needed";

export type SupportStatus = "supported" | "unsupported" | string;

export interface User {
  id: string;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
}

export interface WorkspaceDocument {
  id: string;
  filename: string;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export interface Claim {
  id: string;
  claim_text: string;
  support_status: SupportStatus;
}

export interface Citation {
  id: string;
  claim_id: string | null;
  index: number;
  document_id: string;
  filename: string;
  page_number: number;
  chunk_id: string | null;
  quote: string;
  heading: string | null;
}

export interface AskResponse {
  id: string;
  question: string;
  abstained: boolean;
  abstain_reason?: string | null;
  answer: string;
  claims: Claim[];
  citations: Citation[];
  latency_ms: number;
  model_version: string;
  prompt_version: string;
  retrieval_version: string;
}

export interface ThreadTurn {
  id: string;
  question: string;
  response: AskResponse | null;
  error: string | null;
  pending: boolean;
}
