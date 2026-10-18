# Phase 2 — Task 01: Basic Research Workspace UI

## 1. Objective

Replace the default Next.js starter page with a basic, responsive workspace
interface where an authenticated user can list, create, select, and return to
their selected research workspace.

## 2. Files inspected

- [`frontend/package.json`](../../frontend/package.json) — dependencies and
  available scripts; there is no test or dedicated typecheck script.
- [`frontend/src/app/page.tsx`](../../frontend/src/app/page.tsx) — original
  root route, which was the default Next.js starter screen.
- [`frontend/src/app/layout.tsx`](../../frontend/src/app/layout.tsx) — root
  layout and metadata.
- [`frontend/src/app/globals.css`](../../frontend/src/app/globals.css) —
  existing Tailwind/global style setup.
- [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) — typed
  authentication and workspace methods and API error behavior.
- [`frontend/src/lib/types.ts`](../../frontend/src/lib/types.ts) — `User`,
  `Workspace`, and API response types.
- [`frontend/src/lib/token.ts`](../../frontend/src/lib/token.ts) — existing
  local-storage access-token persistence.
- [`frontend/src/lib/utils.ts`](../../frontend/src/lib/utils.ts) — API error
  and date formatting helpers.
- [`frontend/next.config.ts`](../../frontend/next.config.ts) and
  [`frontend/postcss.config.mjs`](../../frontend/postcss.config.mjs) — build
  configuration relevant to production-build failures.
- [`frontend/eslint.config.mjs`](../../frontend/eslint.config.mjs) — lint
  file-scope configuration.
- [`frontend/AGENTS.md`](../../frontend/AGENTS.md) and the installed
  Next.js App Router
  [server/client component guide](../../frontend/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md)
  — project guidance for client-side interaction and browser APIs.
- [`backend/app/api/workspaces.py`](../../backend/app/api/workspaces.py) and
  [`backend/app/schemas.py`](../../backend/app/schemas.py) — verified
  workspace endpoints and request/response fields.

## 3. Existing frontend architecture

The frontend uses Next.js App Router, React, TypeScript, and Tailwind CSS. The
root route was still the generated starter page. The existing API client
already provided `api.listWorkspaces()` and `api.createWorkspace(name)`,
typed `Workspace` responses, `api.login()`/`api.signup()`, and bearer-token
storage. There was no frontend page or component using those auth/workspace
methods.

The root page is now a client component because the workspace screen requires
interactive forms, React state/effects, and browser local storage. Existing
dependencies and the API client were reused.

## 4. Files modified and why

- **Modified:** [`frontend/src/app/page.tsx`](../../frontend/src/app/page.tsx)
  — replaced the starter page with an existing-API-backed auth entry and
  workspace list/create/select screen.
- **Modified:** [`frontend/src/app/layout.tsx`](../../frontend/src/app/layout.tsx)
  — replaced generated starter metadata with the application title and
  description.
- **Created:** this report.

No API client, backend, schema, dependency, database, infrastructure, CI, or
`.gitignore` files were changed. No previous reports were overwritten.

## 5. Implemented functionality

- Uses the existing login and signup API methods and access-token persistence
  to make the existing auth mechanism usable from the root screen; no new
  authentication system was introduced.
- Loads and displays the authenticated user's workspaces from the real API.
- Shows workspace name and creation time.
- Provides a create form that trims and rejects an empty name, respects the
  backend's 200-character maximum, prevents duplicate submissions while
  pending, displays API errors, and selects a newly created workspace.
- Allows selection of a workspace, marks the selected item accessibly, and
  displays the selected workspace name.
- Persists the selected workspace ID in local storage and restores it only
  when it exists in the current user's returned workspace list.
- Includes a sign-out action that clears the existing token and selected ID.

## 6. API endpoints and contracts used

- `POST /api/auth/login` with `{ email, password }`, returning the existing
  token response.
- `POST /api/auth/signup` with `{ email, password }`, returning the existing
  token response.
- `GET /api/auth/me`, returning `{ id, email }` to restore a saved session.
- `GET /api/workspaces`, returning an array of workspaces with `id`, `name`,
  and `created_at`.
- `POST /api/workspaces` with `{ name }`, returning a workspace with `id`,
  `name`, and `created_at`.

Requests use the existing API client and its bearer-token behavior. No backend
contract was changed.

## 7. Loading, empty, and error-state behavior

- A session status message is shown while a saved token is checked.
- Workspace loading and refresh states are shown while the API request is in
  progress.
- An explicit empty state is shown when a successful list request returns no
  workspaces.
- Workspace load errors include a retry action; the Refresh button is also
  available.
- Sign-in, account creation, and workspace creation errors are displayed
  inline. Pending auth and create submissions disable their respective submit
  buttons.
- Network/API errors are caught and shown instead of leaving rejected
  promises unhandled.

## 8. Responsive behavior

The layout uses a centered maximum-width content area, a single-column layout
on narrow screens, and side-by-side create/list sections on desktop. Workspace
cards use one column on small screens and two columns when space permits.

## 9. Commands executed and actual results

| Command | Actual result |
|---|---|
| `Set-Location frontend; .\node_modules\.bin\tsc.cmd --noEmit --incremental false` | **Passed**, exit code 0. |
| `Set-Location frontend; npm run lint -- src/app/page.tsx src/app/layout.tsx` | **Passed**, exit code 0; changed frontend files have no lint findings. |
| `Set-Location frontend; npm run lint` | **Failed**, exit code 1: 1,568 findings (7 errors, 1,561 warnings). Findings are in the existing minified `public/pdf.worker.min.mjs` and `scripts/copy-pdf-worker.cjs`, not the changed page/layout. The latter has two `@typescript-eslint/no-require-imports` errors; generated worker lint findings include `@typescript-eslint/no-this-alias` errors and numerous warnings. |
| `Set-Location frontend; npm run build` | **Failed**, exit code 1: Next.js 16 defaults to Turbopack, but the existing `next.config.ts` supplies a custom webpack config without Turbopack config. |
| `Set-Location frontend; npm run build -- --webpack` | **Failed**, exit code 1: webpack mode reached PostCSS setup but could not resolve `@tailwindcss/postcss`. |
| `Set-Location frontend; npm ls @tailwindcss/postcss --depth=0` | **Confirmed missing:** package is not installed in the current frontend dependency tree. It is also absent from `package.json` and `package-lock.json`, while `postcss.config.mjs` references it. No packages were installed. |
| `git diff --check` | **Passed**, exit code 0; only non-fatal LF/CRLF working-copy warnings were emitted for the changed source files. |

The package manifest has no frontend test script, and no frontend test files
were found. No backend services were started.

## 10. `git diff --check`

**Passed.** No whitespace errors were reported. Git emitted non-fatal
line-ending warnings for changed frontend source files.

## 11. Git-ignore and report-visibility verification

After creating this report:

- `git check-ignore -v report/build/phase-2-task-01-workspace-ui.md` returned
  no matching rule (exit code 1, Git's expected result for a non-ignored path).
- `git status --short --untracked-files=all` showed
  `?? report/build/phase-2-task-01-workspace-ui.md` along with the modified
  frontend source files.
- No ignore rule was added or changed to hide `report/build/` reports.

## 12. Known limitations

- The UI has not been exercised against a running backend in this task.
- The production build is blocked by pre-existing project setup problems:
  Next.js 16's default Turbopack mode conflicts with the existing webpack
  config, and explicit webpack mode cannot load the PostCSS plugin referenced
  by the current PostCSS config. Dependencies/configuration were not changed
  because they are outside this task's scope.
- The repository-wide lint command fails on the existing generated PDF worker
  and worker-copy script. The changed page and layout pass targeted lint.
- Workspace selection is persisted locally and displayed; no workspace
  detail/document route exists yet, as document management is outside scope.

## 13. Task status

**BLOCKED.** The UI implementation and targeted TypeScript/lint checks are
complete, but production-build verification cannot succeed with the current
Next.js/PostCSS setup. The broad lint script also remains failing on existing
out-of-scope files. No unrelated tooling or feature changes were made.

## 14. Recommended next task

Review the workspace screen, then separately address the frontend's existing
Next.js build-mode/PostCSS dependency configuration and lint file exclusions
before attempting production-build acceptance. Do not begin those fixes until
the current task is reviewed.
