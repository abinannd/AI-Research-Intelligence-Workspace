# Phase 3 - Task 03: Bounded Ask Validation Readiness Check

**Task:** Determine whether the environment is ready for one controlled, bounded real-model Ask validation.  
**Date:** 2026-10-19  
**Scope:** Read-only investigation only. No inference executed, no services started/stopped/restarted, no configuration/source/environment/dependency changes, no model downloads, no migrations, no data alteration, no commits/pushes. Phase 2 Task 07 not executed.  
**Only new file:** this report.  
**Status:** STOP FOR REVIEW — findings recorded, no test executed.

---

## 1. Exact files inspected

- `AGENTS.md` (repository root)
- `report/build/phase-3-task-01-mvp-readiness-review.md`
- `report/build/phase-3-task-02-inference-latency-diagnosis.md`
- `report/build/phase-2-task-03-5-ingestion-verification.md`
- `report/build/phase-2-task-06-citation-browser-verification.md`
- `infra/docker-compose.yml`
- `infra/docker-compose.task07-isolated.yml`
- `infra/README.md`
- `backend/app/config.py`
- `backend/app/runtime.py`
- `backend/app/citations/llm.py`
- `backend/app/citations/qa.py`
- `backend/app/citations/prompts.py`
- `backend/app/citations/validator.py`
- `backend/app/api/ask.py`
- `backend/app/main.py`
- `backend/app/retrieval/retriever.py`
- `backend/app/retrieval/embeddings.py`
- `backend/app/retrieval/qdrant_store.py`
- `backend/app/documents/queue.py`
- `backend/Dockerfile`, `workers/Dockerfile`
- `backend/requirements.txt`, `backend/requirements-ml.txt`
- `workers/jobs.py`, `workers/worker.py`
- `frontend/e2e/mvp-journey.integration.spec.ts`
- `.env.example` (read for variable names/defaults only; `.env` values NOT read or exposed)

Live probes (read-only, no inference):
- `GET http://127.0.0.1:18000/health` (isolated Task 07 API)
- `GET http://127.0.0.1:18000/api/workspaces/{workspace_id}/documents` without auth (confirm auth requirement)
- `GET http://127.0.0.1:16333/healthz` (Qdrant)
- `docker exec` listing of `/models/hub` inside `ari-task07-20261018-2030-api-1`
- `docker logs` of the isolated API and worker containers

---

## 2. Git state

### Before investigation
```
?? report/build/phase-3-task-02-inference-latency-diagnosis.md
```
Latest commit: `830ca5d mvp`. Working tree contained only the Task 02 report as untracked.

### After investigation
```
?? report/build/phase-3-task-02-inference-latency-diagnosis.md
?? report/build/phase-3-task-03-bounded-ask-readiness.md
```
No tracked files modified. No commits/pushes. No existing modifications or untracked files removed or altered.

---

## 3. Runtime and container status

Two Docker Compose stacks are present. Both were left exactly as found; none were started or stopped for this task.

### Isolated Task 07 stack (`ari-task07-20261018-2030-*`, ports 15432/16379/16333/19000-19001/18000) — RUNNING

| Container | Image | Status | Port |
|-----------|-------|--------|------|
| ari-task07-20261018-2030-postgres-1 | postgres:16-alpine | Up 16 hours (healthy) | 127.0.0.1:15432 |
| ari-task07-20261018-2030-redis-1 | redis:7-alpine | Up 16 hours (healthy) | 127.0.0.1:16379 |
| ari-task07-20261018-2030-qdrant-1 | qdrant/qdrant:v1.12.5 | Up 16 hours | 127.0.0.1:16333 |
| ari-task07-20261018-2030-minio-1 | pgsty/minio:RELEASE.2026-08-04 | Up 16 hours | 127.0.0.1:19000/19001 |
| ari-task07-20261018-2030-api-1 | ari-task07-...-api | Up 16 hours | 127.0.0.1:18000 |
| ari-task07-20261018-2030-worker-1 | ari-task07-...-worker | Up 16 hours | (internal) |

- `GET /health` on the isolated API: **HTTP 200 OK** `{"status":"ok"}`
- `GET /healthz` on Qdrant: **HTTP 200 OK** `healthz check passed`
- API logs show prior successful signup, workspace creation, document upload, and repeated document-status polling against workspace `235368be-a06b-4207-8907-77349a6ebb47`. An `OPTIONS /ask` preflight was logged, but **no `POST /ask`** appears in the logs — no Ask request was ever issued/completed against this stack.
- Worker logs show two ingestion jobs completed successfully (1m56s and 23s). Worker is currently idle ("Cleaning registries for queue: ingest").
- This stack was configured with `LLM_MODEL=HuggingFaceTB/SmolLM2-135M-Instruct` (isolated Compose override).

### Main stack (`research-workspace-*`, standard ports 5432/6379/6333/9000-9001/8000) — PARTIALLY RUNNING

| Container | Status |
|-----------|--------|
| research-workspace-postgres-1 | Up 18 hours (healthy) |
| research-workspace-redis-1 | Up 18 hours (healthy) |
| research-workspace-qdrant-1 | Up 18 hours |
| research-workspace-minio-1 | Up 18 hours |
| research-workspace-api-1 | Created (not running) |
| research-workspace-api-verification | Exited (0) 18 hours ago |
| research-workspace-worker-1 | Exited (0) 18 hours ago |

The main stack's database/Redis/Qdrant/MinIO are running, but its API and worker containers are not running (one `Created`, two `Exited`). The main stack is configured with `LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct`.

---

## 4. Model-cache availability and completeness

Inspected via `docker exec ari-task07-20261018-2030-api-1 ls -laR /models/hub`. No host-side `./models` directory exists (`HOST_MODELS_DIR_ABSENT`); cache lives only inside the container volume.

| Model | Cache path | Completeness | Evidence |
|-------|-----------|--------------|----------|
| BAAI/bge-small-en-v1.5 (embedding) | `/models/hub/models--BAAI--bge-small-en-v1.5` | **Complete** | `snapshots/.../model.safetensors` -> blob 133 MB; all config/tokenizer files present via symlinks; `.no_exist` marker absent from snapshot |
| HuggingFaceTB/SmolLM2-135M-Instruct (isolated stack LLM) | `/models/hub/models--HuggingFaceTB--SmolLM2-135M-Instruct` | **Complete** | `snapshots/.../model.safetensors` -> blob 269 MB; config.json, generation_config.json, merges.txt, tokenizer.json, tokenizer_config.json, vocab.json, special_tokens_map.json all present; refs/main present |
| Qwen/Qwen2.5-0.5B-Instruct | `/models/hub/models--Qwen--Qwen2.5-0.5B-Instruct` | **Incomplete** | Blobs include only a 536 MB `fdf756...incomplete` file; snapshot has config/merges/tokenizer files but **no `model.safetensors`** (weights missing); wrong model variant anyway |
| Qwen/Qwen2.5-1.5B-Instruct (main-stack configured production model) | Not present | **Absent** | No `models--Qwen--Qwen2.5-1_5B-Instruct` directory exists in the cache |

**Interpretation:**
- The isolated running stack is configured for SmolLM2-135M-Instruct, and that model's weights **are fully cached** — no initial download would be required for an Ask against this stack.
- The configured production model `Qwen/Qwen2.5-1.5B-Instruct` is **not cached anywhere** — validating it would require a model download, which is prohibited in this task.
- The Qwen 0.5B cache is incomplete and is the wrong model variant regardless.

---

## 5. Existing workspace/document readiness

### What can be confirmed
- Isolated stack workspace `235368be-a06b-4207-8907-77349a6ebb47` exists; API logs show successful upload and repeated status polling for it. Prior reports (Task 01) document that the Task 07 run reached document `ready` status with successful indexing.
- Qdrant collection `ari_task07_20261018_2030` exists (matches isolated stack config).
- Worker completed two ingestion jobs successfully; zero failed jobs.

### What cannot be confirmed without credentials
- Whether a document in that workspace is currently in `ready` status. The documents endpoint requires authentication (`GET /api/workspaces/{id}/documents` without a bearer token returns `{"detail":"Not authenticated"}`).
- No auth credentials were read, obtained, or exposed; `.env` was not read.
- The Task 07 live-evidence file (`frontend/.playwright/task07-live-evidence.json`) is **absent**, so there is no machine-readable record of a completed query/citation from a prior run.

**Conclusion:** Workspace existence and prior ingestion are evidenced by logs and reports, but current `ready`-document status cannot be verified read-only without auth credentials.

---

## 6. Relevant request and timeout behavior

### Server side (from code inspection; no changes made)
- `POST /api/workspaces/{id}/ask` is handled synchronously in the FastAPI route (`backend/app/api/ask.py:50-97`).
- `answer_question()` (`backend/app/citations/qa.py:15-88`) performs retrieval (one BGE `embed_query` + Qdrant `search`), then `llm.complete()` (`backend/app/citations/llm.py:72-88`), then validation and DB commit.
- `HuggingFaceLLMService.complete()` lazy-loads the model on first call (`_load()` at llm.py:59-70), then calls `model.generate(max_new_tokens=700, do_sample=False, ...)` with **no `max_time`, no stopping criteria, no timeout** (llm.py:81-86).
- `backend/app/main.py` has no request-timeout middleware and no route-level timeout on `/ask`. Uvicorn defaults apply (one worker, no explicit keep-alive/request deadline).
- Server-side `latency_ms` is recorded in `qa.py:39` covering retrieval + LLM + validation + DB write; network and frontend render time are excluded.

### Client side (from code inspection)
- `frontend/src/lib/api.ts:168-173` `api.ask()` uses raw `fetch()` with **no `signal`, no `AbortController`, no deadline**.
- `frontend/src/components/WorkspaceAsk.tsx:89-114` `handleSubmit` sets `pending`, awaits `api.ask()`, and on non-401/403 errors shows a generic message. **No client-side timeout, no retry, no deadline UI.**
- The button disables while `pending`, but there is no upper bound on how long `pending` can last.

### Client disconnect vs server-side inference
- Because `/ask` is a synchronous handler with no timeout, a client-side disconnect/timeout (e.g., browser tab close, fetch abort if one were added, or Playwright test abort at 20 min) **does not reliably stop server-side inference**. Uvicorn may continue running `model.generate()` until completion or error. There is no mechanism observed to terminate an in-flight generation on client disconnect.

### Ingestion job timeout (for contrast)
- RQ ingestion jobs use `job_timeout=1800` (30 min) (`queue.py:31`). No equivalent timeout exists for Ask inference.

---

## 7. Observed evidence vs estimates vs hypotheses

### Observed evidence
1. Isolated Task 07 API reachable and healthy (`/health` = 200). Qdrant healthy.
2. SmolLM2-135M-Instruct weights fully cached in the isolated API container; no download needed for that model.
3. Qwen/Qwen2.5-1.5B-Instruct (production default) absent from cache; Qwen 0.5B cache incomplete.
4. No `POST /ask` appears in isolated API logs — no Ask has been issued/completed against this stack.
5. No Task 07 live-evidence file exists.
6. Document-status endpoint requires auth; ready-document status unverifiable without credentials.
7. Worker idle; two prior ingestion jobs succeeded.
8. No server or client timeout configured for Ask; no `latency_ms` recorded for any completed Ask (none completed).

### Estimates (not measurements)
- SmolLM2-135M float32 load + greedy decode on CPU: sub-minute to a few minutes per Ask depending on host CPU; bounded by 700 max new tokens.
- Qwen 1.5B would require download (~several GB) before any inference — prohibited in this task.

### Hypotheses (unverified)
1. A warm SmolLM2 Ask on this stack would complete quickly (model cached, lazy load already potentially done if the service loaded it at startup — though `get_llm()` is only invoked on first Ask, not in lifespan).
2. A Qwen 1.5B Ask cannot run without a download.
3. A client-side timeout would not stop server-side generation (no server timeout, no abort propagation).
4. Cold-start LLM load (first Ask) dominates over warm Asks.

---

## 8. Whether a safe bounded Ask test is currently possible

**No — not against the configured production model, and only conditionally against the running isolated stack.**

| Requirement | Status |
|-------------|--------|
| Avoid downloading model weights | **Met for SmolLM2** (cached); **not met for Qwen 1.5B** (absent, download required — prohibited) |
| Avoid unbounded waiting | **Not met** — no server-side or client-side timeout on `/ask` |
| Clearly defined request deadline | **Not met** — no deadline mechanism exists in client or server |
| Distinguish cold vs warm inference | **Partially met** — cold vs warm can be inferred from first-call load, but no instrumentation exists to record the breakdown |
| Record completed/timed-out/failed outcome | **Not met** — no deadline means no deterministic timeout outcome; can only observe completion or indefinite hang |
| Capture server-side latency and citations | **Met if Ask completes** — `latency_ms` is stored and returned; citations are in the response |
| Avoid leaving runaway inference behind | **Not met** — no mechanism to stop server-side generation if client disconnects/times out |

**The fundamental blocker:** The existing implementation provides no reliable bound on server-side inference work. There is no request timeout, no generation `max_time`, no client fetch deadline, and no way to terminate an in-flight generation on client disconnect. A client-side timeout is explicitly **not** proof that the server stopped processing.

Therefore, executing a real Ask now risks leaving an unbounded CPU generation running on the isolated stack with no cleanup path, and testing the configured production model (Qwen 1.5B) is impossible without a prohibited download.

---

## 9. Smallest recommended next step

Add a bounded server-side deadline to `/ask` inference before attempting any live Ask validation. The minimal change is to bound `HuggingFaceLLMService.complete()` generation (e.g., pass `max_time=` to `model.generate()` in `backend/app/citations/llm.py:81-86`) and/or add a FastAPI route timeout on `/ask`, with a clean abstain/error response on deadline. Once a bounded deadline exists and the configured model's cache status is confirmed, a single controlled Ask can be run with a client deadline shorter than the server deadline, recording completed/timed-out/failed and capturing `latency_ms`/citations on success.

Until that bound is in place, do not execute a real-model Ask.

---

## Git checks (completed before stopping)

1. `git diff --check` — passed (exit code 0).
2. `git status --short --untracked-files=all` — reported only the two new report files as untracked; no tracked files modified.
3. `git check-ignore --no-index report/build/phase-3-task-03-bounded-ask-readiness.md` — no ignore rule matched; file is not ignored.

No fix implemented, no model downloaded, no inference executed, no integration test started. STOP FOR REVIEW.
