import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.catalog import router as catalog_router
from app.api.practice import router as practice_router
from app.core.config import get_settings
from app.db.init_db import init_db


settings = get_settings()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    try:
        init_db()
        logger.info("Database initialized")
    except Exception:
        # The MVP can still serve fallback/generated content if PostgreSQL is not reachable.
        logger.exception("Database initialization failed; continuing with fallback/generated content")
        pass
    yield
    logger.info("Stopping %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(catalog_router)
app.include_router(practice_router)
