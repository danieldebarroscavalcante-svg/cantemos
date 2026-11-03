from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import local_to_utc, utc_to_local
from app.modules.events.models import Event, EventSession, registration_limit
from app.modules.events.schemas import (
    EventSettingsIn,
    EventSettingsOut,
    EventSummary,
    QuotaUsage,
    ReservedQuotaOut,
)
from app.modules.tickets.models import TicketKind, TicketType

GENERAL_NAME = "Entrada gratuita"
PRIORITY_NAME = "Prioridade (PCD, idosos, gestantes)"


def _logo_url(db: Session, event: Event) -> str | None:
    from app.modules.assets.models import Asset
    from app.modules.assets.service import url

    if not event.logo_asset_id:
        return None
    return url(db.scalar(select(Asset.public_id).where(Asset.id == event.logo_asset_id)))


def _invalid(message: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, message)


def main_session(db: Session, event: Event) -> EventSession:
    """MVP: o evento tem uma sessão principal (a primeira)."""
    session = db.scalar(
        select(EventSession)
        .where(EventSession.event_id == event.id)
        .order_by(EventSession.starts_at)
        .limit(1)
    )
    if session is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evento sem sessão configurada.")
    return session


def _types(db: Session, session: EventSession) -> list[TicketType]:
    return list(
        db.scalars(
            select(TicketType)
            .where(TicketType.session_id == session.id)
            .order_by(TicketType.sort_order, TicketType.id)
        )
    )


def _single(types: list[TicketType], kind: TicketKind) -> TicketType | None:
    return next((t for t in types if t.kind == kind), None)


def summarize(db: Session, event: Event, role=None) -> EventSummary:
    session = main_session(db, event)
    return EventSummary(
        my_role=role.value if role else None,
        slug=event.slug,
        title=event.title,
        status=event.status,
        starts_at=utc_to_local(session.starts_at),
        capacity=session.capacity,
        registration_limit=session.registration_limit,
        registered=session.reserved_count,
    )


def get_settings_out(db: Session, event: Event) -> EventSettingsOut:
    session = main_session(db, event)
    types = _types(db, session)
    general = _single(types, TicketKind.GENERAL)
    priority = _single(types, TicketKind.PRIORITY)
    return EventSettingsOut(
        slug=event.slug,
        title=event.title,
        status=event.status,
        venue_name=event.venue_name,
        venue_address=event.venue_address,
        description=event.description,
        logo_url=_logo_url(db, event),
        starts_at=utc_to_local(session.starts_at),
        doors_open_at=utc_to_local(session.doors_open_at) if session.doors_open_at else None,
        capacity=session.capacity,
        overbooking_percent=session.overbooking_percent,
        max_tickets_per_order=event.max_tickets_per_order,
        priority_quota=priority.quantity if priority else 0,
        reserved_quotas=[
            ReservedQuotaOut(
                id=t.public_id, name=t.name, quantity=t.quantity, issued=t.reserved_count
            )
            for t in types
            if t.kind == TicketKind.RESERVED
        ],
        registration_limit=session.registration_limit,
        general=QuotaUsage(
            quantity=general.quantity if general else 0,
            issued=general.reserved_count if general else 0,
        ),
        priority=QuotaUsage(
            quantity=priority.quantity if priority else 0,
            issued=priority.reserved_count if priority else 0,
        ),
        registered=session.reserved_count,
    )


def update_settings(db: Session, event: Event, data: EventSettingsIn) -> EventSettingsOut:
    """Aplica as configurações recalculando as cotas.

    Total aceito = lotação + margem. Prioridade e reservados são cotas fixas;
    a entrada gratuita (pública) fica com o restante. Nenhuma cota pode ficar
    abaixo do que já foi emitido.
    """
    session = main_session(db, event)
    types = _types(db, session)
    limit = registration_limit(data.capacity, data.overbooking_percent)

    if limit < session.reserved_count:
        raise _invalid(
            f"Já existem {session.reserved_count} inscrições; o total aceito "
            f"não pode ficar em {limit}."
        )

    reserved_total = sum(q.quantity for q in data.reserved_quotas)
    general_quantity = limit - data.priority_quota - reserved_total
    if general_quantity < 0:
        raise _invalid(
            f"Prioridade ({data.priority_quota}) + reservados ({reserved_total}) "
            f"ultrapassam o total aceito ({limit})."
        )

    # Entrada gratuita e prioridade
    general = _single(types, TicketKind.GENERAL)
    priority = _single(types, TicketKind.PRIORITY)
    if general is None:
        general = TicketType(
            session_id=session.id, kind=TicketKind.GENERAL, name=GENERAL_NAME, sort_order=1
        )
        db.add(general)
    if priority is None:
        priority = TicketType(
            session_id=session.id,
            kind=TicketKind.PRIORITY,
            name=PRIORITY_NAME,
            is_priority=True,
            sort_order=2,
        )
        db.add(priority)
    for ticket_type, quantity, label in (
        (general, general_quantity, "entrada gratuita"),
        (priority, data.priority_quota, "prioridade"),
    ):
        if quantity < (ticket_type.reserved_count or 0):
            raise _invalid(
                f"A cota de {label} não pode ficar abaixo de {ticket_type.reserved_count} "
                "(ingressos já emitidos)."
            )
        ticket_type.quantity = quantity

    # Cotas reservadas personalizadas
    existing = {t.public_id: t for t in types if t.kind == TicketKind.RESERVED}
    kept: set[str] = set()
    for order, quota in enumerate(data.reserved_quotas, start=10):
        if quota.id:
            ticket_type = existing.get(quota.id)
            if ticket_type is None:
                raise _invalid(f"Cota reservada '{quota.name}' não encontrada.")
            if quota.quantity < ticket_type.reserved_count:
                raise _invalid(
                    f"A cota '{quota.name}' não pode ficar abaixo de "
                    f"{ticket_type.reserved_count} (ingressos já emitidos)."
                )
            kept.add(quota.id)
        else:
            ticket_type = TicketType(session_id=session.id, kind=TicketKind.RESERVED)
            db.add(ticket_type)
        ticket_type.name = quota.name.strip()
        ticket_type.quantity = quota.quantity
        ticket_type.is_hidden = True
        ticket_type.sort_order = order
    for public_id, ticket_type in existing.items():
        if public_id not in kept:
            if ticket_type.reserved_count:
                raise _invalid(
                    f"A cota '{ticket_type.name}' já tem ingressos emitidos "
                    "e não pode ser removida."
                )
            db.delete(ticket_type)

    session.capacity = data.capacity
    session.overbooking_percent = data.overbooking_percent
    session.starts_at = local_to_utc(data.starts_at)
    session.doors_open_at = local_to_utc(data.doors_open_at) if data.doors_open_at else None
    event.max_tickets_per_order = data.max_tickets_per_order
    if data.status is not None:
        event.status = data.status
    for field in ("venue_name", "venue_address", "description"):
        value = getattr(data, field)
        if value is not None:
            setattr(event, field, value.strip() or None)
    db.commit()
    return get_settings_out(db, event)
