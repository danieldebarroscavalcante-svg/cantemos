from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, TimestampMixin
from app.db.types import str_enum


class BroadcastKind(StrEnum):
    CONFIRM = "confirm"  # "faltam poucos dias — não vai? cancele"
    TOMORROW = "tomorrow"  # "é amanhã", com os QR Codes


class BroadcastStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"


class Broadcast(IdMixin, TimestampMixin, Base):
    """Envio em massa de lembretes para os inscritos (com progresso)."""

    __tablename__ = "broadcasts"

    event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[BroadcastKind] = mapped_column(str_enum(BroadcastKind))
    status: Mapped[BroadcastStatus] = mapped_column(
        str_enum(BroadcastStatus), default=BroadcastStatus.RUNNING
    )
    requested_by: Mapped[str] = mapped_column(String(150))
    total: Mapped[int] = mapped_column(Integer, default=0)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
