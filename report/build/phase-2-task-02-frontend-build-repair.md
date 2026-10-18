# Phase 2 — Task 02: Frontend Build Configuration Repair

## 1. Objective

Repair the confirmed Next.js build-mode mismatch and repository-wide lint
failures caused by generated/vendored PDF worker artifacts, while verifying
whether the missing Tailwind PostCSS plugin can be addressed without
unauthorized dependency installation.

## 2. Files inspected

- [`frontend/package.json`](../../frontend/package.json) and
  [`frontend/package-lock.json`](../../frontend/package-lock.json) — declared
  dependencies, scripts, and exact locked versions.
- [`frontend/next.config.ts`](../../frontend/next.config.ts) — standalone
  output and custom Webpack configuration.
- [`frontend/postcss.config.mjs`](../../frontend/postcss.config.mjs) —
  configured Tailwind PostCSS plugin.
- [`frontend/eslint.config.mjs`](../../frontend/eslint.config.mjs) — current
  global ignored paths.
- [`frontend/tsconfig.json`](../../frontend/tsconfig.json) — strict
  TypeScript settings and generated Next.js type inputs.
- [`frontend/src/app/globals.css`](../../frontend/src/app/globals.css) and
  [`frontend/src/app/layout.tsx`](../../frontend/src/app/layout.tsx) —
  existing Tailwind v4 CSS entry and application layout.
- [`frontend/scripts/copy-pdf-worker.cjs`](../../frontend/scripts/copy-pdf-worker.cjs)
  and [`frontend/public/pdf.worker.min.mjs`](../../frontend/public/pdf.worker.min.mjs)
  — CommonJS worker-copy helper and generated/minified vendored worker.
- [`frontend/AGENTS.md`](../../frontend/AGENTS.md) — installed Next.js
  guidance requirement.
- Installed Next.js App Router client/server and bundler documentation under
  `frontend/node_modules/next/dist/docs`.
- Frontend source references to PDF.js/canvas and Git history for
  [`frontend/next.config.ts`](../../frontend/next.config.ts).

## 3. Confirmed root causes

1. Installed and locked Next.js is **16.4.2**. Next.js 16 defaults to
   Turbopack for builds. The existing `next.config.ts` has a custom Webpack
   callback, which caused the default `npm run build` to fail with the
   Turbopack/Webpack configuration conflict.
2. Installed and locked `tailwindcss` and `@tailwindcss/turbopack` are both
   **4.3.3**. `postcss.config.mjs` loads `@tailwindcss/postcss`, but that
   package is absent from `package.json`, `package-lock.json`, and
   `node_modules`. The explicit Webpack build therefore fails resolving it.
   Public npm metadata for `@tailwindcss/postcss@4.3.3` identifies the same
   exact Tailwind dependency version (`tailwindcss: 4.3.3`).
3. The ESLint config overrode Next's default ignores with a short list that
   did not include the checked-in generated PDF worker or the standalone
   CommonJS worker-copy script. The generated minified file produced
   thousands of findings, and the `.cjs` helper produced CommonJS import
   errors.
4. The Webpack callback, present in the initial repository commit, adds
   `canvas: false` to the resolver. The current frontend source has no direct
   `pdfjs-dist` or `canvas` imports, so its current runtime necessity cannot
   be verified from active source usage. It is retained unchanged; selecting
   Webpack preserves its existing effect.

## 4. Files modified and reason for each

- **Modified:** [`frontend/package.json`](../../frontend/package.json) —
  changed only the build script to run `next build --webpack`, matching
  Next.js 16's documented opt-in for an application with a custom Webpack
  config.
- **Modified:** [`frontend/eslint.config.mjs`](../../frontend/eslint.config.mjs)
  — added exact global-ignore entries for the generated PDF worker and its
  CommonJS copy helper. Application source files remain linted.
- **Modified:** [`frontend/package.json`](../../frontend/package.json) —
  added exact dev dependency `@tailwindcss/postcss@4.3.3`; the earlier
  Webpack build-script change remains.
- **Modified:** [`frontend/package-lock.json`](../../frontend/package-lock.json)
  — recorded the exact plugin package and root dev dependency without
  upgrading other packages.
- **Created:** this report.

No UI, backend, API, or feature code was modified. The pre-existing Task 01
workspace UI changes were left intact.

## 5. Exact relevant dependency versions

- `next`: **16.4.2** (installed and locked).
- `tailwindcss`: **4.3.3** (installed and locked).
- `@tailwindcss/turbopack`: **4.3.3** (installed and locked).
- `@tailwindcss/postcss`: **4.3.3**, installed and declared as an exact
  devDependency. Its metadata depends on `tailwindcss` exactly at `4.3.3`.

## 6. Configuration changes and compatibility

- `npm run build` now explicitly selects Webpack. This uses the existing
  custom Webpack callback and avoids adding a second Turbopack configuration.
  Installed Next.js documentation describes `next build --webpack` for this
  case.
- ESLint now ignores only `public/pdf.worker.min.mjs` and
  `scripts/copy-pdf-worker.cjs`, both artifacts/helpers outside application
  TypeScript source. No global lint rules or TypeScript checks were disabled.
- `postcss.config.mjs` and Tailwind CSS source were not bypassed or rewritten.
  The plugin was added at the version matching the existing Tailwind install.

## 7. Commands executed and actual results

| Command | Actual result |
|---|---|
| `Set-Location frontend; node -p "JSON.stringify({next:require('next/package.json').version,tailwind:require('tailwindcss/package.json').version})"` | **Confirmed:** Next.js 16.4.2 and Tailwind CSS 4.3.3. |
| `Set-Location frontend; npm ls next tailwindcss @tailwindcss/turbopack @tailwindcss/postcss --depth=0` | **Confirmed:** Next.js 16.4.2, Tailwind 4.3.3, Turbopack 4.3.3 installed; PostCSS plugin absent. Exit code 1 because requested plugin is missing. |
| `npm view @tailwindcss/postcss@4.3.3 version peerDependencies dependencies engines --json` | **Confirmed:** version 4.3.3; dependency metadata lists `tailwindcss: 4.3.3` (plus matching `@tailwindcss/node` and `@tailwindcss/oxide` 4.3.3). |
| `Set-Location frontend; npm run lint -- src/app/page.tsx src/app/layout.tsx` | **Passed**, exit code 0. |
| `Set-Location frontend; npm run lint` | **Passed**, exit code 0 after the targeted worker ignores. |
| `Set-Location frontend; .\node_modules\.bin\tsc.cmd --noEmit --incremental false` | First run passed before the build attempt. A rerun concurrent with Next build cleanup transiently failed because generated `.next/types/app/layout.ts` and `page.ts` were missing. A subsequent rerun after the build process completed **passed**, exit code 0. |
| `Set-Location frontend; npm run build` before the build-script edit | **Failed**, exit code 1: Next.js 16 Turbopack default conflicted with the existing custom Webpack config. |
| `Set-Location frontend; npm run build -- --webpack` before the build-script edit | **Failed**, exit code 1: `Cannot find module '@tailwindcss/postcss'`. |
| `Set-Location frontend; npm run build` after the build-script edit | **Failed**, exit code 1: Webpack was selected successfully, then the build failed because `@tailwindcss/postcss` is missing. No installation was attempted. |
| `Set-Location frontend; npm ls @tailwindcss/postcss --depth=0` | **Confirmed absent**, exit code 1. |
| `Set-Location frontend; npm install --save-dev --save-exact @tailwindcss/postcss@4.3.3` | **Succeeded**, exit code 0: added 1 package; audited 370 packages. npm reported 5 high-severity vulnerabilities; no audit fix or unrelated upgrade was run. |
| `Set-Location frontend; npm ls @tailwindcss/postcss tailwindcss --depth=0` | **Passed**, exit code 0: `@tailwindcss/postcss@4.3.3`, `tailwindcss@4.3.3`. |
| `Set-Location frontend; .\node_modules\.bin\tsc.cmd --noEmit --incremental false` after installation | **Passed**, exit code 0. |
| `Set-Location frontend; npm run lint` after installation | **Passed**, exit code 0. |
| `Set-Location frontend; npm run build` after installation | **Passed**, exit code 0: Webpack compilation, TypeScript, static page generation, and build trace collection completed; routes `/` and `/_not-found` were generated. |
| `git diff --check` | **Passed**, exit code 0. Git emitted only non-fatal LF/CRLF working-copy warnings. |

Only the authorized package was installed. No backend service was started, no
migrations were run, and no commit or push were performed.

## 8. TypeScript, lint, and production-build outcomes

- TypeScript check: **passed** after the build process completed.
- Targeted lint of the workspace page and layout: **passed**.
- Full frontend lint: **passed** after excluding only the generated worker and
  its CommonJS copy helper.
- Production build: **passed** with the configured Webpack mode after adding
  the exact compatible Tailwind PostCSS plugin.

## 9. `git diff --check`

**Passed.** No whitespace errors; only non-fatal line-ending warnings were
reported.

## 10. Report tracking and Git-ignore verification

After creating the report:

- `git check-ignore -v report/build/phase-2-task-02-frontend-build-repair.md`
  returned **no matching rule**, exit code 1 (expected for a non-ignored file).
- `git status --short --untracked-files=all` included:
  ```text
   M frontend/eslint.config.mjs
   M frontend/package-lock.json
   M frontend/package.json
  ?? report/build/phase-2-task-02-frontend-build-repair.md
  ```
  No changes to the Task 01 UI files appeared in the final status.
- No ignore rule was added to hide reports in `report/build/`.

## 11. Known limitations and unresolved issues

- The custom Webpack alias is retained, but current frontend application source
  does not import PDF.js or canvas directly, so the alias's present necessity
  is unverified.
- No frontend browser/runtime test was executed; no such test script exists in
  the frontend package manifest.
- npm reported 5 high-severity dependency advisories during installation. No
  audit remediation was performed because it could upgrade packages outside
  the authorized scope.

## 12. Task status

**COMPLETE.** The matching PostCSS plugin was installed at the authorized
version, the production build succeeded, TypeScript passed, and repository-wide
lint passed.

## 13. Recommended next task

Review and accept the frontend build repair. Track the npm advisories
separately; no dependency upgrades beyond the explicitly authorized plugin
were made.
