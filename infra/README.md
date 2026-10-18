# Local runtime configuration

The supported local runtime uses Docker Compose for PostgreSQL, Redis/RQ,
Qdrant, MinIO, the FastAPI API, the ingestion worker, and (optionally) the
Next.js UI. The Compose file publishes service ports on loopback only.

## Prepare local secrets

From the repository root, copy `.env.example` to `.env` and fill every blank
secret with a cryptographically random value. Use different random
values for the PostgreSQL password, JWT signing key, MinIO root username, and
MinIO root password. The MinIO application access key must equal
`MINIO_ROOT_USER`, and its secret must equal `MINIO_ROOT_PASSWORD`.
`DATABASE_URL` must use the same PostgreSQL username and password as
`POSTGRES_USER` and `POSTGRES_PASSWORD`. Use URL-safe characters for secrets
embedded in `DATABASE_URL`.

Keep `.env` local; it is ignored by Git. Do not commit it or paste its contents
into logs, issue trackers, or chat. `.env.example` contains replacement
instructions, not credentials.

## Start the Compose runtime

Run these commands from the repository root so the application can load `.env`
from its configured working directory. Passing `--env-file` explicitly also
ensures Compose uses that root file even though the Compose definition is under
`infra/`.

```powershell
docker compose --env-file .env -f infra\docker-compose.yml config
docker compose --env-file .env -f infra\docker-compose.yml up --build
```

To include the frontend:

```powershell
docker compose --env-file .env -f infra\docker-compose.yml --profile ui up --build
```

Published ports are bound to `127.0.0.1`. The API and frontend can be reached
locally at `http://localhost:8000` and `http://localhost:3000`; the database,
Redis, Qdrant, and MinIO ports are likewise limited to the local host. The API
and worker use Compose service DNS names internally.

Compose builds the API from `backend/Dockerfile` and the worker from
`workers/Dockerfile`. It selects PostgreSQL, RQ, MinIO/S3, Qdrant, Sentence
Transformers, and Hugging Face inference. The model cache is stored in the
Compose-managed `hf_cache` volume.

## Run services directly on the host

Direct application startup reads `.env` relative to the current working
directory. Start commands from the repository root; otherwise the root `.env`
may not be found. Direct startup expects PostgreSQL, Redis, Qdrant, and MinIO
to be reachable on the `localhost` URLs in `.env`, and the Python environment
must have both backend dependency sets installed.

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
python -m workers.worker
```

Direct startup uses the backend selectors in `.env`. The local template selects
the persistent services and real embedding/model implementations. Without a
configured `.env`, `backend/app/config.py` falls back to SQLite, memory storage,
a no-op queue, memory vectors, hash embeddings, a stub LLM, and a development
JWT key; do not use those fallbacks for the MVP runtime.

## Environment variables

| Variable(s) | Purpose | Direct host | Compose |
|---|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL credentials and database name | `DATABASE_URL` must match | Compose interpolates these into PostgreSQL and the API database URL |
| `DATABASE_URL` | SQLAlchemy database connection | PostgreSQL on `localhost` | Compose constructs its own URL using `postgres` service DNS |
| `REDIS_URL` | RQ connection | Redis on `localhost` | Compose uses `redis` service DNS |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | JWT signing key and token lifetime | Read from `.env` | Passed to API and worker |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | MinIO root credentials | Match the app access-key pair | Passed to MinIO and mapped to the app access-key pair |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` | S3-compatible object storage | MinIO on `localhost` | Compose supplies service DNS and credentials |
| `QDRANT_URL`, `QDRANT_COLLECTION` | Vector database endpoint and collection | Qdrant on `localhost` | Compose uses `qdrant` service DNS |
| `CORS_ORIGINS` | Allowed browser origins | Defaults to local frontend | Passed to API and worker |
| `MAX_PDF_BYTES`, `MAX_PDF_PAGES` | Upload validation limits | Defaults to 20 MiB and 80 pages | Passed to API and worker |
| `STORAGE_BACKEND`, `QUEUE_BACKEND`, `VECTOR_BACKEND`, `EMBEDDING_BACKEND`, `LLM_BACKEND` | Select storage, queue, vector, embedding, and LLM implementations | Read from `.env`; use `s3`, `rq`, `qdrant`, `st`, `hf` | Compose selects those implementations in its service environment |
| `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `LLM_MODEL`, `HF_HOME` | Model names, vector size, and model cache path | Read from `.env` | Model names are interpolated; cache path is `/models` in containers |
| `PROMPT_VERSION`, `RETRIEVAL_VERSION`, `RETRIEVAL_TOP_K` | Answer/retrieval metadata and retrieval limit | Read from `.env` | Version labels are interpolated; top-k uses the application default |
| `NEXT_PUBLIC_API_URL` | Browser-facing API base URL | Defaults to local API | Passed as both a frontend build argument and runtime environment value |

Compose intentionally sets service-network URLs and ML backends in the
container environment; host-facing `localhost` URLs in `.env` are for direct
host startup. Compose does not use `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT`,
or `QDRANT_URL` from `.env`; it supplies the corresponding internal service
addresses instead.
