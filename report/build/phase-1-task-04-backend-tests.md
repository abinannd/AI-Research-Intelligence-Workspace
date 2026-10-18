# Phase 1 — Task 04: Backend API and Workspace-Isolation Tests

## 1. Objective

Strengthen the backend test harness for authentication, workspace ownership,
document isolation, request validation, and protection against cross-user
mutations without redesigning production behavior.

## 2. Files inspected

- [`backend/tests/conftest.py`](../../backend/tests/conftest.py) — isolated
  SQLite database, FastAPI client, authentication and workspace fixtures.
- [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py) —
  existing API, upload, deletion, retrieval, and citation tests.
- [`backend/app/security.py`](../../backend/app/security.py) — token creation,
  token decoding, and current-user lookup.
- [`backend/app/api/auth.py`](../../backend/app/api/auth.py) — signup, login,
  and current-user routes and response behavior.
- [`backend/app/api/workspaces.py`](../../backend/app/api/workspaces.py) and
  [`backend/app/workspaces/service.py`](../../backend/app/workspaces/service.py)
  — workspace list/create/retrieval and owner-filtered lookup.
- [`backend/app/api/documents.py`](../../backend/app/api/documents.py) and
  [`backend/app/documents/service.py`](../../backend/app/documents/service.py)
  — document list/file/delete paths and workspace ownership checks.
- [`backend/app/api/ask.py`](../../backend/app/api/ask.py) — workspace
  ownership check and request validation before answer processing.
- [`backend/app/models.py`](../../backend/app/models.py) — user, workspace,
  and document ownership relationships.
- [`backend/app/schemas.py`](../../backend/app/schemas.py) — auth, workspace,
  document, and ask request/response schemas.
- Prior Task 01, Task 02, and Task 03 reports were consulted for context;
  source behavior relevant to this task was checked against the current code.

## 3. Existing coverage and identified gaps

The harness already tested health, signup and `/api/auth/me` using a signup
token, SQLite fixture persistence, PDF validation and upload limits, document
deletion success/failure/rollback, in-memory vector isolation, and citation
grounding.

Before this task, the shared `auth_user` fixture's token had no exercised
protected-route use. The harness did not cover missing or malformed bearer
credentials, a second user being denied access to another user's workspace
and documents, or whether a rejected cross-user delete leaves the other
user's data and external resources unchanged. Missing workspace fields and
nonexistent workspace/document IDs also lacked focused API assertions.

## 4. Files modified and reasons

- **Modified:** [`backend/tests/conftest.py`](../../backend/tests/conftest.py)
  — corrected the auth fixture to pass the user ID string expected by
  `create_access_token`.
- **Modified:** [`backend/tests/test_harness.py`](../../backend/tests/test_harness.py)
  — added focused API-level authentication, ownership/isolation, non-mutation,
  and request-validation tests. Existing tests were preserved.
- **Created:** this report.

No production application code, API schema, database schema, migrations,
configuration, frontend, CI, or `.gitignore` files were changed for Task 04.
The pre-existing Task 03 harness and report modifications were preserved.

## 5. Tests added or changed

Four tests were added:

1. Missing credentials and a non-Bearer authorization scheme return the
   observed HTTP 403 response; an invalid bearer token returns HTTP 401 with
   the existing `Invalid token` detail.
2. The corrected fixture token authenticates through `/api/auth/me` and
   permits access to the user's workspace and workspace list.
3. A second user creates an independent workspace and document. The first
   user receives HTTP 404 for the second user's workspace, document list,
   document file, delete, and ask endpoints. The second user's workspace and
   document remain in the database, and storage/vector deletion doubles record
   no calls.
4. An authenticated request with a missing workspace name returns HTTP 422;
   nonexistent workspace and workspace/document file IDs return HTTP 404.

The tests use the existing per-test in-memory SQLite fixture and deterministic
storage/vector test doubles. They do not require live PostgreSQL, Redis,
Qdrant, MinIO, or model downloads.

## 6. Test-infrastructure defect and fix

The `auth_user` fixture called `create_access_token({"sub": user.id})`, while
the actual function signature is `create_access_token(user_id: str)`. The auth
route itself passes `user.id`. Updated the fixture to use that same string
argument and added a protected-route test that verifies the resulting token
works. No production authentication defect was demonstrated.

## 7. Commands executed and actual results

| Command | Actual result |
|---|---|
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider -k "protected_api or fixture_authenticates or user_cannot_access or authenticated_api_validates"` | **Passed:** 4 passed, 18 deselected, 2 warnings. |
| `C:\Python310\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider` | **Passed:** 22 passed, 2 warnings. |
| `git diff --check` | **Passed:** no whitespace errors. Git printed non-fatal LF/CRLF working-copy warnings for modified Python files. |

Warnings observed in both pytest runs:

- Starlette's multipart parser emits a `PendingDeprecationWarning`
  recommending `python_multipart`.
- Pydantic warns that `AskOut.model_version` conflicts with the protected
  `model_` namespace.

No dependencies were installed, no services were started, no migrations were
run, and no commit or push was performed.

## 8. Full backend test result

The complete requested backend harness command passed: **22 passed, 0 failed,
2 warnings** in 5.95 seconds. This includes existing upload-size and Task 03
deletion regression tests.

## 9. `git diff --check`

**Passed.** The command reported no whitespace errors. Git emitted only
non-fatal working-copy line-ending warnings (LF will be replaced by CRLF) for
the modified Python files.

## 10. Report tracking and Git-ignore verification

The required report was checked at
`report/build/phase-1-task-04-backend-tests.md`.

- `git check-ignore -v report/build/phase-1-task-04-backend-tests.md`:
  **no matching rule**; command exit code 1, which is Git's expected result
  when the path is not ignored.
- `git status --short --untracked-files=all` included:
  ```text
   M backend/tests/conftest.py
   M backend/tests/test_harness.py
   M report/build/phase-1-task-03-document-deletion.md
  ?? report/build/phase-1-task-04-backend-tests.md
  ```
  The Task 03 report modification was already present and preserved. The Task
  04 report is visible as an untracked file.

No ignore rule was added or changed to hide this report or other
`report/build/` files.

## 11. API-contract impact

No API contract or production API behavior changed. The tests assert the
existing authentication, ownership, and request-validation response
conventions.

## 12. Known limitations and unresolved risks

- Tests use the existing in-memory SQLite and test-double setup; they do not
  verify live PostgreSQL, external storage, Qdrant, or worker behavior.
- Representative workspace-scoped endpoints were tested rather than every
  route permutation. Existing route code still provides the ownership checks
  for retry and upload; those paths were not expanded as part of this focused
  test task.
- The existing dependency/model warnings remain unchanged and were not fixed
  because they are outside scope.

## 13. Task status

**COMPLETE.** The fixture token mismatch was corrected, representative
authentication and workspace-isolation gaps were covered at the API level,
and the complete backend harness passed.

## 14. Recommended next task

Submit Task 04 for review and wait for approval before selecting or beginning
another task.
