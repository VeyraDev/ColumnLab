import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.api.datasets import import_router, router as datasets_router
from app.api.benchmarks import router as benchmarks_router
from app.api.queries import router as queries_router
from app.api.runtime import router as runtime_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.migrate import run_migrations

settings = get_settings()
logger = logging.getLogger("columnlab")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings.ensure_storage_dirs()
    Base.metadata.create_all(bind=engine)
    try:
        run_migrations(settings.resolved_database_url)
    except Exception as exc:
        logger.warning("Alembic migration skipped or failed: %s", exc)
    logger.info("ColumnLab backend started")
    yield
    logger.info("ColumnLab backend stopped")


app = FastAPI(title="ColumnLab", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": str(exc.detail), "data": None},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(import_router)
app.include_router(queries_router)
app.include_router(benchmarks_router)
app.include_router(runtime_router)
