# Phase 3 - Task 01: MVP Readiness Review

**Review date:** 2026-10-18  
**Scope:** Read-only assessment; this task changed no application source, package manifest, environment file, or runtime configuration. The only new file is this report.

## Executive assessment

**Readiness: conditionally ready for local workspace management and PDF ingestion; not yet verified as a complete research MVP for normal use.**

The documented Compose path is configured for PostgreSQL, Redis/RQ, MinIO, Qdrant, Sentence Transformers, and Hugging Face inference. Prior reports contain a successful live ingestion run, including a `ready` status, one database chunk, and one matching Qdrant point. Authentication, workspace ownership, the upload UI, Ask UI, and PDF viewer also have implementation evidence and relevant automated tests.

However, the available live run did **not** complete the full Ask-to-citation journey. The Task 07 run recorded before this review completed signup, workspace creation, PDF upload, and worker indexing, but its real-model Ask call did not return a result; no query/citation record was present at the last observation. A prior attempt exceeded the 20-minute Playwright timeout using a larger CPU model. Thus real model response quality, citation production from retrieved evidence, and the full live browser journey remain unverified. The current dependency audit also reports five high-severity issues in the frontend ESLint dependency tree.

## Assessment by requested area

### 1. Workspace creation and authentication

**Implementation evidence:** [page.tsx](../../frontend/src/app/page.tsx) uses the existing signup/login and workspace API client calls. It restores a saved session using `/api/auth/me`, loads the authenticated user's workspaces, creates and selects a workspace, and clears the token on sign-out. [auth.py](../../backend/app/api/auth.py) uses authenticated routes and returns the existing token response. Passwords are hashed with bcrypt and bearer tokens are signed with HS256 in [security.py](../../backend/app/security.py).

**Verification evidence:** Phase 1 Task 04 reports authentication and workspace ownership tests. The latest recorded backend harness run during the preceding Task 07 work was `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider`: **22 passed, 2 warnings**. The test harness uses per-test in-memory SQLite and test doubles, not the live Compose database.

**Live evidence:** During the incomplete Task 07 browser attempt, signup and workspace creation returned HTTP 200 against its isolated API. This is partial journey evidence, not a completed acceptance test.

**Security/operational notes:** The browser stores the bearer token in local storage ([token.ts](../../frontend/src/lib/token.ts)); that makes script-injection/XSS prevention important. `hash_password` truncates encoded passwords to 72 bytes while the signup schema accepts up to 128 characters ([security.py](../../backend/app/security.py), [schemas.py](../../backend/app/schemas.py)). Also, [config.py](../../backend/app/config.py) has development defaults (including a development JWT secret); the local setup guide says to use Compose and not these direct-startup fallbacks.

### 2. PDF upload and document status

**Implementation evidence:** [WorkspaceDocuments.tsx](../../frontend/src/components/WorkspaceDocuments.tsx) uses the authenticated workspace-scoped API client, validates the `.pdf` extension, non-empty size, and 20 MiB browser limit, lists documents, displays status/error messages, and refreshes while documents are in flight. The backend enforces the actual PDF validity and configured limits; [pdf.py](../../backend/app/parsing/pdf.py) checks the PDF signature, parseability, non-empty page count, and page limit. The upload route reads at most the configured size plus one byte before rejecting an oversized upload ([documents.py](../../backend/app/api/documents.py)).

**Verification evidence:** The Task 03 report records four upload-validation tests, lint, TypeScript, and production build passing. Task 03.5 reports a live authenticated upload returning `queued` and status polling reaching `indexing` then `ready`. In the partial Task 07 run, the real upload endpoint returned HTTP 200 and the worker completed the uploaded test document.

**Limitations:** Browser upload feedback is indeterminate rather than percentage-based. Polling is every four seconds while statuses are in flight. Scanned or empty PDFs are marked `ocr_needed`; OCR is not implemented.

### 3. Indexing and storage configuration

**Configuration evidence:** [docker-compose.yml](../../infra/docker-compose.yml) configures PostgreSQL, Redis/RQ, MinIO/S3, Qdrant, `bge-small-en-v1.5` embeddings, and Hugging Face LLM inference. The worker and queue both use the `ingest` RQ queue ([queue.py](../../backend/app/documents/queue.py), [worker.py](../../workers/worker.py)). The documented configuration and service wiring are described in [infra/README.md](../../infra/README.md).

**Previously verified live:** Task 03.5 reports successful use of MinIO, Redis/RQ, Sentence Transformers, and Qdrant, with a completed worker job, one stored database chunk, and one matching vector point filtered by workspace and document IDs. It also records that the BGE model was downloaded and used.

**Current Task 07 partial evidence:** An isolated Compose project with a separate PostgreSQL volume, Redis service, MinIO bucket, and Qdrant collection was used. Its API and worker reported `MinioStorage`, `RedisRQQueue`, `QdrantVectorStore`, `SentenceTransformerEmbeddingService`, and `HuggingFaceLLMService`; Redis `PING` succeeded, and API/Qdrant/MinIO health probes returned HTTP 200. The isolated worker logged a successful ingestion job for the new test upload. Existing shared Compose services and their volumes were not reset or stopped.

### 4. Ask endpoint and citation rendering

**Implementation evidence:** [ask.py](../../backend/app/api/ask.py) requires authentication, verifies workspace ownership, requires at least one ready document, scopes retrieval to the workspace and optional ready document IDs, and serializes answer, claims, and citations. [qa.py](../../backend/app/citations/qa.py) retrieves chunks, validates model output against those retrieved chunks, and only creates citations from retrieved chunk metadata. [WorkspaceAsk.tsx](../../frontend/src/components/WorkspaceAsk.tsx) gates the UI until a document is ready and renders the returned answer, claims, citation index, filename, page, and quote.

**Test evidence:** Task 04 reports three Ask-payload tests and seven combined frontend tests passing; its Ask endpoint was not called against a live backend. Task 06's three passing Playwright tests mock auth, workspaces, document listing, and Ask responses, so they test UI behavior rather than backend inference or live citation generation.

**Outstanding verification:** The Task 07 live journey reached the Ask request with a real indexed document and real model backend, but no successful Ask response or citation was recorded. The prior attempt using the configured-size CPU model timed out at the Playwright test's 20-minute limit while waiting for the Ask POST response. A retry selected `HuggingFaceTB/SmolLM2-135M-Instruct` without mocking the response; signup, workspace creation, upload, and successful indexing were observed, but at the last inspection the model weights were still downloading, the API had not logged a completed Ask request, and the isolated database showed zero queries and citations. The retry was interrupted before completion when the review request arrived. Treat the end-to-end Ask result as **unverified**, not passed or failed on answer quality.

### 5. Citation-to-PDF navigation

**Implementation evidence:** [WorkspaceAsk.tsx](../../frontend/src/components/WorkspaceAsk.tsx) fetches PDFs with the existing authenticated, workspace-scoped `getDocumentFile` call. [WorkspacePdfViewer.tsx](../../frontend/src/components/WorkspacePdfViewer.tsx) renders the cited page with PDF.js and highlights matching quote text spans. A request sequence guard prevents an older PDF fetch from replacing a newer citation selection.

**Test evidence:** Task 05 reports 11 frontend tests, lint, TypeScript, and production build passing, but no browser viewer test in that task. Task 06 subsequently reports three Chromium browser tests passing for authenticated workspace/document URL and bearer header, page navigation, quote highlight, stale-response protection, and 404 handling. These use controlled mock API responses and an in-memory generated PDF; they verify browser UI behavior, not live backend citations.

### 6. Frontend/backend connectivity and ports

- The supported local setup is documented in [infra/README.md](../../infra/README.md): browser UI `http://localhost:3000`, API `http://localhost:8000`.
- Compose publishes API and frontend on loopback ports 8000 and 3000. The frontend Dockerfile passes `NEXT_PUBLIC_API_URL` as a build argument; [api.ts](../../frontend/src/lib/api.ts) falls back to `http://localhost:8000`.
- Compose passes internal service DNS names to the API/worker for PostgreSQL, Redis, MinIO, and Qdrant. The browser-facing API URL remains a host URL.
- CORS defaults to `http://localhost:3000`; using `127.0.0.1:3000` instead of the documented `localhost:3000` origin may fail cross-origin browser requests unless that origin is configured. This follows from configuration inspection; no separate browser CORS test was run in this review.
- During Task 07, the standard service ports were already occupied by the existing Compose services and another listener on 8000/3000. The isolated test stack was configured on alternate ports 15432, 16379, 16333, 19000/19001, 18000, and 3100. The existing services were not stopped.

### 7. npm audit and dependency concerns

**Command run for this review:** `Push-Location frontend; npm audit --json` (JSON was summarized without changing the lockfile), followed by `npm audit` and `npm ls eslint-config-next @next/eslint-plugin-next fast-glob braces micromatch --all`.

**Actual result:** `npm audit` exited 1 and reported **5 high, 0 critical, 0 moderate, 0 low**. The dependency path is:

`eslint-config-next@16.4.2` → `@next/eslint-plugin-next@16.4.2` → `fast-glob@3.3.1` → `micromatch@4.0.8` → `braces@3.0.3`.

The reported advisory is [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm): `braces` is vulnerable to stack-exhaustion denial of service through deeply nested patterns. Audit marks the chain high severity. It is in the lint/configuration dependency chain; it is not shown as a direct application runtime dependency in `package.json`.

**Available fix according to npm:** `npm audit fix --force` would install `eslint-config-next@14.2.35`, a breaking major-version downgrade from the installed Next.js/ESLint config 16.4.2. Do not apply that remediation blindly. No audit fix, install, or dependency change was made during this review. The safe next step is to identify a patched dependency resolution compatible with the installed Next 16 toolchain, then rerun lint/build and audit.

### 8. Existing test/build evidence

No long-running test or build was rerun for this review. Prior recorded evidence:

| Evidence source | Recorded result | Scope/caveat |
|---|---|---|
| Phase 1 Task 04 backend report and latest preceding Task 07 run | Backend harness **22 passed, 2 warnings** | In-memory SQLite/test doubles; does not establish live service behavior by itself. |
| Phase 2 Task 03 upload report | 4 upload tests, lint, TypeScript, production build passed | Frontend validation/build, not live ingestion. |
| Phase 2 Task 03.5 ingestion report | Live upload → `ready`; one chunk and one Qdrant point | Verified ingestion only, not Ask or PDF viewer journey. |
| Phase 2 Task 04 Ask report | 3 Ask-payload tests; lint, TypeScript, build passed | Ask API was not live-tested in that task. |
| Phase 2 Task 05 PDF navigation report | 11 frontend tests; lint, TypeScript, build passed | Did not exercise PDF rendering in browser at that time. |
| Phase 2 Task 06 browser report | 3 Playwright tests passed; frontend tests/lint/TypeScript/build passed | Auth/workspace/document/Ask API responses are mocks. |
| Task 07 partial work observed before this review | Browser login/signup and workspace creation succeeded; upload accepted; worker job reached successful completion and document `ready` | Real Ask did not produce a recorded response; full journey did not pass. |
| `npm audit` during this review | 5 high findings | Current audit command; no remediation run. |

Earlier reports identified Node `MODULE_TYPELESS_PACKAGE_JSON` warnings in Node unit tests and backend Starlette/Pydantic warnings. No evidence in the reports establishes these warnings as runtime blockers.

## Outstanding blockers and risks

1. **Full live journey is incomplete.** A live answer and citation from the configured model have not been verified end-to-end. The first CPU-model attempt exceeded 20 minutes; the smaller-model retry did not finish before interruption.
2. **Model latency/first-run cost is material.** Compose uses CPU Hugging Face inference and shared model-cache storage. Task 03.5 already reported a roughly 1 minute 15 second first BGE ingestion; Task 07's separate setup incurred model downloads and its Ask did not finish in the test window. Normal local use may be very slow on machines with limited memory/CPU.
3. **Five high-severity npm audit findings remain.** The automatic npm fix is a breaking downgrade and must not be applied without compatibility review.
4. **Direct-start defaults are unsuitable for normal use.** Without the documented `.env`/Compose configuration, backend defaults include a development JWT key, SQLite, in-memory adapters, no-op queue, hash embeddings, and stub LLM. The README explicitly warns against this fallback.
5. **Authentication hardening merits follow-up.** The bearer token is in local storage; password handling truncates at bcrypt's 72-byte input boundary. Rate limiting and production-grade browser security controls were not assessed by the existing reports.
6. **Host-name consistency matters.** The documented `localhost` UI/API pair matches CORS defaults; changing to `127.0.0.1` or another hostname is not equivalent for browser origin checks.

## Three highest-priority next actions

1. **Complete a bounded live Ask-to-citation test.** Use the already isolated database, queue, bucket, and vector collection; keep auth, upload, indexing, retrieval, and Ask responses real. Ensure the chosen model has completed download before starting the test and set a realistic, measured timeout. Record whether it returns a grounded answer/citation and whether the viewer loads the cited file/page/highlight. Do not reuse or delete the earlier ingestion verification data.
2. **Resolve the `braces` advisory compatibly with Next 16.** Identify a patched version/resolution for the ESLint dependency chain that preserves compatibility; avoid `npm audit fix --force` as currently proposed. Review the diff, then run the frontend audit, lint, TypeScript check, and production build.
3. **Make the supported local path explicit and robust.** Ensure developers use Compose with the required `.env` and the documented `localhost` hostnames; consider a separate approved hardening task for failing closed on unsafe runtime defaults, token storage/XSS protections, and the bcrypt 72-byte password behavior.

## Commands and checks performed for this review

| Command/check | Result |
|---|---|
| Read Phase 1 and Phase 2 reports under `report/build/` | Reviewed reports for runtime configuration, backend tests, upload limits/deletion, workspace UI, frontend build repair, upload/indexing, live ingestion, Ask UI, citation navigation, and mocked citation browser verification. |
| Inspected backend/frontend source and Compose configuration | Read current auth, workspace, document, Ask, retrieval, model, storage, queue, viewer, API client, Dockerfile, Compose and local runtime documentation; no files modified. |
| `npm audit --json` | Exit 1; 5 high findings. Parsed only dependency names, severity, dependency paths and fix availability. |
| `npm audit` | Exit 1; disclosed GHSA-vfj7-8cjw-p6xm in `braces`; proposed `npm audit fix --force` and a breaking `eslint-config-next@14.2.35` downgrade. |
| `npm ls eslint-config-next @next/eslint-plugin-next fast-glob braces micromatch --all` | Confirmed the installed dependency path and versions shown above. |
| `git diff --check` | Passed; no whitespace errors. Git emitted non-fatal LF/CRLF working-copy warnings for existing Task 07 modifications. |
| `git status --short --untracked-files=all` | Final status is recorded below; pre-existing Task 07 work was preserved. |
| `git check-ignore -v --no-index report/build/phase-3-task-01-mvp-readiness-review.md` | No ignore rule matched; this report is not ignored. |

No tests, builds, services, migrations, installs, audit fixes, or environment reads were performed as part of this review. Live Task 07 observations above come from the already-running prior work and are explicitly marked incomplete.

## Final Git status

At the final check, the working tree showed the Task 07 in-progress files plus this report:

```text
 M frontend/package.json
 M frontend/tsconfig.json
?? frontend/e2e/mvp-journey.integration.spec.ts
?? infra/docker-compose.task07-isolated.yml
?? report/build/phase-3-task-01-mvp-readiness-review.md
```

No changes from the Task 07 integration attempt were removed or overwritten. No commit or push was performed.
