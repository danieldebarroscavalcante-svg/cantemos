from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router

settings = get_settings()

app = FastAPI(
    title="EVENTMER API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api/v1")
api.include_router(auth_router)


@api.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api)
