from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, utcnow
from app.db.types import str_enum


class CheckinMethod(StrEnum):
    QR = "qr"
    MANUAL = "manual"


class Checkin(IdMixin, Base):
    """Histórico de check-ins (inclusive os desfeitos) para auditoria."""

    __tablename__ = "checkins"

    ticket_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("event_sessions.id"), index=True)
    operator_user_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("users.id"))
    method: Mapped[CheckinMethod] = mapped_column(str_enum(CheckinMethod))
    gate: Mapped[str | None] = mapped_column(String(50))
    device_id: Mapped[str | None] = mapped_column(String(64))
    # Idempotência para sincronização offline (F2).
    client_uuid: Mapped[str | None] = mapped_column(String(36), unique=True)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime)
    undone_by_user_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"))
