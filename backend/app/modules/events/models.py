from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, IdMixin, PublicIdMixin, TimestampMixin
from app.db.types import str_enum


class EventStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"  # página no ar, inscrições ainda fechadas
    OPEN = "open"  # inscrições abertas
    CLOSED = "closed"  # inscrições encerradas
    FINISHED = "finished"


class Event(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "events"

    organization_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("organizations.id"), index=True
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(150))
    subtitle: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    banner_url: Mapped[str | None] = mapped_column(String(500))
    venue_name: Mapped[str | None] = mapped_column(String(150))
    venue_address: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[EventStatus] = mapped_column(str_enum(EventStatus), default=EventStatus.DRAFT)
    registration_opens_at: Mapped[datetime | None] = mapped_column(DateTime)
    registration_closes_at: Mapped[datetime | None] = mapped_column(DateTime)
    max_tickets_per_order: Mapped[int] = mapped_column(Integer, default=5)

    sessions: Mapped[list["EventSession"]] = relationship(
        back_populates="event", order_by="EventSession.starts_at"
    )


class EventSession(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "event_sessions"

    event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    doors_open_at: Mapped[datetime | None] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column(Integer)  # lugares físicos
    # Margem de inscrições acima da lotação para compensar faltas (no-show).
    overbooking_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Atualizado com UPDATE condicional para impedir overbooking (TKT-06).
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)

    event: Mapped[Event] = relationship(back_populates="sessions")

    @property
    def registration_limit(self) -> int:
        """Total de inscrições aceitas = lotação + margem."""
        return registration_limit(self.capacity, self.overbooking_percent)


def registration_limit(capacity: int, overbooking_percent: int) -> int:
    return capacity + (capacity * overbooking_percent) // 100
