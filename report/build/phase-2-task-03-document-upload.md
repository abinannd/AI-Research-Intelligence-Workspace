# Phase 2 - Task 03: Document Upload and Indexing UI

## Files changed

- `frontend/src/app/page.tsx` - Mounts the document panel for the selected workspace.
- `frontend/src/components/WorkspaceDocuments.tsx` - Implements upload, listing, status display, refresh, polling, and error/empty states.
- `frontend/src/lib/documentUpload.ts` - Shared client-side file validation and the 20 MiB limit.
- `frontend/tests/document-upload.test.mjs` - Focused tests for upload validation.
- `report/build/phase-2-task-03-document-upload.md` - This implementation report.

The working tree also contained a pre-existing modification to `infra/docker-compose.yml`. It was not changed as part of this task.

## API contracts used

- `GET /api/workspaces/{workspace_id}/documents` uses the existing authenticated API client and returns a workspace-scoped array of documents.
- `POST /api/workspaces/{workspace_id}/documents` uses the existing authenticated API client and `multipart/form-data` field `file`; FastAPI returns one document (default HTTP 200).
- Both responses use the existing `WorkspaceDocument` shape: `id`, `filename`, `status`, `page_count`, `error_message`, and `created_at`.
- Both routes require the existing authenticated user and the backend verifies workspace ownership.
- Backend PDF validation requires a `.pdf` filename, PDF signature/openable content, at least one page, no more than 80 pages, and no more than the configured 20 MiB default. The browser validates extension, non-empty file, and 20 MiB size; content and page-count validation remain server-side.
- The upload service commits the document with status `queued` and calls the ingestion queue. Actual background processing depends on queue configuration: the backend default is `noop`; `inline` runs the worker synchronously and `rq` enqueues it in Redis/RQ.
- Existing statuses are displayed using the existing status helpers: `queued`, `parsing`, `indexing`, `ready`, `failed`, and `ocr_needed`.

## Implementation summary

- Added a PDF selector, client-side extension/size/empty-file validation, and the existing authenticated upload client call.
- Added workspace-scoped initial listing, document status and error details, loading/error/retry states, and a useful empty state.
- Added an explicit refresh action. Automatic status refresh polls every four seconds only while a document is in an in-flight state and the page is visible; polling pauses during upload/manual refresh and stops when statuses become terminal.
- Shows upload-pending feedback, but not a percentage: the current `fetch` API client does not expose upload progress events.
- Added four dependency-free Node tests covering extension, empty-file, and exact size-boundary behavior.
- No backend, authentication, workspace API, or dependency changes were made.

## Commands executed and results

Commands were run from `frontend/` unless otherwise noted.

| Command | Result |
|---|---|
| `node --experimental-strip-types --test tests\document-upload.test.mjs` | Passed: 4 tests, 0 failures. Node emitted a non-fatal `MODULE_TYPELESS_PACKAGE_JSON` warning while loading the TypeScript helper. |
| `npm run lint` | Passed (exit code 0). |
| `npx tsc --noEmit --incremental false` | Passed (exit code 0). |
| `npm run build` | Passed (exit code 0); Next.js compiled, type-checked, generated static pages, and produced `/` and `/_not-found`. |
| `git diff --check` | Passed with no whitespace errors. Git emitted a line-ending warning for the pre-existing modified `infra/docker-compose.yml`. |
| `git check-ignore -v --no-index report/build/phase-2-task-03-document-upload.md` | No ignore rule matched; the report is not ignored. |

## Tests passed and failed

- Passed: all 4 focused upload-validation tests.
- Passed: frontend ESLint, standalone TypeScript check, and production build.
- Failed: none.
- No browser/e2e test runner is configured in the frontend package, so the rendered upload flow was not exercised in a browser.

## Known limitations

- Upload percentage progress is unavailable with the existing `fetch`-based API client; the UI shows an indeterminate upload state.
- The browser checks extension and file size only. PDF content integrity and the 80-page limit are validated by the backend after upload begins.
- With backend `queue_backend=noop` (the built-in default), the API accepts the file but no worker advances it beyond `queued`. Configure the intended queue backend to process documents.
- The Node test command reports a non-fatal module-type warning because the frontend package does not declare `"type": "module"`.

## Recommended next task

Implement the workspace Ask UI against the existing ask API and gate submissions on at least one document reaching `ready`, using the document statuses added here.
