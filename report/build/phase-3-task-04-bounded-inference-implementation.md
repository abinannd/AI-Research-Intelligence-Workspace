# Phase 3 - Task 04: Bounded Inference Implementation

**Task:** Implement the smallest practical server-side generation deadline and predictable timeout handling for controlled real-model Ask validation.  
**Date:** 2026-10-19  
**Scope:** Backend (`backend/app/config.py`, `backend/app/citations/llm.py`, `backend/tests/test_harness.py`) and frontend (`frontend/src/lib/api.ts`, `frontend/src/components/WorkspaceAsk.tsx`). No model changes, no weight downloads, no inference executed, no services started/stopped.  
**Status:** STOP FOR REVIEW — implementation complete, tests passing, report recorded.

---

## 1. Files changed and reasons

| File | Change | Reason |
|------|--------|--------|
| `backend/app/config.py` | Added `llm_generation_timeout_seconds: int = 120` | Configurable server-side generation deadline; default 120 seconds |
| `backend/app/citations/llm.py` | `HuggingFaceLLMService.__init__` accepts `max_time`; `model.generate()` receives `max_time=self.max_time`; `build_llm()` wires `settings.llm_generation_timeout_seconds` | Bounds Hugging Face generation itself using Transformers' native `max_time` mechanism |
| `backend/app/citations/qa.py` | No change | Existing exception handler (`qa.py:31-37`) already converts any LLM failure — including invalid/truncated output from a `max_time`-bounded generation — into an abstain response with no claims or citations |
| `backend/app/api/ask.py` | No change | Endpoint contract unchanged; `answer_question()` already records `latency_ms` and returns the standard `AskOut` schema |
| `backend/tests/test_harness.py` | Added 5 tests: `max_time` parameter acceptance, settings wiring, stub backend unaffected, invalid-LLM-output abstain with no citations, Ask endpoint stub compatibility | Verifies deadline mechanism, safe failure handling, and API compatibility |
| `frontend/src/lib/api.ts` | `ask()` accepts optional `timeoutMs`; creates `AbortController` with `setTimeout` abort; passes `signal` to `fetch()` | Client-side deadline; cleans up timer on settle |
| `frontend/src/components/WorkspaceAsk.tsx` | Added `ASK_TIMEOUT_MS = 150_000`; passes timeout to `api.ask()`; handles `AbortError` with clear timeout message; `pending` reset in `finally` | Prevents indefinite loading state; user-visible timeout error |

---

## 2. Deadline mechanism and limitations

### Server-side: `max_time` in Transformers `generate()`

- `backend/app/citations/llm.py:87` — `model.generate(..., max_time=self.max_time)` where `self.max_time` comes from `settings.llm_generation_timeout_seconds` (default 120s).
- `max_time` is a **supported Transformers generation-time mechanism** (Transformers 4.47.1). It is checked during the generation loop and causes generation to stop early when the time budget is exhausted.
- **Not an immediate hard process kill**: When `max_time` is exceeded, `generate()` returns normally with whatever tokens were produced so far. No exception is raised by `generate()` itself.
- **Predictable handling**: Because `max_time` does not raise, the safety net is layered:
  1. Truncated/partial output from `max_time` is typically invalid JSON → `extract_json()` raises `ValueError` → caught by `qa.py:31-37` → abstain response, no claims, no citations.
  2. If partial output happens to be valid JSON (rare), `validate_model_output()` only creates citations from real retrieved chunks with valid indexes — no fabricated citations possible.
  3. `qa.py` records `latency_ms` covering the full attempt including the bounded generation.

### Limitation: client disconnect does not stop server inference

As documented in Task 03, `/ask` is a synchronous FastAPI handler. A client-side abort (AbortController) closes the HTTP connection but **does not terminate** the server-side `model.generate()` call. The server continues until `max_time` expires or generation completes. This is an honest architectural limitation of the synchronous execution model; no route-level timeout or middleware can kill an in-flight generation without moving to async/task-based inference.

### Timeout coordination

- Server-side generation bound: `max_time = 120s` (configurable via `llm_generation_timeout_seconds`).
- Client-side fetch timeout: `ASK_TIMEOUT_MS = 150s` (150 seconds).
- **Server-side limit is shorter** than the client timeout, so the server bounds generation first and returns a response (completion or abstain) within the client's waiting window. The client timeout is a safety net for network issues or server hangs, not the primary inference bound.

---

## 3. Timeout/error behavior

| Scenario | Server behavior | Client behavior | User-facing result |
|----------|----------------|-----------------|-------------------|
| Generation completes within `max_time` | Normal JSON response; `latency_ms` recorded | Response received; `pending` reset | Answer/citations displayed |
| `max_time` exceeded → partial/invalid JSON | `extract_json()` raises; `qa.py` catches → abstain, no claims/citations | 200 response with `abstained=true` | "The sources do not answer this." with abstain reason |
| `max_time` exceeded → rare valid partial JSON | `validate_model_output()` only creates citations from real chunks | 200 response | Valid citations only; answer may be short |
| LLM raises exception (OOM, etc.) | `qa.py:31-37` catches → abstain, no claims/citations | 200 response with `abstained=true` | "The synthesizer could not produce a structured answer" |
| Client fetch abort (timeout) | Server generation continues until `max_time` (no abort propagation) | `AbortError` caught; `pending` reset; error message shown | "The request timed out. The model is still thinking on the server; please try again." |
| 401/403 from server | Standard auth error | Existing handling unchanged | Session/authorization messages |

---

## 4. Tests run and results

### Backend (`pytest`)

```
27 passed, 2 warnings in 7.28s
```

Tests:
- 22 pre-existing tests (unchanged, all pass)
- 5 new tests:
  1. `test_huggingface_llm_accepts_max_time_parameter` — verifies `max_time` stored on instance
  2. `test_build_llm_passes_timeout_from_settings` — verifies `llm_generation_timeout_seconds` wired to `max_time`
  3. `test_build_llm_returns_stub_for_stub_backend` — verifies stub backend unaffected by timeout setting
  4. `test_answer_question_abstains_on_invalid_llm_output_no_citations` — verifies invalid/truncated LLM output yields abstain with zero claims and zero citations
  5. `test_ask_endpoint_stub_llm_compatibility` — verifies Ask endpoint returns 200 with standard schema and `model_version="stub-llm"`

### Frontend (`node --experimental-strip-types --test`)

```
11 passed, 0 failures in 368ms
```

All 11 pre-existing frontend tests pass unchanged. The frontend changes (`api.ts`, `WorkspaceAsk.tsx`) use Next.js/React constructs that cannot be imported in the plain Node.js test infrastructure; component-level timeout testing would require React testing libraries (out of scope for this task).

---

## 5. Existing API compatibility

- **Response schema unchanged**: `AskOut` (`id`, `question`, `abstained`, `abstain_reason`, `answer`, `claims`, `citations`, `latency_ms`, `model_version`, `prompt_version`, `retrieval_version`) is identical.
- **Status codes unchanged**: 200 on success, 400 when no ready documents, 401/403 on auth issues, 404 for workspace/document access.
- **Stub backend unaffected**: `StubLLMService` does not use `max_time`; behavior identical to before.
- **No new dependencies**: Uses Transformers' native `max_time` parameter (already available in `transformers==4.47.1`).
- **No environment changes**: `.env` not modified; no secrets exposed.

---

## 6. Remaining risks and prerequisites for the first live Ask

### Risks

1. **`max_time` is not a hard kill**: Server-side generation continues after client disconnect until `max_time` expires. A runaway generation can occupy the single Uvicorn worker for up to 120s.
2. **Cold-start load still unbounded**: The first `HuggingFaceLLMService.complete()` call triggers model download (if cache cold) and float32 CPU load *before* `max_time` applies. `max_time` only bounds the generation loop, not model loading.
3. **Single worker**: Uvicorn runs one worker; a long generation blocks all other requests on that worker.
4. **Client timeout is not proof of server stop**: Aborting the fetch does not stop server-side inference.

### Prerequisites for first live Ask

1. **Model cache confirmed**: The target model's weights must be present in the HF cache before the Ask. For the isolated Task 07 stack, `SmolLM2-135M-Instruct` is cached (269 MB `model.safetensors`). For the production default `Qwen/Qwen2.5-1.5B-Instruct`, weights are absent — a download would be required (prohibited under current constraints).
2. **Ready document available**: At least one document in `ready` status in the target workspace. The isolated stack has a workspace (`235368be-a06b-4207-8907-77349a6ebb47`) with prior successful ingestion, but current `ready` status cannot be verified without auth credentials.
3. **Timeout tuned**: `llm_generation_timeout_seconds=120` and `ASK_TIMEOUT_MS=150000` are starting values; they should be validated against actual measured generation time on the target hardware.

---

## 7. Is a controlled real-model validation now safe to plan?

**Conditionally yes — against the isolated Task 07 stack only, using SmolLM2-135M-Instruct.**

| Safety requirement | Status |
|-------------------|--------|
| Server-side generation deadline | **Implemented** — `max_time=120s` |
| Client-side request deadline | **Implemented** — 150s AbortController |
| Predictable timeout handling | **Implemented** — abstain on invalid output; clear client timeout message |
| No fabricated citations on failure | **Verified** — validator only creates citations from real retrieved chunks; tested |
| API response schema preserved | **Verified** — 27 backend tests pass |
| Model weights cached (no download needed) | **Met for SmolLM2** on isolated stack; **not met for Qwen 1.5B** |
| Ready document available | **Unverified** — requires auth credentials to confirm |

**Not safe for Qwen/Qwen2.5-1.5B-Instruct**: Model weights are absent from cache; downloading is prohibited under current constraints.

**Recommended next step**: Run a single controlled Ask against the isolated Task 07 stack (API on `127.0.0.1:18000`) using SmolLM2-135M-Instruct, with a client deadline of ~150s, recording `latency_ms`, `abstained`, and citation results. Do not attempt Qwen 1.5B until weights are confirmed cached.

---

## Git checks

1. `git diff --check` — passed (exit code 0; LF/CRLF working-copy warnings are non-fatal and pre-existing).
2. `git status --short --untracked-files=all` — 5 modified files, 1 untracked report (this file); no existing modifications removed or altered.
3. `git check-ignore --no-index report/build/phase-3-task-04-bounded-inference-implementation.md` — no ignore rule matched; file is not ignored.

No commit or push performed. No live inference executed. No Phase 2 Task 07 test run.
