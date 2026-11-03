from collections import Counter

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.timezone import utc_to_local
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.events.router import VIEW_ROLES, _event_for
from app.modules.events.service import main_session
from app.modules.tickets.models import (
    Order,
    OrderStatus,
    Ticket,
    TicketKind,
    TicketStatus,
    TicketType,
)
from app.modules.waitlist.models import WaitlistEntry

router = APIRouter(prefix="/org/events/{slug}", tags=["organizador · números"])


class Count(BaseModel):
    label: str
    people: int


class Stats(BaseModel):
    capacity: int
    registration_limit: int
    registered: int  # pessoas com ingresso válido ou já usado
    present: int
    cancelled: int
    orders: int
    priority: int
    by_age: list[Count]
    by_day: list[Count]
    by_source: list[Count]
    waitlist: list[Count]
    emails_not_sent: int  # inscrições confirmadas cujo e-mail do ingresso falhou


AGE = {"adulto": "Adultos", "crianca": "Crianças", "idoso": "Idosos"}
WAIT = {
    "waiting": "Aguardando",
    "notified": "Avisados (vaga guardada)",
    "registered": "Inscritos pela lista",
    "expired": "Não usaram a vaga",
    "left": "Saíram",
}


@router.get("/stats", response_model=Stats)
def stats(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, VIEW_ROLES)
    session = main_session(db, event)
    rows = db.execute(
        select(Ticket, Order, TicketType.kind)
        .join(Order, Order.id == Ticket.order_id)
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .where(Order.event_id == event.id)
    ).all()
    active = [(t, o, k) for t, o, k in rows if t.status in (TicketStatus.VALID, TicketStatus.USED)]

    by_age = Counter(t.age_group.value for t, _, _ in active)
    by_day = Counter(f"{utc_to_local(o.created_at):%d/%m}" for _, o, _ in rows)
    by_source = Counter((o.source or "Link direto") for _, o, _ in active)
    waitlist = Counter(
        s.value
        for s in db.scalars(select(WaitlistEntry.status).where(WaitlistEntry.event_id == event.id))
    )
    orders = {o.id: o for _, o, _ in rows}
    return Stats(
        capacity=session.capacity,
        registration_limit=session.registration_limit,
        registered=len(active),
        present=sum(1 for t, _, _ in active if t.status == TicketStatus.USED),
        cancelled=sum(1 for t, _, _ in rows if t.status == TicketStatus.CANCELLED),
        orders=sum(1 for o in orders.values() if o.status == OrderStatus.CONFIRMED),
        priority=sum(1 for t, _, k in active if k == TicketKind.PRIORITY or t.accessibility_need),
        by_age=[Count(label=AGE[k], people=by_age.get(k, 0)) for k in AGE],
        by_day=[
            Count(label=day, people=n)
            for day, n in sorted(by_day.items(), key=lambda kv: kv[0][3:] + kv[0][:2])
        ],
        by_source=[Count(label=s, people=n) for s, n in by_source.most_common()],
        waitlist=[Count(label=WAIT[k], people=waitlist[k]) for k in WAIT if waitlist.get(k)],
        emails_not_sent=sum(
            1
            for o in orders.values()
            if o.status == OrderStatus.CONFIRMED and o.email_sent_at is None
        ),
    )
