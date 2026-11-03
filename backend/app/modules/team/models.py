from enum import StrEnum

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, TimestampMixin
from app.db.types import str_enum


class EventRole(StrEnum):
    ADMIN = "admin"  # administra o evento (configura, comunica, equipe)
    MANAGER = "manager"  # produção: acompanha, exporta, recepção
    CHECKIN = "checkin"  # recepção com login: só o check-in


class EventMember(IdMixin, TimestampMixin, Base):
    """Pessoa da equipe de um evento específico (além dos responsáveis da igreja)."""

    __tablename__ = "event_members"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[EventRole] = mapped_column(str_enum(EventRole))
    invited_by_user_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="SET NULL")
    )
