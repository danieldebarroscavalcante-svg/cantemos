from enum import StrEnum

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, TimestampMixin
from app.db.types import str_enum


class MessageKind(StrEnum):
    CONFIRMATION = "confirmation"  # ingresso confirmado
    REMINDER_CONFIRM = "reminder_confirm"  # faltam poucos dias
    REMINDER_TOMORROW = "reminder_tomorrow"  # é amanhã
    WAITLIST_JOINED = "waitlist_joined"  # entrou na lista de espera
    WAITLIST_INVITE = "waitlist_invite"  # abriu vaga


class MessageTemplate(IdMixin, TimestampMixin, Base):
    """Texto personalizado de um e-mail do evento (sem registro = texto padrão)."""

    __tablename__ = "message_templates"
    __table_args__ = (UniqueConstraint("event_id", "kind"),)

    event_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[MessageKind] = mapped_column(str_enum(MessageKind))
    subject: Mapped[str] = mapped_column(String(200))
    heading: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    button_label: Mapped[str] = mapped_column(String(60))
