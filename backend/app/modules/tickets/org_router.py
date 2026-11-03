"""Inscritos do evento no painel: consulta, correção de dados, reenvio e cancelamento."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.timezone import utc_to_local
from app.db.base import utcnow
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event
from app.modules.events.router import EDIT_ROLES, VIEW_ROLES, _event_for
from app.modules.messages.service import ticket_email
from app.modules.notifications.email import EmailError, send_email
from app.modules.tickets import service
from app.modules.tickets.models import Order, OrderStatus, Ticket, TicketKind, TicketType
from app.modules.tickets.schemas import CancelIn
from app.modules.waitlist import service as waitlist

logger = logging.getLogger("eventmer.registrations")
router = APIRouter(prefix="/org/events/{slug}/registrations", tags=["organizador · inscritos"])


class RegistrationTicket(BaseModel):
    id: str
    attendee_name: str
    age_group: str
    ticket_type: str
    priority: bool
    accessibility_need: str | None
    status: str
    checked_in_at: str | None


class Registration(BaseModel):
    code: str
    status: str
    buyer_name: str
    buyer_email: str
    buyer_phone: str | None
    source: str | None
    is_test: bool
    registered_at: str
    email_sent: bool
    tickets: list[RegistrationTicket]


class AttendeeNameIn(BaseModel):
    id: str
    name: str = Field(min_length=2, max_length=150)


class RegistrationUpdate(BaseModel):
    buyer_name: str = Field(min_length=2, max_length=150)
    buyer_email: EmailStr
    buyer_phone: str | None = Field(default=None, max_length=30)
    attendees: list[AttendeeNameIn] = Field(default_factory=list, max_length=50)


def _clean(text: str) -> str:
    return " ".join(text.split())


def _out(db: Session, orders: list[Order]) -> list[Registration]:
    if not orders:
        return []
    rows = db.execute(
        select(Ticket, TicketType)
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .where(Ticket.order_id.in_([o.id for o in orders]))
        .order_by(Ticket.id)
    ).all()
    by_order: dict[int, list[RegistrationTicket]] = {o.id: [] for o in orders}
    for t, tt in rows:
        by_order[t.order_id].append(
            RegistrationTicket(
                id=t.public_id,
                attendee_name=t.attendee_name,
                age_group=t.age_group.value,
                ticket_type=tt.name,
                priority=tt.kind == TicketKind.PRIORITY or bool(t.accessibility_need),
                accessibility_need=t.accessibility_need,
                status=t.status.value,
                checked_in_at=f"{utc_to_local(t.checked_in_at):%d/%m %H:%M}"
                if t.checked_in_at
                else None,
            )
        )
    return [
        Registration(
            code=o.code,
            status=o.status.value,
            buyer_name=o.buyer_name,
            buyer_email=o.buyer_email,
            buyer_phone=o.buyer_phone,
            source=o.source,
            is_test=o.is_test,
            registered_at=f"{utc_to_local(o.created_at):%d/%m/%Y %H:%M}",
            email_sent=o.email_sent_at is not None,
            tickets=by_order[o.id],
        )
        for o in orders
    ]


def _order(db: Session, event: Event, code: str) -> Order:
    order = db.scalar(select(Order).where(Order.event_id == event.id, Order.code == code.upper()))
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inscrição não encontrada.")
    return order


@router.get("", response_model=list[Registration])
def list_registrations(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Todas as inscrições do evento, da mais recente para a mais antiga."""
    event = _event_for(db, user, slug, VIEW_ROLES)
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.event_id == event.id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
    )
    return _out(db, orders)


@router.put("/{code}", response_model=Registration)
def update_registration(
    slug: str,
    code: str,
    payload: RegistrationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Corrige nome, e-mail e telefone do responsável e os nomes dos participantes."""
    event = _event_for(db, user, slug, EDIT_ROLES)
    order = _order(db, event, code)
    email = normalize_email(str(payload.buyer_email))
    if email != order.buyer_email and not order.is_test:
        taken = db.scalar(
            select(Order.code).where(
                Order.event_id == event.id,
                Order.buyer_email == email,
                Order.status == OrderStatus.CONFIRMED,
                Order.is_test.is_(False),
                Order.id != order.id,
            )
        )
        if taken:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"Este e-mail já está na inscrição {taken}."
            )
    found = db.scalars(select(Ticket).where(Ticket.order_id == order.id))
    tickets = {t.public_id: t for t in found}
    if any(a.id not in tickets for a in payload.attendees):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não está nesta inscrição.")
    names = {a.id: _clean(a.name) for a in payload.attendees}
    if any(len(n) < 2 for n in names.values()) or len(_clean(payload.buyer_name)) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Preencha os nomes completos.")

    if email != order.buyer_email:
        # A inscrição passa para a conta "leve" do novo e-mail; a conta antiga não é alterada.
        order.buyer_user_id = service._buyer(db, email, _clean(payload.buyer_name), None).id
        order.buyer_email = email
    order.buyer_name = _clean(payload.buyer_name)
    order.buyer_phone = _clean(payload.buyer_phone or "") or None
    for ticket_id, name in names.items():
        tickets[ticket_id].attendee_name = name
    db.commit()
    logger.info("Inscrição %s corrigida por %s", order.code, user.email)
    return _out(db, [order])[0]


@router.post("/{code}/resend", response_model=Registration)
def resend_registration(
    slug: str, code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Reenvia o e-mail com os ingressos para o responsável."""
    event = _event_for(db, user, slug, VIEW_ROLES)
    order = _order(db, event, code)
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta inscrição foi cancelada.")
    try:
        send_email(ticket_email(db, service.order_out(db, order)))
    except EmailError as exc:
        logger.exception("Falha ao reenviar o ingresso da inscrição %s", order.code)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Não foi possível enviar o e-mail agora. Tente de novo."
        ) from exc
    order.email_sent_at = utcnow()
    db.commit()
    return _out(db, [order])[0]


@router.post("/{code}/cancel", response_model=Registration)
def cancel_registration(
    slug: str,
    code: str,
    payload: CancelIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancela a inscrição inteira (lista vazia) ou só algumas pessoas; a vaga volta ao público."""
    event = _event_for(db, user, slug, EDIT_ROLES)
    order = service.cancel(db, _order(db, event, code), payload.ticket_ids)
    logger.info("Inscrição %s: cancelamento feito por %s", order.code, user.email)
    waitlist.notify_next(db, event)
    db.refresh(order)
    return _out(db, [order])[0]
