"""Teste geral (painel): inscrição de teste para o próprio e-mail, para conferir todo o fluxo
(e-mail, ingressos, recepção, cancelamento, números) e removê-la depois."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import sign_order_token
from app.db.base import utcnow
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.events.router import EDIT_ROLES, VIEW_ROLES, _event_for
from app.modules.messages.service import ticket_email
from app.modules.notifications import email as email_module
from app.modules.tickets import service
from app.modules.tickets.models import Order, Ticket, TicketStatus
from app.modules.tickets.schemas import AttendeeIn, OrderIn

logger = logging.getLogger("eventmer.tickets")
router = APIRouter(prefix="/org/events/{slug}", tags=["organizador · teste geral"])


class TestOrderOut(BaseModel):
    code: str
    token: str
    email: str
    people: int
    valid: int
    present: int
    cancelled: int
    email_sent: bool


def _out(db: Session, order: Order) -> TestOrderOut:
    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    return TestOrderOut(
        code=order.code,
        token=sign_order_token(order.public_id),
        email=order.buyer_email,
        people=len(tickets),
        valid=sum(t.status == TicketStatus.VALID for t in tickets),
        present=sum(t.status == TicketStatus.USED for t in tickets),
        cancelled=sum(t.status == TicketStatus.CANCELLED for t in tickets),
        email_sent=order.email_sent_at is not None,
    )


@router.get("/test-registrations", response_model=list[TestOrderOut])
def list_tests(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, VIEW_ROLES)
    orders = db.scalars(
        select(Order).where(Order.event_id == event.id, Order.is_test).order_by(Order.id.desc())
    )
    return [_out(db, o) for o in orders]


@router.post("/test-registration", response_model=TestOrderOut, status_code=201)
def create_test(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, EDIT_ROLES)
    first = user.name.split()[0] if user.name else "Responsável"
    order = service.create_order(
        db,
        event.slug,
        OrderIn(
            buyer_name=f"TESTE · {user.name}",
            buyer_email=user.email,
            consent=True,
            source="teste-geral",
            attendees=[
                AttendeeIn(name=f"TESTE · {first}"),
                AttendeeIn(name="TESTE · Criança", age_group="crianca"),
                AttendeeIn(
                    name="TESTE · Idosa",
                    age_group="idoso",
                    priority=True,
                    accessibility_need="Cadeirante",
                ),
            ],
        ),
        is_test=True,
    )
    try:
        email_module.send_email(ticket_email(db, service.order_out(db, order)))
        order.email_sent_at = utcnow()
        db.commit()
    except email_module.EmailError:
        logger.exception("Teste geral: e-mail não enviado")
    return _out(db, order)


@router.delete("/test-registrations")
def delete_tests(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, EDIT_ROLES)
    removed = service.delete_test_orders(db, event)
    return {"removed": removed}
