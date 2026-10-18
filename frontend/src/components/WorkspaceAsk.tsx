"use client";

import { useState, type FormEvent } from "react";

import { ApiError, api } from "@/lib/api";
import { createAskPayload } from "@/lib/ask";
import type { AskResponse } from "@/lib/types";

interface WorkspaceAskProps {
  workspaceId: string;
  readyDocumentIds: string[];
  documentsLoading: boolean;
  documentsError: boolean;
}

export default function WorkspaceAsk({
  workspaceId,
  readyDocumentIds,
  documentsLoading,
  documentsError,
}: WorkspaceAskProps) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload = createAskPayload(question, readyDocumentIds);
  const disabled = documentsLoading || documentsError || pending || payload === null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requestPayload = createAskPayload(question, readyDocumentIds);
    if (!requestPayload) return;

    setError(null);
    setResponse(null);
    setPending(true);
    try {
      setResponse(await api.ask(workspaceId, requestPayload));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        setError("Your session has expired. Please sign in again.");
      } else if (requestError instanceof ApiError && requestError.status === 403) {
        setError("You are not authorized to ask questions in this workspace.");
      } else {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Could not get an answer. Please try again.",
        );
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mt-6 border-t border-slate-200 pt-5" aria-labelledby="workspace-ask-heading">
      <h3 id="workspace-ask-heading" className="text-lg font-semibold text-slate-900">
        Ask this workspace
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        Ask a question about the indexed PDFs in this workspace.
      </p>
      {documentsLoading ? (
        <p className="mt-3 text-sm text-slate-600" role="status">
          Checking document readiness…
        </p>
      ) : documentsError ? (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          Document readiness could not be checked. Refresh the document list before asking.
        </p>
      ) : readyDocumentIds.length === 0 ? (
        <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
          Ask is locked until at least one PDF is Ready.
        </p>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          Searching {readyDocumentIds.length} ready {readyDocumentIds.length === 1 ? "PDF" : "PDFs"}.
        </p>
      )}

      <form className="mt-4 flex flex-col gap-3" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700" htmlFor="workspace-question">
          Question
          <textarea
            className="min-h-28 resize-y rounded-md border border-slate-300 px-3 py-2.5 text-base text-slate-950 outline-none focus:border-sky-700 focus:ring-2 focus:ring-sky-100 disabled:bg-slate-50"
            disabled={documentsLoading || pending}
            id="workspace-question"
            maxLength={8000}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What are the main findings?"
            required
            value={question}
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs text-slate-500">{question.length}/8000 characters</span>
          <button
            className="rounded-md bg-sky-800 px-4 py-2.5 font-semibold text-white hover:bg-sky-900 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800"
            disabled={disabled}
            type="submit"
          >
            {pending ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {error && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      {response && (
        <section className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:p-5" aria-label="Answer">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-semibold text-slate-900">Answer</h4>
            <span className="text-xs text-slate-500">{response.latency_ms} ms</span>
          </div>
          {response.abstained && (
            <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-950">
              The answer is not supported by the available sources.
              {response.abstain_reason ? ` ${response.abstain_reason}` : ""}
            </p>
          )}
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-800">
            {response.answer}
          </p>

          {response.claims.length > 0 && (
            <div className="mt-5">
              <h5 className="font-semibold text-slate-900">Claims</h5>
              <ul className="mt-2 space-y-2">
                {response.claims.map((claim) => (
                  <li className="rounded-md bg-white px-3 py-2 text-sm text-slate-800" key={claim.id}>
                    <span>{claim.claim_text}</span>
                    <span className="ml-2 text-xs font-medium text-slate-500">
                      {claim.support_status}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {response.citations.length > 0 && (
            <div className="mt-5">
              <h5 className="font-semibold text-slate-900">Sources</h5>
              <ol className="mt-2 space-y-3">
                {response.citations.map((citation) => (
                  <li className="rounded-md border border-slate-200 bg-white p-3" key={citation.id}>
                    <p className="text-sm font-semibold text-sky-900">
                      [{citation.index}] {citation.filename} · Page {citation.page_number}
                    </p>
                    {citation.heading && (
                      <p className="mt-1 text-xs font-medium text-slate-600">{citation.heading}</p>
                    )}
                    <blockquote className="mt-2 border-l-2 border-slate-300 pl-3 text-sm leading-5 text-slate-700">
                      {citation.quote}
                    </blockquote>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </section>
      )}
    </section>
  );
}
