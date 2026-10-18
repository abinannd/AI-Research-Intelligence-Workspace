# Phase 1 — Task 01: Secure Local Runtime Configuration

**Project:** AI Research Intelligence Workspace | **Date:** 2026-10-18
**Scope:** Local configuration only. No services were started and no application logic, schema, or API contract was changed.

## 1. Task objective

Establish a safe, reproducible local runtime configuration for the existing
Docker Compose architecture, keep local secrets out of Git, document host and
Compose configuration, and verify consistency using non-destructive checks.

## 2. Files inspected

- [`.gitignore`](../../.gitignore)
- [`.env.example`](../../.env.example)
- [`backend/app/config.py`](../../backend/app/config.py)
- [`infra/docker-compose.yml`](../../infra/docker-compose.yml)
- [`backend/Dockerfile`](../../backend/Dockerfile)
- [`workers/Dockerfile`](../../workers/Dockerfile)
- Existing configuration-related documentation: [`report/18.10.2026.md`](../18.10.2026.md)

The root ignore rule excludes `.env`; it was not tracked. A root `.env` did not
exist before this task.

## 3. Files created or modified

- **Created:** root `.env` with local-only, independently generated credentials.
  Its contents are ignored by Git and are intentionally not reproduced here.
- **Created:** [`infra/README.md`](../../infra/README.md) with setup instructions,
  startup commands, URL/override behavior, and environment variable purposes.
- **Created:** this report.
- **Modified:** [`.env.example`](../../.env.example), replacing weak sample
  credentials with empty secret fields that must be filled.
- **Modified:** [`infra/docker-compose.yml`](../../infra/docker-compose.yml),
  requiring secret values rather than silently using weak fallbacks, mapping
  MinIO app credentials to the MinIO root credentials, and binding published
  ports to loopback.
- **Not modified:** application code, including `backend/app/config.py`, both
  Dockerfiles, the database schema, and API routes.

## 4. Configuration decisions

1. The supported local Compose path is to run from the repository root and
   explicitly supply `--env-file .env`. This avoids relying on Compose's
   project-directory lookup for a `.env` file located at the repository root
   while the Compose YAML is under `infra/`.
2. The local `.env` uses host-facing `localhost` service addresses for direct
   host execution. Compose supplies internal service DNS names such as
   `postgres`, `redis`, `qdrant`, and `minio` to containers instead.
3. Compose now errors when PostgreSQL credentials, JWT signing key, or MinIO
   root credentials are absent. The tracked template leaves secret fields
   blank; it contains no working secret defaults.
4. MinIO's application key and secret match its root username and password,
   respectively, because Compose currently configures no separate MinIO
   application user.
5. PostgreSQL, Redis, Qdrant, MinIO (including its console), API, and frontend
   published ports bind to `127.0.0.1` for local-only access.
6. Compose continues selecting the existing PostgreSQL, RQ, MinIO/S3, Qdrant,
   Sentence Transformers, and Hugging Face implementations. No implementation
   or architecture was replaced.
7. Direct backend startup loads `.env` relative to the current working
   directory. The documented host commands therefore run from the repository
   root. Running from `backend/` may not load the root `.env`.

## 5. Environment variables and purpose

| Variable(s) | Purpose and configuration behavior |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL user, password, and database. Compose requires these and uses them for the PostgreSQL container and API connection string. |
| `DATABASE_URL` | SQLAlchemy database URL for direct host startup (`localhost`). Compose constructs its own URL from the PostgreSQL variables and uses Compose DNS. |
| `REDIS_URL` | Redis/RQ endpoint for direct host startup (`localhost`). Compose uses the `redis` service address. |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | JWT signing secret and token lifetime. Compose passes them to API and worker. |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | MinIO root credentials. Compose requires both and maps them to the API/worker S3 access-key pair. |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` | S3-compatible object storage connection and bucket. Direct host values use `localhost`; Compose overrides endpoint with internal DNS. |
| `QDRANT_URL`, `QDRANT_COLLECTION` | Vector database endpoint and collection. Direct host values use `localhost`; Compose overrides endpoint with internal DNS. |
| `CORS_ORIGINS` | Browser origins allowed by the API. Defaults to the local frontend origin. |
| `MAX_PDF_BYTES`, `MAX_PDF_PAGES` | PDF limits: 20 MiB and 80 pages. |
| `STORAGE_BACKEND`, `QUEUE_BACKEND`, `VECTOR_BACKEND`, `EMBEDDING_BACKEND`, `LLM_BACKEND` | Select implementations for direct host startup. The local template selects `s3`, `rq`, `qdrant`, `st`, and `hf`; Compose sets those same selections in its service environment. |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `LLM_MODEL`, `HF_HOME` | Embedding/model identifiers, vector dimension, and local model cache. Compose uses the existing model defaults and mounts the cache at `/models`. |
| `PROMPT_VERSION`, `RETRIEVAL_VERSION`, `RETRIEVAL_TOP_K` | Prompt/retrieval metadata and retrieval count. Compose passes version labels; top-k uses the application default. |
| `NEXT_PUBLIC_API_URL` | Browser-facing API base URL, local port 8000. |

The worker inherits the API environment through a Compose YAML anchor. The
Dockerfiles set `PYTHONPATH`, unbuffered output, and `HF_HOME` as image defaults;
Compose mounts the model cache and supplies runtime settings. No other
credentials or external model tokens are required by the inspected files.

## 6. Security checks performed

- Verified root `.env` was absent before creation, is not tracked, and matches
  the `.env` ignore rule in `.gitignore`.
- Generated distinct local values using the operating system's cryptographic
  random number generator. The PostgreSQL password, JWT key, MinIO username,
  and MinIO password were generated independently. Secret values were not
  printed or included in this report.
- Verified the MinIO application username/password match the configured MinIO
  root username/password, and the PostgreSQL URL uses the configured password.
- Verified `.env.example` has all expected keys and blank secret fields; no
  working credentials remain in the example.
- Replaced Compose credential fallbacks with required-value substitutions.
- Verified every Compose interpolation variable has a corresponding
  `.env.example` key.
- Verified all seven published Compose port bindings use `127.0.0.1`.
- No service was started, no network exposure was initiated, and no database
  migration or test that writes a database was run.

## 7. Commands executed and actual results

| Command/check | Result |
|---|---|
| `git status --short`; `git ls-files --error-unmatch .env`; `git check-ignore -v .env` | Before changes, `.env` was absent and not tracked. After creation, `git check-ignore -v .env` reported `.gitignore:1:.env`; the tracked-index check still found no `.env`. |
| PowerShell `.NET RandomNumberGenerator` creation of `.env` | Succeeded. Four independent random values were generated; output disclosed no values. The file was created with create-new semantics and was not overwritten. |
| PowerShell local-secret, credential-alignment, and Git-exclusion validation | Passed; `.env` is ignored/untracked, secrets are distinct, MinIO credentials align, and PostgreSQL URL matches. Values were not displayed. |
| PowerShell `.env.example` required-key and blank-secret validation | Passed. |
| PowerShell Compose interpolation/template and port-binding check | Passed: all 17 distinct interpolation variables have sample entries; all 7 published ports bind to loopback. |
| `git diff --check` | Passed. Git emitted a non-fatal LF/CRLF working-copy warning for `infra/docker-compose.yml`. |
| Docker CLI availability check (`Get-Command docker`) | Docker CLI was not found. |
| `docker compose --env-file .env -f infra\docker-compose.yml config` | Not run because Docker is unavailable. Compose runtime/config-parser validation was not performed. |

No backend tests, frontend checks, production build, Docker builds, migrations,
or service/runtime checks were run for this configuration-only task.

## 8. Unresolved issues

- **Compose validation is unverified:** Docker was not available, so Compose YAML
  parsing and interpolated runtime configuration could not be tested.
- **Direct-startup fallback remains in application code:** if a user bypasses
  the documented setup and starts the backend without a root `.env` or
  environment overrides, `backend/app/config.py` still permits a development
  JWT secret and selects SQLite, in-memory storage/vector implementations,
  no-op queue, hash embeddings, and a stub LLM. The application-code change
  needed to fail closed was explicitly outside this task's allowed scope.
- The local `.env` is intentionally ignored and therefore will not be included
  in a commit or shared checkout. Preserve it locally; if it is lost, recreate
  it from the documented template with new independently generated secrets.

## 9. Application behavior change confirmation

No backend/frontend application logic, API behavior, or database schema changed.
The local Compose network exposure was intentionally narrowed: published ports
now accept connections only on loopback instead of all host interfaces. Compose
service selection and internal service architecture remain unchanged.

## 10. Task status

**COMPLETE** for establishing and documenting the local configuration.

Secret handling, Git exclusion, environment-key consistency, and loopback port
bindings were verified. Docker Compose parsing and runtime behavior remain
unverified because Docker is unavailable; no service is claimed to work based
on this configuration-only task.

## 11. Recommended next task from the approved roadmap

Proceed to **Phase 1 — Task 02: upload and deletion reliability fixes**, after
reviewing and approving its scope. This task has not been started.
