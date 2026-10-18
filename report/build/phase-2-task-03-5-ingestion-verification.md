# Phase 2 - Task 03.5: Verify Document Ingestion

## Result

**End-to-end ingestion passed** using a newly created authenticated test account/workspace and an in-memory generated, one-page, non-sensitive PDF. The authenticated API upload returned `queued`; the RQ worker processed it; status polling observed `indexing` and then `ready`. The database contained one chunk for the test document, and Qdrant contained one matching vector point with the expected document/workspace payload.

No application source or Compose file was changed. No credentials or `.env` values were printed or saved in this report.

## Components inspected

- `infra/docker-compose.yml`: service definitions, environment wiring, health dependencies, ports, volumes.
- `backend/app/documents/queue.py`, `backend/app/documents/service.py`: queue name, queue backend, upload persistence/enqueue sequence.
- `workers/jobs.py`, `workers/worker.py`, `workers/Dockerfile`: job processing, RQ startup, listening queue, image dependencies.
- `backend/app/documents/storage.py`, `backend/app/retrieval/qdrant_store.py`, `backend/app/runtime.py`: MinIO/S3 and Qdrant adapters and runtime initialization.
- `backend/app/api/documents.py`, `backend/app/api/auth.py`, `backend/app/api/workspaces.py`: authenticated test workflow endpoints.
- `backend/app/config.py`, `backend/app/retrieval/embeddings.py`, `backend/requirements.txt`, `backend/requirements-ml.txt`: runtime selection, model settings, and ML package requirements.

## Configuration and runtime evidence

- Compose configuration validated with the root `.env` supplied to Compose. The file was not read or displayed.
- Compose config selects `QUEUE_BACKEND=rq`, `REDIS_URL=redis://redis:6379/0`, `STORAGE_BACKEND=s3`, `MINIO_ENDPOINT=minio:9000`, `VECTOR_BACKEND=qdrant`, and `QDRANT_URL=http://qdrant:6333`. API and worker receive the shared application environment.
- `RedisRQQueue` and `workers.worker` both use queue name `ingest`. Worker logs confirmed `Listening on ingest`; `rq info` showed one idle worker, the `ingest` queue, and zero failed jobs after the test.
- Runtime adapter check returned `MinioStorage`, `QdrantVectorStore`, `RedisRQQueue`, and `SentenceTransformerEmbeddingService`.
- Redis `PING` returned `True`; the API started successfully on the alternate port and reported health `ok`.
- MinIO `/minio/health/live` and Qdrant `/healthz` each returned HTTP 200. API startup initialized the configured runtime; the successful upload and worker retrieval also exercised MinIO write/read.
- Qdrant collection `research_chunks` reported status `green`.
- Worker ML imports/package metadata succeeded: FastAPI 0.115.6, PyMuPDF 1.25.2, qdrant-client 1.12.1, redis 5.2.1, RQ 2.1.0, sentence-transformers 3.3.1, torch 2.14.1+cpu, transformers 4.47.1.
- The BGE model cache was absent before processing. It was present, including its model config, after the worker completed the upload, demonstrating model acquisition and use on this run.

## Actual workflow

1. Created a unique test user using a random password held only in the PowerShell process; created a dedicated workspace via the authenticated API. The token/password were withheld from output and not persisted.
2. Generated a one-page text PDF in memory in the worker container. Its generic text was solely for exercising extraction, chunking, embedding, and indexing.
3. Uploaded it using authenticated `POST /api/workspaces/{workspace_id}/documents` with multipart field `file`. Response: HTTP 200, `page_count=1`, `status=queued`.
4. Polled authenticated `GET /api/workspaces/{workspace_id}/documents`. Observed `indexing`, then `ready`.
5. Worker logs recorded the `workers.jobs.ingest_document` job as successfully completed in approximately 1 minute 15 seconds, with `Job OK`.
6. Queried the relational database for chunks matching the test document and workspace: **1 chunk**.
7. Queried Qdrant with both `document_id` and `workspace_id` filters: **1 vector point**; payload matched both identifiers.

The polling interval did not observe the brief `parsing` status; the successful final state and chunk/vector checks demonstrate that parsing and indexing completed.

## Commands executed and actual results

Commands ran in PowerShell from the repository root. No `.env` values were included in command output.

| Command / action | Actual result |
|---|---|
| `git status --short --untracked-files=all` and `git --no-pager diff -- infra\docker-compose.yml` at start | No working-tree changes or Compose diff were reported. Compose was left unchanged. |
| Initial `docker compose ps --all` without an env file | Failed interpolation because required Compose variables were not supplied. No services were changed by this probe. |
| `docker compose --env-file .env -f infra\docker-compose.yml config -q` | Passed; printed `COMPOSE_CONFIG_VALID`. |
| `docker compose --env-file .env -f infra\docker-compose.yml ps --all` before startup | PostgreSQL and Redis healthy; MinIO and Qdrant running; API and worker were not running. |
| `Invoke-WebRequest` probes to `http://127.0.0.1:8000/health`, `http://127.0.0.1:6333/healthz`, `http://127.0.0.1:9000/minio/health/live` | All returned HTTP 200. The port-8000 health response was from an already-listening process, not the Compose API container. |
| `docker compose --env-file .env -f infra\docker-compose.yml up -d --build api worker` | Both images built successfully and the worker started. API startup failed because host port 127.0.0.1:8000 was already occupied. Compose created `research-workspace_hf_cache`; no volume was deleted or reset. |
| `docker compose --env-file .env -f infra\docker-compose.yml run -d --no-deps -p 127.0.0.1:8001:8000 --name research-workspace-api-verification api` | Started the Compose API on port 8001; `/health` returned `ok`. Unauthenticated `/api/auth/me` returned 403, as expected without bearer credentials. |
| `docker compose --env-file .env -f infra\docker-compose.yml logs --no-color --tail 40 worker` | Worker startup logged `Listening on ingest`; logs showed a pre-existing queued job completed before the test upload, then the test ingestion job completed with `Job OK`. The unrelated job's document outcome was not assessed. |
| `docker compose --env-file .env -f infra\docker-compose.yml exec -T worker python -c "<package/runtime checks>"` | Required imports/versions passed; Redis ping true; expected MinIO, Qdrant, RQ, and SentenceTransformer adapters selected. A first version probe using `qdrant_client.__version__` raised `AttributeError`; the package-metadata version probe then succeeded with qdrant-client 1.12.1. |
| Authenticated PowerShell test script: signup, create workspace, generate PDF, multipart `POST /api/workspaces/{id}/documents`, poll `GET /api/workspaces/{id}/documents` | First attempt stopped after signup/workspace creation because PowerShell had not loaded `System.Net.Http`; no document was uploaded. Retried after `Add-Type -AssemblyName System.Net.Http`: signup/workspace creation and upload succeeded; upload HTTP 200, `queued`, one page; polling observed `indexing` then `ready`. |
| Worker-container database/Qdrant verification script filtered by the test workspace and document IDs | `CHUNK_COUNT 1`; `VECTOR_POINT_COUNT 1`; `VECTOR_PAYLOAD_MATCH True`. |
| `docker compose --env-file .env -f infra\docker-compose.yml exec -T worker rq info --url redis://redis:6379/0` | One worker, one queue, zero executing, two finished, zero failed; worker idle. Finished count includes the unrelated pre-existing job noted above. |
| Worker model-cache check and `QdrantClient.get_collection` | BGE cache and model config present; `research_chunks` status `green`, one point. |
| `docker stop research-workspace-api-verification research-workspace-worker-1` | Both verification containers stopped successfully (exit 0). Existing PostgreSQL, Redis, MinIO, and Qdrant containers remained running. |

## Blockers and limitations

- Host port 8000 was occupied, preventing the Compose API service from binding its declared port. Verification succeeded by running the same API image on local port 8001; Compose was not edited.
- The worker image build required downloading CPU PyTorch and Python dependencies and took approximately 13 minutes in this environment. The BGE model was not pre-cached and was downloaded during ingestion; this run succeeded.
- The first test script attempt created a separate isolated test user/workspace but failed before uploading a document because the PowerShell HTTP assembly was not loaded. A second, separate test identity/workspace was used for the successful run.
- The worker processed one pre-existing job already in Redis when it started. Its document outcome was not checked; the test run did not clear or reset the queue/database.
- Successful test user/workspace/document/chunk/vector data remain in the persistent services. They were intentionally not deleted, consistent with the no-reset/no-volume-deletion requirement. Generated credentials were ephemeral and withheld.
- The Compose `api` service container created during the failed port bind remains in `Created` state; it was not removed. The alternate verification API and worker were stopped. No volume was removed.

## Git checks

- `git diff --check`: passed (exit code 0; `GIT_DIFF_CHECK=PASS`).
- `git status --short --untracked-files=all`: only `?? report/build/phase-2-task-03-5-ingestion-verification.md` was reported.
- `git check-ignore -v --no-index report/build/phase-2-task-03-5-ingestion-verification.md`: no ignore rule matched; `REPORT_NOT_IGNORED`.
- Report trailing-whitespace scan: no matches.

## Recommended next task

Verify the user-facing workspace upload/status journey against this live-configured ingestion stack, then implement the workspace Ask UI gated on at least one document reaching `ready`. Keep the existing persistent test data isolated; do not reset service volumes.
