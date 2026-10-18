# Phase 2 - Task 06: Citation Browser Verification

## Outcome

Added and ran a focused Playwright browser suite for citation-to-PDF navigation. All three browser tests passed. Test responses and a two-page PDF are generated in-memory; no backend, `.env`, or persistent test data was changed.

## Files changed

- `frontend/package.json` and `frontend/package-lock.json` - Added `@playwright/test` and the `test:e2e` script.
- `frontend/playwright.config.ts` - Configured Chromium, the isolated Next.js test server, and test artifact output.
- `frontend/e2e/citation-pdf.spec.ts` - Added the browser coverage and generated sample PDF fixture.
- `frontend/next.config.ts` - Uses a separate `.next-playwright` output directory only for the Playwright server, preventing collisions with the existing development server.
- `frontend/.gitignore` and `frontend/eslint.config.mjs` - Excluded generated Playwright output from Git and lint.
- `report/build/phase-2-task-06-citation-browser-verification.md` - This report.

## Contracts and behavior verified

- Used the existing `GET /api/workspaces/{workspace_id}/documents/{document_id}/file` route through the app's `api.getDocumentFile(workspaceId, documentId)` call.
- Verified the file request used the expected workspace/document IDs and `Authorization: Bearer browser-test-token`.
- Mocked authentication, workspace, ready-document listing, and Ask responses through Playwright route interception. No backend API or response shape was changed.
- Confirmed citation selection displays page 2 of the generated two-page PDF and highlights the quoted text.
- Delayed the first PDF response, selected a second citation, then released the earlier response; the viewer continued to show the second document, page, and highlight.
- Returned HTTP 404 for an unavailable PDF and confirmed the UI reports that the cited PDF is no longer available in the workspace.

## Commands executed and actual results

Commands ran from `frontend/` except where indicated.

| Command | Result |
|---|---|
| `npm install --save-dev @playwright/test` | Passed; added 3 packages and audited 373 packages. npm reported 5 high-severity vulnerabilities in the dependency tree; no audit fix was run. |
| `npx playwright install chromium` | Passed (exit code 0); downloaded Playwright Chromium / Chrome for Testing 156.0.8078.4. |
| `npm run test:e2e -- --workers=1` | Passed: 3 browser tests, 0 failures. |
| `node --experimental-strip-types --test tests\*.test.mjs` | Passed: 11 tests, 0 failures. Node emitted non-fatal `MODULE_TYPELESS_PACKAGE_JSON` warnings for existing TypeScript helper imports. |
| `npm run lint` | Passed (exit code 0). |
| `npx tsc --noEmit --incremental false` | Passed (exit code 0). |
| `$env:PLAYWRIGHT_TEST='1'; npm run build` | Passed (exit code 0); production build compiled, type-checked, generated static pages, and collected build traces in the isolated test output directory. |
| `git diff --check` | Passed with no whitespace errors. |
| `git check-ignore -v --no-index report/build/phase-2-task-06-citation-browser-verification.md` | No ignore rule matched; the report is not ignored. |
| `git status --short --untracked-files=all` | Inspected; final entries are listed in the task response. |

### Resolved validation issues

- Initial Playwright startup collided with an already-running Next dev server. The test config now uses a dedicated port and `.next-playwright` directory; the pre-existing server was not stopped or modified.
- Next 16 selected Turbopack by default, which rejected the repository's custom webpack configuration. The Playwright server explicitly uses webpack.
- The first failure-state assertion matched both the PDF error and Next's route-announcer alert; it now scopes the assertion to the PDF error paragraph.
- ESLint initially traversed generated test output. The generated directories are now excluded from lint and Git.

## Tests passed and failed

- Passed: all 3 browser tests, all 11 existing frontend tests, ESLint, standalone TypeScript check, production build, and `git diff --check`.
- Failed: initial setup/selector/lint attempts described above; each was corrected and the final corresponding check passed.
- No browser test was skipped in the final run.

## Known limitations

- API responses are controlled mocks; this test verifies frontend request scoping and bearer-header construction but not a live authentication service or backend authorization.
- The generated PDF is an isolated minimal two-page fixture, not a user document.
- Coverage runs in Chromium only.
- npm reported 5 high-severity dependency advisories during installation; this task did not audit or remediate the dependency tree.

## Recommended next task

Run a broader browser-level workspace journey against an isolated test backend, including real upload/index status transitions and Ask responses, while continuing to preserve persistent data.
