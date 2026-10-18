"use client";

import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { api } from "@/lib/api";
import WorkspaceAsk from "@/components/WorkspaceAsk";
import { validatePdfUpload } from "@/lib/documentUpload";
import { IN_FLIGHT_STATUSES, statusHelp, statusLabel } from "@/lib/status";
import type { DocumentStatus, WorkspaceDocument } from "@/lib/types";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  queued: "bg-amber-100 text-amber-900",
  parsing: "bg-sky-100 text-sky-900",
  indexing: "bg-indigo-100 text-indigo-900",
  ready: "bg-emerald-100 text-emerald-900",
  failed: "bg-red-100 text-red-900",
  ocr_needed: "bg-orange-100 text-orange-900",
};
const STATUS_POLL_INTERVAL_MS = 4000;

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export default function WorkspaceDocuments({ workspaceId }: { workspaceId: string }) {
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadPending, setUploadPending] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDocuments() {
      setLoading(true);
      setDocumentsError(null);
      try {
        const result = await api.listDocuments(workspaceId);
        if (active) setDocuments(result);
      } catch (error) {
        if (active) setDocumentsError(errorMessage(error));
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadDocuments();
    return () => {
      active = false;
    };
  }, [workspaceId]);

  const hasInFlightDocuments = documents.some((document) =>
    IN_FLIGHT_STATUSES.has(document.status),
  );

  useEffect(() => {
    if (!hasInFlightDocuments || uploadPending || refreshing) return;
    let active = true;
    let timeoutId: number;

    async function pollDocuments() {
      if (document.visibilityState === "visible") {
        try {
          const result = await api.listDocuments(workspaceId);
          if (active) {
            setDocuments(result);
            setDocumentsError(null);
          }
        } catch (error) {
          if (active) setDocumentsError(errorMessage(error));
        }
      }
      if (active) timeoutId = window.setTimeout(pollDocuments, STATUS_POLL_INTERVAL_MS);
    }

    timeoutId = window.setTimeout(pollDocuments, STATUS_POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearTimeout(timeoutId);
    };
  }, [hasInFlightDocuments, refreshing, uploadPending, workspaceId]);

  async function refreshDocuments() {
    setRefreshing(true);
    setDocumentsError(null);
    try {
      setDocuments(await api.listDocuments(workspaceId));
    } catch (error) {
      setDocumentsError(errorMessage(error));
    } finally {
      setRefreshing(false);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0] ?? null;
    setUploadSuccess(null);
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const validationError = validatePdfUpload(file.name, file.size);
    if (validationError) {
      setSelectedFile(null);
      setUploadError(validationError);
      event.currentTarget.value = "";
      return;
    }
    setSelectedFile(file);
    setUploadError(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setUploadError(null);
    setUploadSuccess(null);
    if (!selectedFile) {
      setUploadError("Choose a PDF file to upload.");
      return;
    }

    const validationError = validatePdfUpload(selectedFile.name, selectedFile.size);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setUploadPending(true);
    try {
      const uploaded = await api.uploadDocument(workspaceId, selectedFile);
      setDocuments((current) => [
        uploaded,
        ...current.filter((document) => document.id !== uploaded.id),
      ]);
      setUploadSuccess(`Uploaded ${uploaded.filename}. Processing status: ${statusLabel(uploaded.status)}.`);
      setSelectedFile(null);
      form.reset();
    } catch (error) {
      setUploadError(errorMessage(error));
    } finally {
      setUploadPending(false);
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Workspace documents</h3>
          <p className="mt-1 text-sm text-slate-600">
            Upload a text-based PDF up to 20 MiB and 80 pages.
          </p>
        </div>
        <button
          className="shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
          disabled={loading || refreshing || uploadPending}
          onClick={() => void refreshDocuments()}
          type="button"
        >
          {refreshing ? "Refreshing…" : "Refresh documents"}
        </button>
      </div>

      <form className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleUpload}>
        <label className="flex min-w-0 flex-1 flex-col gap-1.5 text-sm font-medium text-slate-700">
          PDF file
          <input
            accept=".pdf,application/pdf"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 file:mr-3 file:rounded file:border-0 file:bg-sky-50 file:px-3 file:py-1.5 file:font-semibold file:text-sky-900 hover:file:bg-sky-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
            disabled={loading || refreshing || uploadPending}
            onChange={handleFileChange}
            type="file"
          />
        </label>
        <button
          className="rounded-md bg-sky-800 px-4 py-2.5 font-semibold text-white hover:bg-sky-900 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800"
          disabled={loading || refreshing || uploadPending || !selectedFile}
          type="submit"
        >
          {uploadPending ? "Uploading…" : "Upload PDF"}
        </button>
      </form>
      <p className="mt-2 text-xs text-slate-500">
        The file contents and 80-page limit are verified by the server. Uploading does not report percentage progress.
      </p>
      {uploadPending && (
        <p className="mt-3 text-sm text-sky-800" role="status">
          Uploading {selectedFile?.name}…
        </p>
      )}
      {uploadError && (
        <p className="mt-3 text-sm text-red-800" role="alert">{uploadError}</p>
      )}
      {uploadSuccess && (
        <p className="mt-3 text-sm text-emerald-800" role="status">{uploadSuccess}</p>
      )}

      <div className="mt-6 border-t border-slate-200 pt-5">
        <h4 className="font-semibold text-slate-900">Uploaded PDFs</h4>
        {documentsError && (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            <p role="alert">Could not load document status: {documentsError}</p>
            <button
              className="mt-2 font-semibold underline underline-offset-2"
              disabled={refreshing || uploadPending}
              onClick={() => void refreshDocuments()}
              type="button"
            >
              Try again
            </button>
          </div>
        )}
        {loading ? (
          <p className="mt-3 text-sm text-slate-600" role="status">Loading documents…</p>
        ) : documents.length > 0 ? (
          <ul className="mt-3 divide-y divide-slate-200">
            {documents.map((document) => (
              <li className="flex flex-col gap-2 py-4 sm:flex-row sm:items-start sm:justify-between" key={document.id}>
                <div className="min-w-0">
                  <p className="break-words font-medium text-slate-900">{document.filename}</p>
                  <p className="mt-1 text-sm text-slate-600">
                    {document.page_count === null
                      ? "Page count unavailable"
                      : `${document.page_count} ${document.page_count === 1 ? "page" : "pages"}`}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {statusHelp(document.status, document.error_message)}
                  </p>
                </div>
                <span
                  className={`w-fit shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[document.status]}`}
                  aria-label={`Processing status: ${statusLabel(document.status)}`}
                >
                  {statusLabel(document.status)}
                </span>
              </li>
            ))}
          </ul>
        ) : documentsError ? null : (
          <div className="mt-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-center">
            <p className="font-medium text-slate-800">No PDFs in this workspace yet</p>
            <p className="mt-1 text-sm text-slate-600">
              Choose a PDF above to start processing your first research document.
            </p>
          </div>
        )}
        {hasInFlightDocuments && (
          <p className="mt-2 text-xs text-slate-500" role="status">
            Processing statuses refresh automatically while this page is open.
          </p>
        )}
      </div>
      <WorkspaceAsk
        documentsError={documentsError !== null}
        documentsLoading={loading || refreshing}
        readyDocumentIds={documents
          .filter((document) => document.status === "ready")
          .map((document) => document.id)}
        workspaceId={workspaceId}
      />
    </section>
  );
}
