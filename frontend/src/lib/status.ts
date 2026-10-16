import type { DocumentStatus } from "@/lib/types";

export const TERMINAL_STATUSES: ReadonlySet<DocumentStatus> = new Set([
  "ready",
  "failed",
  "ocr_needed",
]);

export const IN_FLIGHT_STATUSES: ReadonlySet<DocumentStatus> = new Set([
  "queued",
  "parsing",
  "indexing",
]);

export function isTerminalStatus(status: DocumentStatus): boolean {
  return TERMINAL_STATUSES.has(status);
}

export function statusLabel(status: DocumentStatus): string {
  switch (status) {
    case "queued":
      return "Queued";
    case "parsing":
      return "Parsing";
    case "indexing":
      return "Indexing";
    case "ready":
      return "Ready";
    case "failed":
      return "Failed";
    case "ocr_needed":
      return "Needs OCR";
    default:
      return status;
  }
}

export function statusHelp(status: DocumentStatus, errorMessage?: string | null): string {
  if (errorMessage) return errorMessage;
  switch (status) {
    case "queued":
      return "Waiting for the ingestion worker to pick up this file.";
    case "parsing":
      return "Extracting page text and headings from the PDF.";
    case "indexing":
      return "Embedding pages so they can be cited. Ask unlocks when this becomes Ready.";
    case "ready":
      return "Indexed and searchable. You can ask questions about this paper.";
    case "failed":
      return "Ingestion failed. Retry, or delete and upload a different PDF.";
    case "ocr_needed":
      return "This PDF looks scanned or empty of text. OCR is not in the MVP — upload a text-based PDF instead.";
    default:
      return "Status unknown.";
  }
}
