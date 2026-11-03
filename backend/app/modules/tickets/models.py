from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK, IdMixin, PublicIdMixin, TimestampMixin
from app.db.types import str_enum


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class TicketStatus(StrEnum):
    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"
    TRANSFERRED = "transferred"


class AgeGroup(StrEnum):
    ADULT = "adulto"
    CHILD = "crianca"
    SENIOR = "idoso"


class TicketKind(StrEnum):
    GENERAL = "general"  # inscrição pública
    PRIORITY = "priority"  # PCD, idosos, gestantes
    RESERVED = "reserved"  # cota interna (coral, equipe, convidados) emitida pela secretaria


class TicketType(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "ticket_types"

    session_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("event_sessions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[TicketKind] = mapped_column(
        str_enum(TicketKind), default=TicketKind.GENERAL, server_default=TicketKind.GENERAL.value
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(300))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    quantity: Mapped[int] = mapped_column(Integer)
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)
    max_per_order: Mapped[int | None] = mapped_column(Integer)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False)  # PCD, idosos, gestantes
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)  # cota interna / pré-venda
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Order(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    code: Mapped[str] = mapped_column(String(16), unique=True)  # ex.: CNT-7K3P9
    organization_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("organizations.id"), index=True
    )
    event_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("events.id"), index=True)
    buyer_user_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("users.id"), index=True)
    buyer_name: Mapped[str] = mapped_column(String(150))
    buyer_email: Mapped[str] = mapped_column(String(255), index=True)
    buyer_phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus), default=OrderStatus.CONFIRMED
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    source: Mapped[str | None] = mapped_column(String(80))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")


class Ticket(IdMixin, PublicIdMixin, TimestampMixin, Base):
    __tablename__ = "tickets"

    order_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    ticket_type_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("ticket_types.id"))
    session_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("event_sessions.id"), index=True)
    attendee_name: Mapped[str] = mapped_column(String(150), index=True)
    age_group: Mapped[AgeGroup] = mapped_column(str_enum(AgeGroup), default=AgeGroup.ADULT)
    accessibility_need: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[TicketStatus] = mapped_column(str_enum(TicketStatus), default=TicketStatus.VALID)
    # Preenchido com UPDATE condicional (status valid -> used) para impedir check-in duplo.
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)

    order: Mapped[Order] = relationship(back_populates="tickets")
