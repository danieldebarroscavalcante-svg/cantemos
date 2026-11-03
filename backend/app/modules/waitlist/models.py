from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, PublicIdMixin, TimestampMixin
from app.db.types import str_enum


class WaitlistStatus(StrEnum):
    WAITING = "waiting"  # na fila
    NOTIFIED = "notified"  # avisado: vaga guardada até hold_until
    REGISTERED = "registered"  # fez a inscrição
    EXPIRED = "expired"  # não usou a vaga a tempo
    LEFT = "left"  # saiu da fila


class WaitlistEntry(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "waitlist_entries"

    event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[WaitlistStatus] = mapped_column(
        str_enum(WaitlistStatus), default=WaitlistStatus.WAITING, index=True
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime)
    hold_until: Mapped[datetime | None] = mapped_column(DateTime)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)
