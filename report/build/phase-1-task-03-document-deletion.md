# Phase 1 — Task 03: Document Deletion Reliability

## 1. Objective

Ensure a document is not reported as deleted and its database row is not
removed unless both vector-index cleanup and object-storage cleanup succeed.

## 2. Root cause

The original `delete_document` service function in
[`backend/app/documents/service.py`](../../backend/app/documents/service.py)
wrapped `storage.delete` and `vectors.delete_document` in separate broad
`except Exception: pass` blocks. It then unconditionally deleted the document
row and committed. Consequently, an API request could return its success
response even if either external resource remained.

The API endpoint in
[`backend/app/api/documents.py`](../../backend/app/api/documents.py) returns
HTTP 204 when the service completes. Exceptions not converted to
`HTTPException` would be handled as server errors, but the service suppressed
the cleanup errors, so they never reached the endpoint.

## 3. Files inspected

- [`backend/app/api/documents.py`](../../backend/app/api/documents.py) —
  workspace-scoped DELETE endpoint and existing 204 success response.
- [`backend/app/documents/service.py`](../../backend/app/documents/service.py)
  — ownership lookup and deletion sequence.
- [`backend/app/documents/storage.py`](../../backend/app/documents/storage.py)
  — `Storage.delete`, `MemoryStorage.delete`, and `MinioStorage.delete`.
- [`backend/app/retrieval/qdrant_store.py`](../../backend/app/retrieval/qdrant_store.py)
  — `VectorStore.delete_document`, memory and Qdrant implementations.
- [`backend/app/models.py`](../../backend/app/models.py) — document, chunk,
  citation relationships and relevant foreign-key delete behavior.
- [`backend/app/database.py`](../../backend/app/database.py) — SQLAlchemy
  session lifecycle.
- [`backend/tests/conftest.py`](../../backend/tests/conftest.py) — isolated
  SQLite database and FastAPI test-client fixtures.
- [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py) —
  existing test conventions and test doubles.
- [`.gitignore`](../../.gitignore) and current Git status — report ignore and
  visibility checks.

## 4. Files modified

- **Modified:** [`backend/app/documents/service.py`](../../backend/app/documents/service.py)
  — propagate external cleanup failures as HTTP 503 and defer database
  deletion until both external cleanup calls succeed.
- **Modified:** [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py)
  — add deterministic endpoint-level tests for success, both cleanup failures,
  partial cleanup, and retry by repeated DELETE.
- **Created:** this report at the required path.

No application API route, schema, configuration, frontend, infrastructure, or
`.gitignore` file was modified.

## 5. Original failure behavior

Original order:

1. Attempt object deletion; ignore any exception.
2. Attempt vector deletion; ignore any exception.
3. Delete and commit the database document regardless.
4. Return HTTP 204 from the endpoint.

The existing storage implementations and vector stores expose synchronous
`delete`/`delete_document` operations. They do not provide a transaction spanning
storage, Qdrant, and PostgreSQL. ORM document relationships cascade to chunks;
citations referencing a document use `ON DELETE SET NULL`.

## 6. Implemented deletion flow

The service now:

1. Resolves the document using the existing workspace ownership check.
2. Deletes vectors for the document and workspace.
3. Deletes the stored file.
4. Deletes the database document and commits only after both external calls
   return successfully.

If vector cleanup raises an exception, the service raises HTTP 503 with a
vector-cleanup failure detail and does not attempt storage deletion or database
deletion. If storage cleanup raises, it raises HTTP 503 with a storage-cleanup
failure detail and leaves the database row in place. The exception is chained
for server-side diagnosis rather than silently suppressed. Successful deletion
continues to return HTTP 204; a subsequent request after full deletion follows
the existing not-found behavior.

The cleanup order is vectors, then storage, then database. This makes a vector
failure leave the object intact and lets a storage failure retain the database
row needed to retry cleanup. It does not make the external operations atomic.

## 7. Partial-failure and retry implications

- If vector deletion succeeds but object deletion fails, the database row
  remains, while the vector index may already be absent. The endpoint reports
  HTTP 503, not success.
- A caller can retry with the same DELETE URL while the row remains. The test
  verifies that a second request attempts both cleanup operations again and
  removes the row only after they succeed.
- There is no automatic retry queue or deletion state. Repeated cleanup is
  compatible with the in-memory vector implementation and is expected to be
  safe for the current Qdrant filtered deletion and S3-compatible object
  deletion behavior, but remote service behavior was not executed here.
- If PostgreSQL commit fails after both external deletes succeed, the external
  resources may be gone while the database row remains. No cross-system
  transaction can prevent that with the current interfaces; a later request
  must rely on idempotent external delete operations. This task adds no
  background recovery mechanism.

## 8. Tests added

Added three endpoint-level tests using the existing isolated SQLite fixture
with local recording doubles:

1. **Successful deletion:** both external cleanup methods are called, database
   row is removed, endpoint returns 204.
2. **Vector cleanup failure:** endpoint returns 503, database row remains, and
   storage cleanup is not attempted.
3. **Storage cleanup failure / partial failure:** vector cleanup succeeds,
   storage fails, endpoint returns 503, and the row remains. A repeated DELETE
   then succeeds after the test double recovers; only that successful retry
   removes the row.

The test cases require no live PostgreSQL, Redis, Qdrant, or MinIO services.

## 9. Commands executed and actual results

| Command | Actual result |
|---|---|
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider -k delete_document` | **Passed:** 3 passed, 14 deselected; two existing dependency warnings. |
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider` | **Passed:** 17 passed; two existing dependency warnings. |
| `git diff --check` | **Passed** (non-fatal Git LF/CRLF working-copy warnings observed for modified Python files). |
| `git status --short --untracked-files=all` | Run after report creation; see the final report-tracking verification below. |

No packages were installed. No services were started. No migrations were run.

## 10. Git diff check result

`git diff --check` completed successfully after the source and test edits. It
reported no whitespace errors. Git emitted only its non-fatal line-ending
conversion warning for modified Python files.

## 11. Report tracking verification

- Required command: `git check-ignore -v report/build/phase-1-task-03-document-deletion.md`
- Actual result: no matching ignore rule was returned (exit status 1, meaning
  the report is not ignored).
- Required command: `git status --short --untracked-files=all`
- Actual result after creating this report:
  `?? report/build/phase-1-task-03-document-deletion.md`
- No `.gitignore` rule was added or changed to hide this report.

## 12. API-contract impact

No API route, success response, or database schema contract changed. Successful
DELETE still returns HTTP 204. Cleanup failures now return HTTP 503 with a
human-readable detail rather than incorrectly returning success.

## 13. Known limitations and unresolved risks

- External cleanup and database commit are not atomic. A database commit error
  after external deletion can leave the database row without its external
  resources.
- Partial cleanup has no automatic worker/reconciliation path; a caller must
  retry the DELETE while the document row remains.
- Real Qdrant, MinIO, and PostgreSQL failure modes were not exercised. Tests
  verify service/API decisions using deterministic doubles and SQLite.

## 14. Task status

**COMPLETE.** Required external cleanup failures now prevent database deletion
and success responses. Focused deletion tests and the full backend harness
passed. The requested report is present and was verified as not ignored by Git.

## 15. Recommended next task

Proceed to the next approved roadmap item only after review and approval. Task
04 was not started.
