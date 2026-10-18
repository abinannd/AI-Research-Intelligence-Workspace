# Phase 2 - Task 05: Citation-to-PDF Navigation

## Existing viewer and API contracts reused

- **Existing viewer:** Inspection of `frontend/src/components/` and `frontend/src/app/` found no PDF viewer component or PDF display route. The existing dependency is `pdfjs-dist` (`^6.4.299`), and `frontend/public/pdf.worker.min.mjs` is already present. The viewer added here uses that dependency and worker; no new package was added.
- **PDF retrieval:** `api.getDocumentFile(workspaceId, documentId): Promise<Blob>` in `frontend/src/lib/api.ts` sends the existing bearer token to `GET /api/workspaces/{workspace_id}/documents/{document_id}/file`. The backend route requires `get_current_user`, calls `get_owned_document(db, user, workspace_id, document_id)`, and returns the stored bytes as `application/pdf`. Missing document/file behavior is HTTP 404.
- **Citation shape:** The backend `CitationOut` includes `index`, `filename`, 1-indexed `page_number`, `quote`, nullable `document_id`, nullable `chunk_id`, nullable `heading`, and claim/citation identifiers. A citation is selectable only when its `document_id` is non-null and `page_number` is a positive integer.
- **Smallest implementation:** Keep the current Ask UI and API unchanged. Turn valid citations into selectors, fetch the workspace-scoped Blob through `api.getDocumentFile`, and render the requested page and quote in an inline PDF.js viewer beneath the answer. Use PDF.js text content to highlight text spans when the normalized quote matches; otherwise still show the cited page and report that the quote could not be located.

## Files changed

- `frontend/src/components/WorkspaceAsk.tsx` - Adds citation selection, PDF loading/error states, and viewer integration.
- `frontend/src/components/WorkspacePdfViewer.tsx` - New inline PDF.js page renderer with page controls and text-layer quote highlighting.
- `frontend/src/components/WorkspacePdfViewer.module.css` - Minimal page/text-layer positioning and highlight styling.
- `frontend/src/lib/citationNavigation.ts` - Resolves citation targets and matching text-layer spans.
- `frontend/tests/citation-navigation.test.mjs` - Focused navigation/quote matching tests.
- `report/build/phase-2-task-05-citation-pdf-navigation.md` - This report.

The existing Ask UI and types from Task 04 remain in place. The previously untracked Task 03.5 report was preserved and not modified. No backend, API, dependency, `.env`, or persistent test data changes were made.

## Implementation summary

- Citation cards with valid document IDs/pages are keyboard-accessible buttons. Selecting one uses that citation's document ID in the current workspace's authenticated file request.
- Repeated citations for the already loaded PDF reuse its Blob; switching documents fetches the requested workspace-scoped file. A request sequence guard prevents a stale slower fetch from replacing a newer selection.
- The viewer opens inline, scrolls into view, loads PDF.js dynamically, displays the citation's 1-indexed page, and provides previous/next page controls.
- Quote matching is case-insensitive and whitespace-normalized across PDF.js text items. Matching text items receive a visible highlight. If the quote is absent from page text, the cited page remains visible with a useful notice.
- Null document IDs and invalid pages are non-selectable and explain why the PDF cannot open. API 401/403/404 and PDF load/render errors are surfaced. The API client's existing 401 handling clears the token and invokes the session-expired sign-in handler.
- No new dependency or endpoint was introduced.

## Commands executed and actual results

Commands ran in PowerShell from the repository root; frontend commands changed into `frontend/` and returned to the root.

| Exact command | Actual result |
|---|---|
| `Push-Location frontend; node --experimental-strip-types --test tests\citation-navigation.test.mjs tests\ask.test.mjs tests\document-upload.test.mjs; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; 11 tests passed, 0 failed: 4 citation-navigation tests, 3 Ask tests, and 4 upload tests. Node emitted non-fatal `MODULE_TYPELESS_PACKAGE_JSON` warnings for TypeScript helper modules. |
| `Push-Location frontend; npm run lint; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; ESLint passed. An earlier lint attempt failed on state resets inside effects in the new viewer; these were corrected, and the final lint passed. |
| `Push-Location frontend; npx tsc --noEmit --incremental false; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; TypeScript passed. An earlier check found nullable PDF.js captures/types; the viewer was adjusted to use narrowed function parameters and the final check passed. |
| `Push-Location frontend; npm run build; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; Next.js production build compiled, type-checked, generated static pages, and produced `/` and `/_not-found`. |
| `git diff --check` | Exit code 0; no whitespace errors. |
| `git check-ignore -v --no-index report/build/phase-2-task-05-citation-pdf-navigation.md` | No ignore rule matched; report is not ignored. |
| `git status --short --untracked-files=all` | Inspected after the report was written; final status is recorded below. |

## Tests passed and failed

- Passed: 4 citation target/text matching tests, 3 Ask payload tests, and 4 upload validation tests.
- Passed: frontend lint, standalone TypeScript check, production build, and `git diff --check`.
- Failed final checks: none. Earlier lint/type-check attempts failed while the new PDF.js viewer was being developed; causes and successful reruns are recorded in the command table.
- No browser/e2e runner is configured in the frontend package. PDF.js page rendering was type-checked and production-built, but not interactively exercised in a browser in this task.

## Known limitations

- Text highlighting marks the complete PDF.js text spans intersecting the normalized quote, rather than drawing word-level rectangles. Highlighting may not match if extracted PDF text differs substantially from the citation quote, in which case the page is still displayed with a mismatch notice.
- Scanned/image-only pages have no selectable text layer, so quote highlighting cannot work there.
- The viewer displays one page at a time with previous/next controls; it does not implement a full document thumbnail/search/zoom interface.
- A browser/e2e verification of actual canvas rendering and highlighted text remains outstanding.
- Node test runs report the existing non-fatal module-type warning; no package manifest change was made.

## Recommended next task

Add a focused browser/e2e test for the citation journey using an isolated sample PDF: select a citation, confirm the authenticated file request, verify the displayed page, and assert that matching quote text is highlighted. Keep this scoped to the existing viewer and avoid changing persistent service data.

## Final Git checks

- `git diff --check`: passed (exit code 0).
- `git status --short --untracked-files=all`: reported `M frontend/src/components/WorkspaceAsk.tsx`; untracked `frontend/src/components/WorkspacePdfViewer.module.css`, `frontend/src/components/WorkspacePdfViewer.tsx`, `frontend/src/lib/citationNavigation.ts`, `frontend/tests/citation-navigation.test.mjs`, and this report.
- `git check-ignore -v --no-index report/build/phase-2-task-05-citation-pdf-navigation.md`: no ignore rule matched; report is not ignored.
- Report trailing-whitespace scan: no matches.
