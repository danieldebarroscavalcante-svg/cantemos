"""Credenciamento: leitura do QR, busca por nome, entrada da família e contadores."""

import secrets
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.security import checkin_code_fingerprint, decode_token, verify_qr
from app.core.timezone import utc_to_local
from app.db.base import utcnow
from app.modules.auth.models import User
from app.modules.checkin.models import Checkin, CheckinMethod
from app.modules.checkin.schemas import (
    AttendeeOut,
    CheckinResult,
    OrderBrief,
    Summary,
)
from app.modules.events.models import Event
from app.modules.events.service import main_session
from app.modules.organizations.models import OrganizationMember, Role
from app.modules.tickets.models import Order, Ticket, TicketKind, TicketStatus, TicketType

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
OPERATOR_ROLES = (Role.OWNER, Role.ADMIN, Role.MANAGER, Role.CHECKIN)


@dataclass
class Operator:
    event: Event
    name: str
    user_id: int | None
    is_staff: bool  # equipe com login (pode desfazer qualquer entrada)


def new_checkin_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def event_by_slug(db: Session, slug: str) -> Event:
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


def resolve_operator(db: Session, slug: str, token: str | None) -> Operator:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Acesso da recepção expirado. Entre novamente."
    )
    payload = decode_token(token) if token else None
    if payload is None:
        raise unauthorized
    event = event_by_slug(db, slug)

    if payload.get("type") == "access":
        user = db.get(User, int(payload["sub"]))
        role = db.scalar(
            select(OrganizationMember.role).where(
                OrganizationMember.user_id == user.id if user else False,
                OrganizationMember.organization_id == event.organization_id,
            )
        )
        if user is None or not user.is_active or role not in OPERATOR_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso à recepção deste evento.")
        return Operator(event=event, name=user.name, user_id=user.id, is_staff=True)

    if payload.get("type") == "checkin":
        if (
            payload.get("event") != event.id
            or not event.checkin_code
            or payload.get("cv") != checkin_code_fingerprint(event.checkin_code)
        ):
            raise unauthorized
        return Operator(event=event, name=str(payload["name"]), user_id=None, is_staff=False)

    raise unauthorized


# ---------------------------------------------------------------- leitura


def summary(db: Session, event: Event) -> Summary:
    session = main_session(db, event)
    rows = db.execute(
        select(Ticket.status, TicketType.kind, Ticket.accessibility_need, func.count())
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .where(Ticket.session_id == session.id)
        .group_by(Ticket.status, TicketType.kind, Ticket.accessibility_need)
    ).all()
    registered = sum(n for st, _, _, n in rows if st in (TicketStatus.VALID, TicketStatus.USED))
    present = sum(n for st, _, _, n in rows if st == TicketStatus.USED)
    priority_present = sum(
        n
        for st, kind, need, n in rows
        if st == TicketStatus.USED and (kind == TicketKind.PRIORITY or need)
    )
    return Summary(
        capacity=session.capacity,
        registration_limit=session.registration_limit,
        registered=registered,
        present=present,
        priority_present=priority_present,
    )


def _last_operator(db: Session, ticket_ids: list[int]) -> dict[int, str]:
    if not ticket_ids:
        return {}
    rows = db.execute(
        select(Checkin.ticket_id, Checkin.operator_name, User.name)
        .outerjoin(User, User.id == Checkin.operator_user_id)
        .where(Checkin.ticket_id.in_(ticket_ids), Checkin.undone_at.is_(None))
        .order_by(Checkin.id)
    ).all()
    return {ticket_id: (op_name or user_name or "") for ticket_id, op_name, user_name in rows}


def _attendees(db: Session, tickets: list[Ticket]) -> list[AttendeeOut]:
    types = {
        t.id: t
        for t in db.scalars(
            select(TicketType).where(TicketType.id.in_({t.ticket_type_id for t in tickets}))
        )
    }
    operators = _last_operator(db, [t.id for t in tickets if t.status == TicketStatus.USED])
    return [
        AttendeeOut(
            id=t.public_id,
            name=t.attendee_name,
            age_group=t.age_group,
            type_name=types[t.ticket_type_id].name,
            priority=types[t.ticket_type_id].kind == TicketKind.PRIORITY
            or bool(t.accessibility_need),
            accessibility_need=t.accessibility_need,
            status=t.status,
            checked_in_at=utc_to_local(t.checked_in_at) if t.checked_in_at else None,
            checked_in_by=operators.get(t.id),
        )
        for t in tickets
    ]


def _order_brief(db: Session, order: Order) -> OrderBrief:
    # populate_existing: o UPDATE atômico não atualiza objetos já carregados na sessão.
    tickets = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.order_id == order.id)
            .order_by(Ticket.id)
            .execution_options(populate_existing=True)
        )
    )
    return OrderBrief(code=order.code, buyer_name=order.buyer_name, tickets=_attendees(db, tickets))


def search(db: Session, event: Event, query: str, limit: int = 15) -> list[OrderBrief]:
    q = " ".join(query.split())
    if len(q) < 2:
        return []
    like = f"%{q}%"
    order_ids = db.scalars(
        select(Order.id)
        .outerjoin(Ticket, Ticket.order_id == Order.id)
        .where(
            Order.event_id == event.id,
            or_(
                Ticket.attendee_name.ilike(like),
                Order.buyer_name.ilike(like),
                Order.code.ilike(like),
                Order.buyer_email.ilike(like),
            ),
        )
        .group_by(Order.id)
        .order_by(func.min(Order.buyer_name))
        .limit(limit)
    ).all()
    orders = db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    briefs = [_order_brief(db, o) for o in orders]
    return sorted(briefs, key=lambda b: b.buyer_name.lower())


# ---------------------------------------------------------------- entrada


def _check_in(
    db: Session, op: Operator, ticket: Ticket, method: CheckinMethod, device_id: str | None
) -> bool:
    """Marca a entrada de forma atômica. False se o ingresso não estava válido."""
    now = utcnow()
    result = db.execute(
        update(Ticket)
        .where(Ticket.id == ticket.id, Ticket.status == TicketStatus.VALID)
        .values(status=TicketStatus.USED, checked_in_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return False
    db.add(
        Checkin(
            ticket_id=ticket.id,
            session_id=ticket.session_id,
            operator_user_id=op.user_id,
            operator_name=op.name,
            method=method,
            device_id=device_id,
            checked_in_at=now,
        )
    )
    return True


def _result_for(db: Session, op: Operator, ticket: Ticket, done: bool) -> CheckinResult:
    db.commit()
    db.refresh(ticket)
    order = db.get(Order, ticket.order_id)
    brief = _order_brief(db, order)
    me = next(a for a in brief.tickets if a.id == ticket.public_id)
    if done:
        result, message = "ok", "Entrada liberada"
    elif ticket.status == TicketStatus.USED:
        when = f"{me.checked_in_at:%H:%M}" if me.checked_in_at else ""
        by = f" por {me.checked_in_by}" if me.checked_in_by else ""
        result, message = "already", f"Já entrou às {when}{by}"
    else:
        result, message = "cancelled", "Ingresso cancelado"
    return CheckinResult(
        result=result, message=message, ticket=me, order=brief, summary=summary(db, op.event)
    )


def _ticket_of_event(db: Session, op: Operator, public_id: str) -> Ticket | None:
    session = main_session(db, op.event)
    ticket = db.scalar(select(Ticket).where(Ticket.public_id == public_id))
    if ticket is None or ticket.session_id != session.id:
        return None
    return ticket


def scan(db: Session, op: Operator, qr: str, device_id: str | None) -> CheckinResult:
    public_id = verify_qr(qr)
    if public_id is None:
        return CheckinResult(
            result="invalid",
            message="QR Code inválido",
            summary=summary(db, op.event),
        )
    ticket = _ticket_of_event(db, op, public_id)
    if ticket is None:
        return CheckinResult(
            result="other_event",
            message="Ingresso de outro evento",
            summary=summary(db, op.event),
        )
    done = _check_in(db, op, ticket, CheckinMethod.QR, device_id)
    return _result_for(db, op, ticket, done)


def manual(db: Session, op: Operator, ticket_public_id: str) -> CheckinResult:
    ticket = _ticket_of_event(db, op, ticket_public_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")
    done = _check_in(db, op, ticket, CheckinMethod.MANUAL, None)
    return _result_for(db, op, ticket, done)


def check_in_order(db: Session, op: Operator, code: str) -> OrderBrief:
    order = db.scalar(
        select(Order).where(Order.code == code.strip().upper(), Order.event_id == op.event.id)
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inscrição não encontrada.")
    for ticket in db.scalars(select(Ticket).where(Ticket.order_id == order.id)):
        _check_in(db, op, ticket, CheckinMethod.MANUAL, None)
    db.commit()
    return _order_brief(db, order)


def undo(db: Session, op: Operator, ticket_public_id: str) -> OrderBrief:
    ticket = _ticket_of_event(db, op, ticket_public_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado.")
    last = db.scalar(
        select(Checkin)
        .where(Checkin.ticket_id == ticket.id, Checkin.undone_at.is_(None))
        .order_by(Checkin.id.desc())
        .limit(1)
    )
    if ticket.status != TicketStatus.USED or last is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este ingresso não tem entrada registrada.")
    # Voluntário só desfaz a própria leitura (engano na hora); a equipe desfaz qualquer uma.
    if not op.is_staff and last.operator_name != op.name:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Só quem registrou a entrada (ou a coordenação) pode desfazer.",
        )
    now = utcnow()
    last.undone_at = now
    last.undone_by_user_id = op.user_id
    last.undone_by_name = op.name
    ticket.status = TicketStatus.VALID
    ticket.checked_in_at = None
    db.commit()
    return _order_brief(db, db.get(Order, ticket.order_id))
