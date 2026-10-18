import assert from "node:assert/strict";
import test from "node:test";

import { MAX_PDF_BYTES, validatePdfUpload } from "../src/lib/documentUpload.ts";

test("accepts PDF filenames regardless of extension casing at the 20 MiB limit", () => {
  assert.equal(validatePdfUpload("research.PDF", MAX_PDF_BYTES), null);
});

test("rejects files that do not have the PDF extension", () => {
  assert.equal(validatePdfUpload("research.docx", 1024), "Only PDF files are accepted.");
});

test("rejects empty files", () => {
  assert.equal(validatePdfUpload("empty.pdf", 0), "Choose a non-empty PDF file.");
});

test("rejects files larger than the backend's 20 MiB limit", () => {
  assert.equal(
    validatePdfUpload("oversized.pdf", MAX_PDF_BYTES + 1),
    "PDF exceeds the 20 MiB size limit.",
  );
});
