import { formatApiError } from "@/lib/utils";
import { getAccessToken, setAccessToken } from "@/lib/token";
import type {
  AskResponse,
  TokenResponse,
  User,
  Workspace,
  WorkspaceDocument,
} from "@/lib/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: { auth?: boolean; parseJson?: boolean } = {},
): Promise<T> {
  const { auth = true, parseJson = true } = options;
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401 && auth) {
    setAccessToken(null);
    onUnauthorized?.();
  }

  if (!response.ok) {
    const body = await parseBody(response);
    throw new ApiError(response.status, body, formatApiError(body, response.statusText));
  }

  if (!parseJson) {
    return undefined as T;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await parseBody(response)) as T;
}

export const api = {
  signup(email: string, password: string) {
    return request<TokenResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, { auth: false });
  },

  login(email: string, password: string) {
    return request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, { auth: false });
  },

  me() {
    return request<User>("/api/auth/me");
  },

  listWorkspaces() {
    return request<Workspace[]>("/api/workspaces");
  },

  createWorkspace(name: string) {
    return request<Workspace>("/api/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  getWorkspace(workspaceId: string) {
    return request<Workspace>(`/api/workspaces/${workspaceId}`);
  },

  listDocuments(workspaceId: string) {
    return request<WorkspaceDocument[]>(`/api/workspaces/${workspaceId}/documents`);
  },

  uploadDocument(workspaceId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<WorkspaceDocument>(`/api/workspaces/${workspaceId}/documents`, {
      method: "POST",
      body: form,
    });
  },

  retryDocument(workspaceId: string, documentId: string) {
    return request<WorkspaceDocument>(
      `/api/workspaces/${workspaceId}/documents/${documentId}/retry`,
      { method: "POST" },
    );
  },

  deleteDocument(workspaceId: string, documentId: string) {
    return request<void>(
      `/api/workspaces/${workspaceId}/documents/${documentId}`,
      { method: "DELETE" },
      { parseJson: true },
    );
  },

  async getDocumentFile(workspaceId: string, documentId: string): Promise<Blob> {
    const token = getAccessToken();
    const response = await fetch(
      `${API_BASE}/api/workspaces/${workspaceId}/documents/${documentId}/file`,
      {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      },
    );
    if (response.status === 401) {
      setAccessToken(null);
      onUnauthorized?.();
    }
    if (!response.ok) {
      const body = await parseBody(response);
      throw new ApiError(response.status, body, formatApiError(body, "Could not load PDF"));
    }
    return response.blob();
  },

  ask(workspaceId: string, payload: { question: string; document_ids?: string[] }, timeoutMs?: number) {
    const controller = new AbortController();
    const timeoutId = timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : undefined;
    const promise = request<AskResponse>(`/api/workspaces/${workspaceId}/ask`, {
      method: "POST",
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    if (timeoutId !== undefined) {
      promise.finally(() => clearTimeout(timeoutId));
    }
    return promise;
  },
};
