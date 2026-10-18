# Python Environment Recovery

## Initial environment diagnosis

- Project root: `C:\BRAIN-STORM\AI Research Intelligence Workspace`.
- `C:\Python310\python.exe` executed successfully and reported Python
  **3.10.6** (64-bit).
- Three top-level Python virtual environments were present:
  - `.venv` had `pyvenv.cfg` and `Scripts\python.exe`; it was a Python
    **3.10.6** venv.
  - `.venv-1` had `pyvenv.cfg` and `Scripts\python.exe`; it was a Python
    **3.14** venv created by uv.
  - `.venv-py314-backup` had `pyvenv.cfg` and `Scripts\python.exe`; it was a
    Python **3.14** venv created by uv.
- Two Uvicorn processes were identified by their command lines as belonging to
  this project. The process using `.venv` was stopped before cleanup. The
  second host-Python process exited before it could be stopped; a second
  process check confirmed no project Uvicorn process remained.
- The PowerShell session had no `VIRTUAL_ENV` or `CONDA_PREFIX` set.
- `.gitignore` contains `.venv/`; Git confirms the newly created `.venv` is
  ignored.
- Required and development dependency files are
  [`backend/requirements.txt`](../backend/requirements.txt) and
  [`backend/requirements-dev.txt`](../backend/requirements-dev.txt).
  Optional model dependencies are in
  [`backend/requirements-ml.txt`](../backend/requirements-ml.txt).
- No requirements files, backend source, `.env`, or `.env.example` were
  modified. Secret values were not printed or recorded.

## Environment directories removed and recreated

Removed only these verified Python environment directories, all resolved
inside the project root:

- `.venv` (old Python 3.10.6 environment)
- `.venv-1` (Python 3.14 environment)
- `.venv-py314-backup` (Python 3.14 environment)

Created a new `.venv` using the requested
`C:\Python310\python.exe -m venv .venv`. The final environment is Python
**3.10.6**, and `sys.executable` resolves to:

`C:\BRAIN-STORM\AI Research Intelligence Workspace\.venv\Scripts\python.exe`

Pip is installed within the new environment and reports **26.2.1**. The venv
is ignored by the existing `.gitignore` rule.

## Dependency installation

Installed the pinned application and development dependencies into the new
environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
```

The install completed successfully with exit code 0. Direct versions specified
by the requirements files were installed, including FastAPI 0.115.6,
SQLAlchemy 2.0.36, psycopg2-binary 2.9.10, Pydantic 2.10.4,
pydantic-settings 2.7.0, Uvicorn 0.34.0, pytest 8.3.4, and the declared
database, storage, queue, vector client, PDF, and HTTP dependencies.

Pip was upgraded inside `.venv` from 22.2.1 to 26.2.1. The upgrade command
completed successfully; pip emitted a warning that it could not check for the
latest version.

### Optional ML dependencies

`backend/requirements-ml.txt` specifies Sentence Transformers 3.3.1,
Transformers 4.47.1, and Accelerate 1.2.1. These are needed when the configured
Sentence Transformers embedding adapter actually embeds documents/queries and
when the Hugging Face language-model adapter performs inference. Model
downloads are also needed for those operations.

They were **not installed**: application startup creates these adapters
lazily, and their model libraries are imported when embedding or inference is
requested. They are not needed for the current isolated backend tests or for
checking imports, and installing them would bring in large ML dependencies.
They must be installed before exercising real document ingestion, embedding,
or answer generation with the current `st`/`hf` selectors.

## Dependency consistency and import checks

`pip check` completed with exit code 0:

```text
No broken requirements found.
```

Imports succeeded from the new venv for FastAPI, SQLAlchemy, Pydantic
Settings, psycopg2, Uvicorn, Boto3, Qdrant client, Redis, RQ, PyMuPDF, PyJWT,
bcrypt, multipart, and httpx. `import app.main` also succeeded without
starting the application lifespan.

## Backend tests

Executed from the project root using the new environment:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_harness.py -q -p no:cacheprovider
```

**Result: 22 passed in 5.97 seconds**, exit code 0. The tests use the existing
isolated SQLite/test-double fixtures; this result does not prove live
PostgreSQL, Redis, Qdrant, MinIO, or model operation.

## Runtime configuration and infrastructure diagnosis

The `.env` file was not printed. The selected non-secret backend identifiers
read from it are:

- Storage: `s3`
- Queue: `rq`
- Vector store: `qdrant`
- Embeddings: `st`
- LLM: `hf`

The configured database URL parses as driver `postgresql+psycopg2`, host
`localhost`, port `5432`. Username, password, and database URL were not
printed. Per [`backend/app/main.py`](../backend/app/main.py), FastAPI lifespan
creates database tables and initializes the runtime. With these selected
backends, initialization contacts PostgreSQL, Qdrant, and MinIO; Redis is
required for the RQ queue during job enqueue/processing.

Infrastructure checks found:

- Docker CLI: unavailable (`docker` was not found in PATH).
- Docker Desktop: no executable found in the checked standard install paths,
  no installed-app registry entry found, and no Docker Desktop process or
  `com.docker.service` was detected. Docker Desktop was not detected on this
  machine.
- PostgreSQL Windows service: none found.
- Local TCP ports **5432**, **6379**, **6333**, **9000**, and **9001** were all
  closed at the time of checking.

The intended service setup in
[`infra/docker-compose.yml`](../infra/docker-compose.yml) is PostgreSQL 16,
Redis 7, Qdrant 1.12.5, and MinIO, with the API/worker selecting PostgreSQL,
RQ, S3-compatible storage, Qdrant, Sentence Transformers, and Hugging Face.
[`infra/README.md`](../infra/README.md) documents Compose startup and cautions
that `.env` contains local secrets.

Because Docker and the required service endpoints are unavailable, Uvicorn
was **not started**, the `/health` endpoint was **not tested**, and frontend
login was **not verified**. This is an infrastructure blocker, not a Python
dependency or application-import failure. No system software was installed
and no services were launched.

## Files changed

- Created this report.
- Removed and recreated only the named ignored virtual environment
  directories. `.venv` is ignored by Git.
- No source code, tests, requirements files, `.env`, `.env.example`,
  infrastructure files, database schema, or ignore rules were changed.

## Commands executed and results

| Command/check | Result |
|---|---|
| `C:\Python310\python.exe --version` and version/executable probe | Passed; Python 3.10.6 at `C:\Python310\python.exe`. |
| Project-process inspection and targeted stop | Stopped the verified `.venv` Uvicorn process; second process had exited on recheck; final check found none. |
| Exact-target venv verification | Confirmed all three named directories were in the project root and had `pyvenv.cfg` plus `Scripts\python.exe`. |
| `C:\Python310\python.exe -m venv .venv` | Passed; new venv created. |
| `.venv` Python/pip verification | Passed; Python 3.10.6, executable points inside project `.venv`, pip 22.2.1 initially. |
| `.venv\Scripts\python.exe -m pip install --upgrade pip` | Passed; pip upgraded to 26.2.1. Non-fatal latest-version-check warning. |
| `.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt` | Passed; exit code 0. |
| `.venv\Scripts\python.exe -m pip check` | Passed; no broken requirements. |
| Application dependency import probe and `import app.main` | Passed; all listed dependencies and the application module imported. |
| Full backend test harness command above | Passed; 22 passed. |
| Docker/service/port checks | Docker CLI and Docker Desktop not detected; PostgreSQL service absent; all checked infrastructure ports closed. |
| Uvicorn and `/health` | Not run because PostgreSQL, Qdrant, and MinIO prerequisites were unavailable. |
| `git check-ignore -v .venv` | Matched `.gitignore:2:.venv/`; environment remains ignored. |

## Report visibility

- `git check-ignore -v report/build/python-environment-recovery.md` returned
  no matching rule (Git exit code 1, expected for a non-ignored report).
- `git status --short --untracked-files=all` showed this report as untracked.
- No ignore rule was added or changed.

## Remaining blocker and exact next commands

The Python environment is clean and reproducible, but the API cannot complete
startup or serve frontend authentication until its configured services are
available. Docker Desktop was not detected and must be installed/started by
the user or an administrator; system software was not installed by this task.
After Docker Desktop is available and the user authorizes service startup, run
from the project root:

```powershell
docker compose --env-file .env -f infra\docker-compose.yml up -d postgres redis qdrant minio
```

Verify service readiness without printing `.env`:

```powershell
Test-NetConnection 127.0.0.1 -Port 5432
Test-NetConnection 127.0.0.1 -Port 6379
Test-NetConnection 127.0.0.1 -Port 6333
Test-NetConnection 127.0.0.1 -Port 9000
```

When PostgreSQL, Qdrant, and MinIO are reachable, start the API from the
project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir backend
```

Then, in another terminal, test the health endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Do not use the real `st`/`hf` ingestion and Q&A workflows until
`backend/requirements-ml.txt` is installed into `.venv` and model availability
is addressed.

## Status

**COMPLETE — Python environment recovery and offline backend verification.**
**Runtime startup remains blocked by unavailable infrastructure.** The API
startup and health-check criteria could not be verified, and frontend login
must not be considered tested.
