from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.workspaces import router as workspaces_router
from app.config import get_settings
from app.database import Base, get_engine
from app.runtime import get_runtime


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=get_engine())
    get_runtime()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Research Intelligence Workspace", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(workspaces_router)
    app.include_router(documents_router)
    app.include_router(ask_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
