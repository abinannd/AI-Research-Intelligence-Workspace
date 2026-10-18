# Phase 2 - Task 04: Workspace Ask UI

## Actual API contract inspected before implementation

- Endpoint: authenticated `POST /api/workspaces/{workspace_id}/ask`.
- Authentication: FastAPI `get_current_user` bearer dependency. The handler verifies workspace ownership before asking.
- Request (`AskIn`): `{ "question": string, "document_ids"?: string[] }`. `question` has 1-8000 character schema bounds. The route trims the question before invoking Q&A.
- Readiness and workspace constraints: the route returns HTTP 400 with `Ask is locked until at least one PDF is Ready` if the workspace has no `ready` documents. If `document_ids` is provided, every ID must belong to the workspace (otherwise HTTP 404) and be `ready` (otherwise HTTP 400).
- Response (`AskOut`): `id`, `question`, `abstained`, `abstain_reason`, `answer`, `claims`, `citations`, `latency_ms`, `model_version`, `prompt_version`, and `retrieval_version`.
- Claims contain `id`, `claim_text`, and `support_status`.
- Citations contain `id`, `claim_id`, `index`, nullable `document_id`, `filename`, `page_number`, nullable `chunk_id`, `quote`, and nullable `heading`. They are ordered by `index`; displayed references use the backend index as `[index]`.
- Existing `api.ask(workspaceId, payload)` sends this request through the authenticated API client; no endpoint or response fields were invented.

## Files changed

- `frontend/src/components/WorkspaceAsk.tsx` - Adds the question form, readiness gating, answer/claim/citation rendering, and loading/error states.
- `frontend/src/components/WorkspaceDocuments.tsx` - Supplies the selected workspace's ready document IDs and list loading/error state to the Ask UI.
- `frontend/src/app/page.tsx` - Connects the existing API unauthorized handler to session expiry UI.
- `frontend/src/lib/ask.ts` - Builds a trimmed, ready-document-scoped ask payload and rejects empty/unready submissions.
- `frontend/src/lib/types.ts` - Makes `Citation.document_id` nullable to match the backend schema.
- `frontend/tests/ask.test.mjs` - Adds focused request-payload validation tests.
- `report/build/phase-2-task-04-ask-ui.md` - This report.

Existing unrelated persistent artifacts, including `report/build/phase-2-task-03-5-ingestion-verification.md`, were preserved.

## Implementation summary

- Added an 8000-character question textarea and Ask action inside the current selected workspace document panel.
- The action remains disabled while document status is loading/refreshing, if readiness could not be loaded, when no document is `ready`, while a request is in flight, or when the question is blank.
- Requests include only ready document IDs from the currently selected workspace, preserving the backend workspace scope and readiness checks.
- Displays the returned answer, abstention reason when present, claims and support statuses, and citations as numbered `[index]` references with the actual filename, page, heading, and quote. Citations are not navigable; no PDF viewer was added.
- Reports API errors; 403 is shown as a workspace authorization error. On 401 the existing API client clears the token and the page returns to sign-in with a session-expired message.
- No backend, endpoint, dependency, `.env`, or persistent test data changes were made.

## Commands executed and actual results

Commands ran in PowerShell from the repository root; frontend commands changed into `frontend/` and returned to the root.

| Exact command | Result |
|---|---|
| `Push-Location frontend; node --experimental-strip-types --test tests\ask.test.mjs tests\document-upload.test.mjs; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; 7 tests passed, 0 failed. Node emitted non-fatal `MODULE_TYPELESS_PACKAGE_JSON` warnings for the `.ts` helper modules. |
| `Push-Location frontend; npm run lint; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; ESLint passed. |
| `Push-Location frontend; npx tsc --noEmit --incremental false; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; TypeScript check passed. |
| `Push-Location frontend; npm run build; $result = $LASTEXITCODE; Pop-Location; exit $result` | Exit code 0; Next.js production build compiled, type-checked, generated static pages, and produced `/` and `/_not-found`. |
| `git diff --check` | Passed (exit code 0); Git reported only a line-ending warning for `frontend/src/lib/types.ts`. |
| `git status --short --untracked-files=all` | Inspected after report creation; see final Git checks below. |
| `git check-ignore -v --no-index report/build/phase-2-task-04-ask-ui.md` | No ignore rule matched; report is not ignored. |

## Test outcomes

- Passed: 3 Ask payload tests (empty question blocked, no-ready-documents blocked, trimmed question and ready IDs included).
- Passed: 4 existing PDF upload validation tests.
- Failed: none.
- The frontend has no configured browser/e2e test runner, so no interactive browser test of the form or API response rendering was run.
- The Ask endpoint itself was inspected but not invoked against a live backend for this UI task.

## Limitations

- No PDF viewer integration or citation page navigation is included; citations are displayed as text, as scoped.
- Automatic status refresh continues to come from the existing workspace document component. While status cannot be confirmed or is refreshing, Ask is disabled.
- Authenticated API errors are rendered using the existing API error message formatter. HTTP 401 returns to sign-in; HTTP 403 stays in the workspace and displays an authorization error.
- The existing Node test invocation emits a harmless module-type warning because the frontend package does not declare `"type": "module"`.

## Recommended next task

Implement citation-to-PDF navigation using the existing PDF viewer contract: select a citation, load its workspace-scoped PDF, jump to `page_number`, and highlight `quote`. Keep the existing Ask answer/citation schema as the source of truth.

## Final Git checks

- `git diff --check`: passed (exit code 0); Git emitted a line-ending warning for `frontend/src/lib/types.ts`, with no whitespace errors.
- `git status --short --untracked-files=all`: showed the six intended frontend source/test changes and two untracked reports: the preserved Task 03.5 report and this Task 04 report.
- `git check-ignore -v --no-index report/build/phase-2-task-04-ask-ui.md`: no ignore rule matched; report is not ignored.
- Report trailing-whitespace scan: no matches.
