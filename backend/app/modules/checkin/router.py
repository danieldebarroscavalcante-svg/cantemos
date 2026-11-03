import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.ratelimit import RateLimiter, client_ip
from app.core.security import create_checkin_token
from app.core.timezone import utc_to_local
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.checkin import service
from app.modules.checkin.schemas import (
    CheckinResult,
    OperatorOut,
    OrderBrief,
    ReceptionInfo,
    ReceptionLoginIn,
    ReceptionLoginOut,
    ScanIn,
    Summary,
)
from app.modules.events.router import EDIT_ROLES, VIEW_ROLES, _event_for
from app.modules.tickets.models import Order, Ticket, TicketKind, TicketType

router = APIRouter(prefix="/checkin/events/{slug}", tags=["recepção"])
org_router = APIRouter(prefix="/org/events/{slug}", tags=["organizador · recepção"])

bearer = HTTPBearer(auto_error=False)
login_limiter = RateLimiter(max_calls=10, per_seconds=600)


def operator(
    slug: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> service.Operator:
    return service.resolve_operator(db, slug, credentials.credentials if credentials else None)


# ------------------------------------------------------------ voluntários / equipe


@router.post("/login", response_model=ReceptionLoginOut)
def reception_login(
    slug: str, payload: ReceptionLoginIn, request: Request, db: Session = Depends(get_db)
):
    login_limiter.hit(f"{client_ip(request)}:{slug}")
    event = service.event_by_slug(db, slug)
    code = payload.code.strip().upper()
    if not event.checkin_code or code != event.checkin_code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código da recepção incorreto.")
    name = " ".join(payload.name.split())
    return ReceptionLoginOut(
        token=create_checkin_token(event.id, name, event.checkin_code),
        event_slug=event.slug,
        event_title=event.title,
        operator_name=name,
    )


@router.get("/me", response_model=OperatorOut)
def whoami(op: service.Operator = Depends(operator), db: Session = Depends(get_db)):
    from app.modules.tickets.service import branding

    return OperatorOut(
        name=op.name,
        event_slug=op.event.slug,
        event_title=op.event.title,
        can_undo=op.is_staff,
        event_logo_url=branding(db, op.event)["logo_url"],
    )


@router.get("/summary", response_model=Summary)
def get_summary(op: service.Operator = Depends(operator), db: Session = Depends(get_db)):
    return service.summary(db, op.event)


@router.post("/scan", response_model=CheckinResult)
def scan(payload: ScanIn, op: service.Operator = Depends(operator), db: Session = Depends(get_db)):
    return service.scan(db, op, payload.qr, payload.device_id)


@router.get("/search", response_model=list[OrderBrief])
def search(
    q: str = Query(min_length=1, max_length=100),
    op: service.Operator = Depends(operator),
    db: Session = Depends(get_db),
):
    return service.search(db, op.event, q)


@router.post("/tickets/{ticket_id}/checkin", response_model=CheckinResult)
def manual_checkin(
    ticket_id: str, op: service.Operator = Depends(operator), db: Session = Depends(get_db)
):
    return service.manual(db, op, ticket_id)


@router.post("/tickets/{ticket_id}/undo", response_model=OrderBrief)
def undo_checkin(
    ticket_id: str, op: service.Operator = Depends(operator), db: Session = Depends(get_db)
):
    return service.undo(db, op, ticket_id)


@router.post("/orders/{code}/checkin", response_model=OrderBrief)
def order_checkin(
    code: str, op: service.Operator = Depends(operator), db: Session = Depends(get_db)
):
    return service.check_in_order(db, op, code)


# ------------------------------------------------------------ painel do organizador


@org_router.get("/reception", response_model=ReceptionInfo)
def reception_info(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, VIEW_ROLES)
    return ReceptionInfo(code=event.checkin_code, checkin_path=f"/checkin/{event.slug}")


@org_router.post("/reception/code", response_model=ReceptionInfo)
def regenerate_code(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Gera um novo código; quem entrou com o código antigo precisa entrar de novo."""
    event = _event_for(db, user, slug, EDIT_ROLES)
    event.checkin_code = service.new_checkin_code()
    db.commit()
    return ReceptionInfo(code=event.checkin_code, checkin_path=f"/checkin/{event.slug}")


class AttendeeRow(BaseModel):
    code: str
    buyer_name: str
    buyer_email: str
    buyer_phone: str | None
    attendee_name: str
    age_group: str
    ticket_type: str
    priority: bool
    accessibility_need: str | None
    status: str
    checked_in_at: str | None
    registered_at: str
    source: str | None


def _rows(db: Session, user: User, slug: str) -> list[AttendeeRow]:
    event = _event_for(db, user, slug, VIEW_ROLES)
    rows = db.execute(
        select(Order, Ticket, TicketType)
        .join(Ticket, Ticket.order_id == Order.id)
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .where(Order.event_id == event.id)
        .order_by(Order.buyer_name, Order.id, Ticket.id)
    ).all()
    return [
        AttendeeRow(
            code=o.code,
            buyer_name=o.buyer_name,
            buyer_email=o.buyer_email,
            buyer_phone=o.buyer_phone,
            attendee_name=t.attendee_name,
            age_group=t.age_group.value,
            ticket_type=tt.name,
            priority=tt.kind == TicketKind.PRIORITY or bool(t.accessibility_need),
            accessibility_need=t.accessibility_need,
            status=t.status.value,
            checked_in_at=f"{utc_to_local(t.checked_in_at):%d/%m %H:%M}"
            if t.checked_in_at
            else None,
            registered_at=f"{utc_to_local(o.created_at):%d/%m/%Y %H:%M}",
            source=o.source,
        )
        for o, t, tt in rows
    ]


@org_router.get("/attendees", response_model=list[AttendeeRow])
def attendees(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _rows(db, user, slug)


@org_router.get("/attendees.csv")
def attendees_csv(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    labels = {
        "code": "Inscrição", "buyer_name": "Responsável", "buyer_email": "E-mail",
        "buyer_phone": "Telefone", "attendee_name": "Participante", "age_group": "Faixa etária",
        "ticket_type": "Tipo", "priority": "Prioridade", "accessibility_need": "Necessidade",
        "status": "Situação", "checked_in_at": "Entrada", "registered_at": "Inscrito em",
        "source": "Origem",
    }  # fmt: skip
    status_pt = {"valid": "Inscrito", "used": "Presente", "cancelled": "Cancelado"}
    buffer = io.StringIO()
    buffer.write("﻿")  # BOM: acentos corretos ao abrir no Excel
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(labels.values())
    for row in _rows(db, user, slug):
        data = row.model_dump()
        data["priority"] = "Sim" if row.priority else ""
        data["status"] = status_pt.get(row.status, row.status)
        writer.writerow(data[key] or "" for key in labels)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="inscritos-{slug}.csv"'},
    )
