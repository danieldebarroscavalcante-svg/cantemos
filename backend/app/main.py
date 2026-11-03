import logging

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401 — registra todos os modelos antes do primeiro uso
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.assets.router import org_router as identity_router
from app.modules.assets.router import public_router as assets_router
from app.modules.auth.router import router as auth_router
from app.modules.broadcasts.router import router as broadcasts_router
from app.modules.checkin.router import org_router as reception_router
from app.modules.checkin.router import router as checkin_router
from app.modules.events.router import router as events_router
from app.modules.notifications.router import router as notifications_router
from app.modules.reports.router import router as reports_router
from app.modules.tickets.router import router as tickets_router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

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
api.include_router(events_router)
api.include_router(notifications_router)
api.include_router(tickets_router)
api.include_router(checkin_router)
api.include_router(reception_router)
api.include_router(broadcasts_router)
api.include_router(reports_router)
api.include_router(assets_router)
api.include_router(identity_router)


@api.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Usado pelo Render: só confirma que a API está de pé."""
    return {"status": "ok"}


@api.get("/health/db", tags=["infra"])
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Usado pelo monitor de uptime: consulta o banco, o que também evita que o banco
    gratuito (Aiven) seja desligado por inatividade."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Banco de dados indisponível.") from exc
    return {"status": "ok", "database": "ok"}


app.include_router(api)
