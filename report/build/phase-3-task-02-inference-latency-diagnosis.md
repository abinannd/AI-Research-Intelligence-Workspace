# Phase 3 - Task 02: Inference Latency Diagnosis

**Task:** Diagnose Ask/inference latency without running inference.  
**Date:** 2026-10-19  
**Scope:** Read-only investigation. No inference executed, no services started/restarted, no configuration modified, no secrets exposed, Phase 2 Task 07 not executed. The only new file is this report.  
**Status:** STOP FOR REVIEW — findings recorded, no fix implemented.

---

## 1. Executive summary

The Ask path is server-side synchronous: HTTP request → retrieval (one BGE embedding encode + Qdrant search) → LLM generation → DB commit → response. The configured production LLM is `Qwen/Qwen2.5-1.5B-Instruct` running on **CPU in float32** with lazy (first-call) model loading, up to **700 new tokens** of greedy decoding, and **no server-side or client-side request timeout**. Cold start therefore includes a possible Hugging Face model download plus a float32 CPU load of a ~1.5B-parameter model before any token is generated. Task 01's review already recorded that a prior CPU-model Ask attempt did not return within Playwright's 20-minute window, and the SmolLM2 retry was still downloading weights at last observation with zero queries/citations recorded.

Likely dominant latency contributors (hypotheses, not measurements): cold LLM download/load on the first Ask, per-request CPU greedy decode of up to 700 tokens, and per-Ask BGE `embed_query`. The absence of any timeout means a slow or stuck generation holds the HTTP connection and leaves the frontend in an indefinite "Asking…" state with only a generic error on failure.

---

## 2. Method and constraints

- Read-only inspection of source, configuration, Compose files, Dockerfiles, requirements, and prior reports under `report/build/`.
- No inference was run; no model weights downloaded; no services started or restarted; no `.env` contents read or exposed; no configuration, migration, data, or code changes made.
- Phase 2 Task 07 artifacts (`infra/docker-compose.task07-isolated.yml`, `frontend/e2e/mvp-journey.integration.spec.ts`) were inspected for context only and not executed.
- Evidence is separated into **observed** (code/config read), **measured** (numbers from prior reports), **estimated** (approximations from model sizes/hardware class), and **hypothesis** (unverified).

---

## 3. Observed evidence (from source/config inspection)

### 3.1 Model and backend selection
- `backend/app/config.py:29` — default `llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"`; `.env.example:32` and `infra/docker-compose.yml:75` confirm the same production default.
- `backend/app/config.py:35` — default `llm_backend: str = "stub"`; Compose sets `LLM_BACKEND: hf` (`infra/docker-compose.yml:81`), so the Compose path uses the real Hugging Face implementation.
- `backend/app/citations/llm.py:49-88` — `HuggingFaceLLMService.complete()`:
  - Lazy load: `_load()` runs on **every first** `complete()` call (singleton via `runtime.get_llm()`), loading `AutoTokenizer.from_pretrained` and `AutoModelForCausalLM.from_pretrained(torch_dtype=torch.float32, device_map="cpu")`.
  - Generation: `model.generate(**inputs, max_new_tokens=700, do_sample=False, pad_token_id=eos_token_id)` — greedy decode, up to 700 new tokens, no `max_time`/`timeout`/stopping criteria, no `torch.compile` or quantization.
  - Model/tokenizer are cached on the service instance after first load (`self._model`, `self._tokenizer`); warm requests skip load/download.
- `backend/app/citations/llm.py:91-94` — `build_llm()` returns `StubLLMService()` unless `llm_backend == "hf"`.

### 3.2 Ask invocation path
- `backend/app/api/ask.py:50-97` — `POST /api/workspaces/{workspace_id}/ask`: auth, workspace ownership, readiness gate (≥1 ready document), optional document scoping, then `answer_question(...)`; serializes `latency_ms`, `model_version`, `prompt_version`, `retrieval_version`.
- `backend/app/citations/qa.py:15-88` — `answer_question()`:
  - `started = time.perf_counter()`; `retriever.search(...)`; `run_llm(llm, question, retrieved)`; `validate_model_output(...)`; `latency_ms = int((perf_counter() - started) * 1000)` (qa.py:39).
  - Server-side latency covers retrieval + LLM generation + validation/DB write; network and frontend render time are excluded.
  - On LLM exception, falls back to abstain without re-raising (qa.py:31-37).
- `backend/app/citations/qa.py:27` — retrieval: `retriever.search(question, ...)` → `embeddings.embed_query(question)` (one BGE encode) + `store.search(vector, ..., limit=top_k)`.
- `backend/app/retrieval/retriever.py:6-9` — `top_k` comes from `settings.retrieval_top_k`; default `retrieval_top_k: int = 8` (config.py:39).
- `backend/app/retrieval/embeddings.py:53-75` — `SentenceTransformerEmbeddingService`: lazy `SentenceTransformer(model_name)` load on first encode; `embed_query` encodes a single prefixed sentence.
- `backend/app/retrieval/qdrant_store.py:127-163` — Qdrant `search` with workspace (+optional document) filter, `with_payload=True`, limit=top_k.

### 3.3 Runtime wiring and cold start
- `backend/app/runtime.py:59-63` — `get_llm()` builds the LLM once and caches it globally (`_llm`).
- `backend/app/main.py:15-19` — FastAPI `lifespan` calls `get_runtime()`, which initializes embeddings and vectors but **not** the LLM; LLM load is deferred to the first Ask.
- `backend/app/main.py:22-41` — no request-timeout middleware, no `timeout_keep_alive` override, no route-level timeout on `/ask`. Uvicorn defaults apply.

### 3.4 Queue / worker timeouts (ingestion, not Ask, but relevant context)
- `backend/app/documents/queue.py:31` — RQ enqueue with `job_timeout=1800` (30 minutes).
- `workers/jobs.py:17-96` — ingestion: parse → chunk → embed documents (BGE, batch encode) → upsert vectors; status flow `parsing → indexing → ready`.
- `workers/worker.py:16-22` — RQ worker on queue `ingest`, blocking `work()`.

### 3.5 Compose/runtime configuration
- `infra/docker-compose.yml` — API and worker share `hf_cache:/models` volume (`HF_HOME=/models`); `LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct`; CPU torch image (`backend/Dockerfile:13` installs torch from the PyTorch CPU wheel).
- `backend/Dockerfile:1-24` — `python:3.11-slim`, CPU-only torch, no GPU, no model pre-warming in `CMD`.
- Compose healthchecks: postgres 5s, redis 3s; qdrant/minio use `service_started` only; no startup/grace period accounting for model load.
- No `OMP_NUM_THREADS`, `MKL_THREADING`, or torch thread limiting observed in Compose or Dockerfiles.

### 3.6 Frontend / client timeout paths
- `frontend/src/lib/api.ts:43-83` — `request()` uses raw `fetch()` with **no `signal`/timeout and no `AbortController`**; `api.ask()` (api.ts:168-173) is a plain POST with no deadline.
- `frontend/src/components/WorkspaceAsk.tsx:89-114` — `handleSubmit` sets `pending`, awaits `api.ask(...)`, catches errors; non-401/403 failures map to generic "Could not get an answer. Please try again." (ask.tsx:104-109). No client-side timeout, no retry, no deadline UI.
- The browser/tab may apply its own fetch timeout, but none is configured in application code.

### 3.7 Phase 2 Task 07 artifacts (context only, not executed)
- `infra/docker-compose.task07-isolated.yml` — alternate ports (API 18000, Qdrant 16333, Redis 16379, MinIO 19000/19001, Postgres 15432), isolated bucket/collection, and `LLM_MODEL: HuggingFaceTB/SmolLM2-135M-Instruct` (smaller model).
- `frontend/e2e/mvp-journey.integration.spec.ts` — `test.setTimeout(20 * 60 * 1000)` (20 minutes); status readiness polled with `timeout: 12 * 60 * 1000`; Ask captured via `page.waitForResponse(...)` with no explicit response timeout (Playwright default applies).

---

## 4. Measurements (from prior reports; no new inference run)

| Source | Value | Context |
|--------|-------|---------|
| Phase 2 Task 03.5 (`report/build/phase-2-task-03-5-ingestion-verification.md`) | BGE first ingestion ≈ 1 min 15 s | Cold model download + CPU load on first worker run; model cache absent before, present after. |
| Phase 2 Task 03.5 | Worker image build ≈ 13 min | CPU torch + ML deps download/build. |
| Phase 3 Task 01 (`report/build/phase-3-task-01-mvp-readiness-review.md`) | Prior CPU-model Ask did not complete within Playwright's 20-minute window | Real-model Ask call recorded no result; zero queries/citations at last observation. |
| Phase 3 Task 01 | SmolLM2-135M retry still downloading weights at interruption | No completed Ask response; end-to-end Ask unverified. |
| Phase 2 Task 03.5 | `rq info`: 1 worker, `ingest` queue, 0 failed jobs | Queue/worker itself healthy; no backlog indication. |

No per-Ask server latency (`latency_ms`) has been recorded in any report, because no completed live Ask exists.

---

## 5. Estimates (approximations; not measurements)

- Qwen2.5-1.5B float32 weights ≈ 2.8–3 GB. On CPU with no quantization/GPU, first-call cost = HF download (network-dependent, if cache cold) + float32 model load + tokenizer load, then greedy decode of up to 700 tokens.
- SmolLM2-135M float32 ≈ 250 MB — smaller download/load, but still CPU-bound decoding.
- One BGE `embed_query` (384-dim, single sentence) is expected to be small relative to LLM generation, but still a CPU model load on first Ask if embeddings are cold.
- Per-token CPU generation speed for a 1.5B model is hardware-dependent; no measurement available. Worst case with max_new_tokens=700 and no early stopping could be minutes per Ask.

These are estimates only; they must be validated with timed live runs (without changing code).

---

## 6. Hypotheses (unverified; to be tested)

1. **Dominant cost is cold LLM load/download on the first Ask.** The first Ask after a cold container start triggers HF download (if cache empty) and float32 CPU load of Qwen2.5-1.5B before generation. Subsequent Asks reuse the cached singleton (`runtime.py:_llm`, `llm.py:_model`).
2. **Per-request generation is unbounded.** `max_new_tokens=700` with `do_sample=False` and no generation timeout means a single Ask can spend a long time decoding on CPU, holding the HTTP connection.
3. **No server/client timeout masks the problem.** There is no FastAPI/uvicorn request timeout and no client fetch timeout/abort, so a slow generation produces an indefinite "Asking…" state rather than a bounded error. The only observed failure mode is a test-level 20-minute Playwright timeout.
4. **Per-Ask BGE encode adds a smaller fixed cost** (one sentence, cold-load on first Ask if the ST model cache is cold).
5. **Warm-state Asks may be acceptable** once both BGE and LLM are loaded; the cliff is the cold start.

---

## 7. Timeout and failure-path summary

| Layer | Timeout configured? | Behavior on slow inference |
|-------|--------------------|----------------------------|
| RQ ingestion job (`queue.py:31`) | `job_timeout=1800` s | Ingestion job killed by RQ after 30 min → document `failed`. |
| API / FastAPI (`main.py`) | None | No request deadline; slow `/ask` holds the worker/connection. |
| Uvicorn (`backend/Dockerfile:23`) | Defaults only | No explicit timeout override. |
| LLM generation (`llm.py:81-86`) | None | `generate()` runs to completion or OOM/error; no `max_time`. |
| Frontend `api.ask` (`api.ts:168-173`) | None | Raw `fetch`, no `signal`, no deadline; browser-dependent. |
| Frontend UI (`WorkspaceAsk.tsx`) | None | Indefinite `pending`; errors map to generic message. |
| Playwright Task 07 (`mvp-journey.integration.spec.ts:115`) | Test 20 min; readiness poll 12 min | Ask has no explicit response timeout; test aborts at 20 min. |

---

## 8. Impact and risk to MVP acceptance

MVP criterion 3 (Ask Question) and criterion 4 (Verifiable Citations) depend on a completed Ask response. The diagnosis indicates:

- **First Ask on a cold stack is very likely to be slow or to time out** in a browser test window (already evidenced by Task 01: 20-minute Playwright timeout, no completed Ask).
- **No bounded failure mode**: without a timeout, the UI shows "Asking…" indefinitely; on failure it shows a generic message with no retry.
- **Citation page-jump (criterion 5)** depends on a successful Ask first, so it is blocked by the same latency.

---

## 9. Recommended next steps (for review — do not implement yet)

1. Instrument and measure: record server-side `latency_ms` breakdown (retrieval vs LLM vs validation) for warm and cold Asks against a ready document; confirm whether cold-start download/load or per-token generation dominates.
2. Add a bounded server-side timeout for `/ask` generation (e.g., FastAPI/route timeout or `generate(max_time=...)`), with a clean abstain/error response on timeout.
3. Add a client fetch timeout/abort and a retry or deadline UI in `WorkspaceAsk.tsx` so users are not left in indefinite "Asking…".
4. Consider model/warm-up options: preload LLM at API startup (`runtime.get_llm()` in lifespan), quantization (`torch_dtype=torch.float16`/`load_in_8bit` if CPU-compatible), or lowering `max_new_tokens`; validate against answer quality (grounded citations).
5. Re-run the Task 07 journey only after model weights are confirmed downloaded and a measured, realistic timeout is in place.

---

## 10. Git checks (completed before stopping)

1. `git diff --check` — passed (no whitespace errors; non-fatal LF/CRLF warnings for pre-existing working copy are unrelated).
2. `git status --short --untracked-files=all` — working tree clean; Task 07 changes are committed (`830ca5d mvp`); only this new report is untracked.
3. `git check-ignore --no-index report/build/phase-3-task-02-inference-latency-diagnosis.md` — no ignore rule matched (`REPORT_NOT_IGNORED`); the file is not ignored by Git.

No fix has been implemented and no integration test has been started. STOP FOR REVIEW.
