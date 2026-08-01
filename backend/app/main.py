from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.catalog import router as catalog_router
from app.api.practice import router as practice_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(title=settings.app_name)

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

