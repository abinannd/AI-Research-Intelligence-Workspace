# Phase 1 — Task 02: Enforce the PDF Upload Size Limit

**Project:** AI Research Intelligence Workspace | **Date:** 2026-10-18

## 1. Objective

Enforce the existing configured PDF byte limit while reading the uploaded file,
reject oversized input before it can reach document storage or queueing, and
preserve valid-upload and PDF-validation behavior.

## 2. Root cause

The synchronous `post_document` route in
[`backend/app/api/documents.py`](../../backend/app/api/documents.py) called
`file.file.read()` without a size argument. It therefore read the entire upload
into a `bytes` object before `create_document` called
`validate_pdf_bytes`, where the configured maximum was checked.

The byte limit is `Settings.max_pdf_bytes` in
[`backend/app/config.py`](../../backend/app/config.py), defaulting to 20 MiB.
`Storage.put` in [`backend/app/documents/storage.py`](../../backend/app/documents/storage.py)
requires complete `bytes`, so storage cannot accept a stream without a broader
interface change.

## 3. Files inspected

- [`backend/app/api/documents.py`](../../backend/app/api/documents.py) — actual
  upload route; synchronous `def`, previously unbounded read.
- [`backend/app/documents/service.py`](../../backend/app/documents/service.py) —
  existing PDF validation mapping and storage-before-queue ordering.
- [`backend/app/documents/storage.py`](../../backend/app/documents/storage.py)
  — storage interface accepts complete bytes.
- [`backend/app/config.py`](../../backend/app/config.py) — configured
  `max_pdf_bytes` setting.
- [`backend/app/parsing/pdf.py`](../../backend/app/parsing/pdf.py) — existing
  PDF byte, signature, parse, and page-count validation.
- [`backend/tests/conftest.py`](../../backend/tests/conftest.py) — isolated
  SQLite/in-memory test setup and PDF fixture.
- [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py) —
  existing PDF validation tests and added focused route tests.

## 4. Files created or modified

- **Modified:** [`backend/app/api/documents.py`](../../backend/app/api/documents.py)
- **Modified:** [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py)
- **Created:** this report.

No other tracked source files were changed. The pre-existing root `.env` remains
ignored and was not read, modified, or included in this report.

## 5. Implementation details

- Added `_read_upload_with_limit`, which reads at most 64 KiB per call and
  tracks the cumulative byte count against `settings.max_pdf_bytes`.
- Each read is capped to the smaller of the chunk limit and the remaining
  allowance plus one byte. The first byte over the limit triggers the existing
  HTTP 400 response detail (`PDF exceeds size limit of N bytes`); the helper
  clears its accumulated buffer and does not return partial data.
- A file exactly equal to the configured limit is accepted. The helper checks
  for end-of-file with a one-byte read after reaching the limit.
- The route passes complete bytes to the unchanged document service only after
  the bounded read succeeds. Consequently, oversized uploads cannot reach
  validation, storage, or queue submission through this route.
- The uploaded temporary file is closed in a `finally` block for success,
  validation errors, and other exceptions.
- Existing PDF signature, extension, parse, and page-count validation remains
  unchanged in `validate_pdf_bytes`.

## 6. Tests added

Added five focused regression tests to `test_harness.py`:

1. Valid PDF below the configured limit stores the original bytes and enqueues
   exactly one document.
2. Valid PDF exactly at the configured limit is accepted.
3. A tracked stream confirms bounded incremental reads and rejection after
   exactly one byte beyond its configured maximum.
4. An API upload one byte over the limit returns HTTP 400 and calls neither
   storage nor the queue.
5. Invalid PDF content retains the existing HTTP 400 validation response and
   does not call storage or the queue.

Tests use the existing in-memory SQLite fixture and recording storage/queue
doubles. They do not require PostgreSQL, Redis, Qdrant, MinIO, Docker, or model
downloads.

## 7. Commands executed and actual results

| Command/check | Actual result |
|---|---|
| `C:\Users\tvabi\.local\bin\python3.14.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider -k 'read_upload_with_limit or upload_pdf or upload_invalid_pdf'` | **Could not run:** `No module named pytest` in the configured Python 3.14 environment. No packages were installed. |
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider -k 'read_upload_with_limit or upload_pdf or upload_invalid_pdf'` | **Passed:** 5 passed, 9 deselected. Two existing dependency warnings. |
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider` | **Passed:** 14 passed. Two existing dependency warnings (Starlette multipart deprecation and Pydantic `model_version` protected namespace warning). |
| `git diff --check` | **Passed.** Git emitted non-fatal LF/CRLF working-copy warnings for the two modified Python files. |
| `git status --short` | Only the upload route and backend harness test are modified; the requested report is under the existing ignored `report\build` directory. |

No services were started, no migrations were run, and no packages were installed.

## 8. Known limitations

- The existing storage contract requires full bytes for valid files, so a
  permitted upload can still occupy up to the configured maximum in application
  memory. This change bounds that memory use to the configured limit rather
  than buffering an arbitrarily large upload.
- Starlette parses the multipart request before invoking this route and may
  spool its upload to a temporary file. This route's bound controls bytes read
  into the application buffer; it does not impose an upstream HTTP request-body
  limit or prevent the multipart parser from receiving/spooling the complete
  request.
- Docker/runtime behavior was not checked; it is not required for the focused
  in-memory tests.

## 9. API contract confirmation

The API contract did not change. Oversized PDF files continue to receive HTTP
400 with the same `detail` text used by existing PDF validation. Valid uploads
continue through the existing document service and return its existing
`DocumentOut` response.

## 10. Task status

**COMPLETE.** Bounded reading, size boundary behavior, early rejection before
storage/queue, and existing invalid-PDF behavior were implemented and verified
by the focused backend harness.

## 11. Recommended next task

Proceed to the approved roadmap's **document deletion reliability** task after
review and approval. It was not started as part of this task.
