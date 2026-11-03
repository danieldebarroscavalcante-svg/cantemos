"""Inscrição pública, cancelamento e consulta de ingressos."""

import logging
import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, undefer

from app.core.security import sign_order_token, sign_qr, verify_order_token
from app.core.timezone import utc_to_local
from app.db.base import utcnow
from app.modules.assets.models import Asset
from app.modules.assets.service import EMAIL_SAFE
from app.modules.assets.service import url as asset_url
from app.modules.auth.models import User
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event, EventSession, EventStatus
from app.modules.events.service import main_session
from app.modules.notifications.email import Attachment
from app.modules.organizations.models import Organization
from app.modules.tickets.models import (
    Order,
    OrderStatus,
    Ticket,
    TicketKind,
    TicketStatus,
    TicketType,
)
from app.modules.tickets.schemas import (
    OrderIn,
    OrderOut,
    PublicEvent,
    TicketOut,
    WaitlistInvite,
)
from app.modules.waitlist import service as waitlist
from app.modules.waitlist.models import WaitlistEntry, WaitlistStatus

logger = logging.getLogger("eventmer.tickets")


def branding(db: Session, event: Event) -> dict:
    """Logo do evento e nome/logo da organização (para páginas e e-mails)."""
    org = db.get(Organization, event.organization_id)
    ids = {event.logo_asset_id, event.banner_asset_id, org.logo_asset_id if org else None} - {None}
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(ids)))} if ids else {}
    event_logo = assets.get(event.logo_asset_id)
    org_logo = assets.get(org.logo_asset_id) if org else None
    banner = assets.get(event.banner_asset_id)
    return {
        "logo_url": asset_url(event_logo.public_id) if event_logo else None,
        "banner_url": asset_url(banner.public_id) if banner else None,
        "organization_name": org.name if org else None,
        "organization_logo_url": asset_url(org_logo.public_id) if org_logo else None,
        "event_logo": event_logo,
    }


def email_logo(db: Session, event: Event) -> Attachment | None:
    """Logo do evento embutido no e-mail (só PNG/JPG, que os programas de e-mail exibem)."""
    if not event.logo_asset_id:
        return None
    asset = db.scalar(
        select(Asset).where(Asset.id == event.logo_asset_id).options(undefer(Asset.data))
    )
    if asset is None or asset.content_type not in EMAIL_SAFE:
        return None
    ext = "png" if asset.content_type == "image/png" else "jpg"
    return Attachment(f"logo.{ext}", asset.data, asset.content_type, inline_cid="logo@eventmer")


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O, 1/I


def _error(code: int, message: str) -> HTTPException:
    return HTTPException(code, message)


# ---------------------------------------------------------------- consulta


def get_public_event(db: Session, slug: str) -> Event:
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None or event.status == EventStatus.DRAFT:
        raise _error(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return event


def _public_types(db: Session, session: EventSession) -> dict[TicketKind, TicketType]:
    types = db.scalars(
        select(TicketType).where(
            TicketType.session_id == session.id,
            TicketType.kind.in_((TicketKind.GENERAL, TicketKind.PRIORITY)),
        )
    )
    return {t.kind: t for t in types}


def public_event_out(
    db: Session, event: Event, invited: WaitlistEntry | None = None
) -> PublicEvent:
    session = main_session(db, event)
    types = _public_types(db, session)

    def remaining(kind: TicketKind) -> int:
        t = types.get(kind)
        return max(0, t.quantity - t.reserved_count) if t else 0

    available = waitlist.available_for_public(db, event, invited.id if invited else None)
    brand = branding(db, event)
    waiting = db.scalar(
        select(func.count()).where(
            WaitlistEntry.event_id == event.id, WaitlistEntry.status == WaitlistStatus.WAITING
        )
    )

    return PublicEvent(
        slug=event.slug,
        title=event.title,
        subtitle=event.subtitle,
        description=event.description,
        venue_name=event.venue_name,
        venue_address=event.venue_address,
        status=event.status,
        starts_at=utc_to_local(session.starts_at),
        doors_open_at=utc_to_local(session.doors_open_at) if session.doors_open_at else None,
        max_tickets_per_order=event.max_tickets_per_order,
        available=available,
        priority_available=min(available, remaining(TicketKind.PRIORITY)),
        waitlist_waiting=int(waiting or 0),
        logo_url=brand["logo_url"],
        banner_url=brand["banner_url"],
        organization_name=brand["organization_name"],
        organization_logo_url=brand["organization_logo_url"],
        invite=WaitlistInvite(
            name=invited.name,
            quantity=invited.quantity,
            hold_until=utc_to_local(invited.hold_until),
        )
        if invited
        else None,
    )


def order_out(db: Session, order: Order) -> OrderOut:
    event = db.get(Event, order.event_id)
    types = {
        t.id: t
        for t in db.scalars(
            select(TicketType).join(Ticket).where(Ticket.order_id == order.id).distinct()
        )
    }
    tickets = db.scalars(select(Ticket).where(Ticket.order_id == order.id).order_by(Ticket.id))
    return OrderOut(
        code=order.code,
        token=sign_order_token(order.public_id),
        status=order.status,
        buyer_name=order.buyer_name,
        buyer_email=order.buyer_email,
        created_at=utc_to_local(order.created_at),
        email_sent=order.email_sent_at is not None,
        event=public_event_out(db, event),
        tickets=[
            TicketOut(
                id=t.public_id,
                attendee_name=t.attendee_name,
                age_group=t.age_group,
                type_name=types[t.ticket_type_id].name,
                priority=types[t.ticket_type_id].kind == TicketKind.PRIORITY
                or bool(t.accessibility_need),
                accessibility_need=t.accessibility_need,
                status=t.status,
                qr=sign_qr(t.public_id) if t.status == TicketStatus.VALID else None,
            )
            for t in tickets
        ],
    )


def order_from_token(db: Session, token: str) -> Order:
    public_id = verify_order_token(token)
    order = db.scalar(select(Order).where(Order.public_id == public_id)) if public_id else None
    if order is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Inscrição não encontrada. Confira o link.")
    return order


# ---------------------------------------------------------------- inscrição


def _reserve(db: Session, ticket_type: TicketType, quantity: int) -> bool:
    """Reserva atômica: só incrementa se couber (evita overbooking em acessos simultâneos)."""
    if quantity <= 0:
        return True
    result = db.execute(
        update(TicketType)
        .where(
            TicketType.id == ticket_type.id,
            TicketType.reserved_count + quantity <= TicketType.quantity,
        )
        .values(reserved_count=TicketType.reserved_count + quantity)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _release(db: Session, ticket_type_id: int, session_id: int, quantity: int) -> None:
    db.execute(
        update(TicketType)
        .where(TicketType.id == ticket_type_id)
        .values(reserved_count=TicketType.reserved_count - quantity)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(EventSession)
        .where(EventSession.id == session_id)
        .values(reserved_count=EventSession.reserved_count - quantity)
        .execution_options(synchronize_session=False)
    )


def _new_code(db: Session, event: Event) -> str:
    prefix = "".join(ch for ch in event.slug.upper() if ch.isalpha())[:3] or "EVT"
    for _ in range(10):
        code = f"{prefix}-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(5))
        if not db.scalar(select(Order.id).where(Order.code == code)):
            return code
    raise RuntimeError("Não foi possível gerar um código de inscrição único.")


def _buyer(db: Session, email: str, name: str, phone: str | None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=name, phone=phone)  # conta "leve", sem senha
        db.add(user)
        db.flush()
    return user


def create_order(db: Session, slug: str, data: OrderIn, *, is_test: bool = False) -> Order:
    """Cria a inscrição. Com is_test (Teste geral do painel), funciona com o evento em qualquer
    situação e não conta para a regra de uma inscrição por e-mail."""
    if is_test:
        event = db.scalar(select(Event).where(Event.slug == slug))
        if event is None:
            raise _error(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    else:
        event = get_public_event(db, slug)
    if event.status != EventStatus.OPEN and not is_test:
        raise _error(status.HTTP_409_CONFLICT, "As inscrições não estão abertas.")
    if not data.consent:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "É preciso aceitar os termos de uso e a política de privacidade.",
        )
    if len(data.attendees) > event.max_tickets_per_order:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Cada inscrição pode ter no máximo {event.max_tickets_per_order} pessoas.",
        )

    email = normalize_email(str(data.buyer_email))
    existing = db.scalar(
        select(Order.code).where(
            Order.event_id == event.id,
            Order.buyer_email == email,
            Order.status == OrderStatus.CONFIRMED,
            Order.is_test.is_(False),
        )
    )
    if existing and not is_test:
        raise _error(
            status.HTTP_409_CONFLICT,
            "Já existe uma inscrição com este e-mail. Use “Reenviar meu ingresso” para "
            "recebê-lo de novo.",
        )

    session = main_session(db, event)
    types = _public_types(db, session)
    general, priority = types.get(TicketKind.GENERAL), types.get(TicketKind.PRIORITY)
    if general is None:
        raise _error(status.HTTP_409_CONFLICT, "Evento sem ingressos configurados.")

    # Vagas guardadas para quem foi chamado da lista de espera não ficam disponíveis ao público.
    invited = None if is_test else waitlist.entry_from_token(db, event, data.waitlist_token)
    available = waitlist.available_for_public(db, event, invited.id if invited else None)
    if len(data.attendees) > available:
        if available == 0:
            raise _error(status.HTTP_409_CONFLICT, "Inscrições esgotadas.")
        raise _error(
            status.HTTP_409_CONFLICT,
            f"Restam apenas {available} vaga(s). Reduza o número de pessoas e tente de novo.",
        )

    # Prioridade usa a cota própria; se ela não comportar o grupo, essas pessoas entram na
    # cota geral (o atendimento prioritário continua marcado no ingresso).
    wants_priority = [a for a in data.attendees if a.priority]
    in_priority: set[int] = set()
    if wants_priority and priority is not None and _reserve(db, priority, len(wants_priority)):
        in_priority = {id(a) for a in wants_priority}
    general_count = len(data.attendees) - len(in_priority)
    if not _reserve(db, general, general_count):
        db.rollback()
        db.refresh(general)
        left = max(0, general.quantity - general.reserved_count)
        if left == 0:
            raise _error(status.HTTP_409_CONFLICT, "Inscrições esgotadas.")
        raise _error(
            status.HTTP_409_CONFLICT,
            f"Restam apenas {left} vaga(s). Reduza o número de pessoas e tente de novo.",
        )

    db.execute(
        update(EventSession)
        .where(EventSession.id == session.id)
        .values(reserved_count=EventSession.reserved_count + len(data.attendees))
        .execution_options(synchronize_session=False)
    )
    buyer = _buyer(db, email, data.buyer_name.strip(), data.buyer_phone)
    order = Order(
        code=_new_code(db, event),
        organization_id=event.organization_id,
        event_id=event.id,
        buyer_user_id=buyer.id,
        buyer_name=" ".join(data.buyer_name.split()),
        buyer_email=email,
        buyer_phone=(data.buyer_phone or "").strip() or None,
        status=OrderStatus.CONFIRMED,
        source=(data.source or "").strip()[:80] or None,
        consent_at=utcnow(),
        is_test=is_test,
    )
    db.add(order)
    db.flush()
    for attendee in data.attendees:  # mantém a ordem informada no formulário
        ticket_type = priority if id(attendee) in in_priority else general
        db.add(
            Ticket(
                order_id=order.id,
                ticket_type_id=ticket_type.id,
                session_id=session.id,
                attendee_name=attendee.name,
                age_group=attendee.age_group,
                accessibility_need=(attendee.accessibility_need or "").strip()
                or ("Atendimento prioritário" if attendee.priority else None),
            )
        )
    if not is_test:
        waitlist.mark_registered(db, event, email, invited)
    db.commit()
    logger.info("Inscrição %s criada (%d pessoas)", order.code, len(data.attendees))
    return order


# ---------------------------------------------------------------- cancelamento


def cancel(db: Session, order: Order, ticket_ids: list[str]) -> Order:
    if order.status != OrderStatus.CONFIRMED:
        raise _error(status.HTTP_409_CONFLICT, "Esta inscrição já foi cancelada.")
    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    targets = [t for t in tickets if not ticket_ids or t.public_id in ticket_ids]
    if ticket_ids and len(targets) != len(set(ticket_ids)):
        raise _error(status.HTTP_404_NOT_FOUND, "Ingresso não encontrado nesta inscrição.")
    if any(t.status == TicketStatus.USED for t in targets):
        raise _error(
            status.HTTP_409_CONFLICT, "Ingresso já utilizado na entrada não pode ser cancelado."
        )

    now = utcnow()
    for ticket in targets:
        if ticket.status != TicketStatus.VALID:
            continue
        ticket.status = TicketStatus.CANCELLED
        ticket.cancelled_at = now
        _release(db, ticket.ticket_type_id, ticket.session_id, 1)
    if all(t.status == TicketStatus.CANCELLED for t in tickets):
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = now
    db.commit()
    logger.info("Inscrição %s: %d ingresso(s) cancelado(s)", order.code, len(targets))
    return order


def find_active_order(db: Session, slug: str, email: str) -> Order | None:
    event = get_public_event(db, slug)
    return db.scalar(
        select(Order).where(
            Order.event_id == event.id,
            Order.buyer_email == normalize_email(email),
            Order.status == OrderStatus.CONFIRMED,
            Order.is_test.is_(False),
        )
    )


def delete_test_orders(db: Session, event: Event) -> int:
    """Remove as inscrições do Teste geral, com entradas registradas, devolvendo as vagas."""
    from app.modules.checkin.models import Checkin

    orders = list(db.scalars(select(Order).where(Order.event_id == event.id, Order.is_test)))
    for order in orders:
        for ticket in db.scalars(select(Ticket).where(Ticket.order_id == order.id)):
            if ticket.status in (TicketStatus.VALID, TicketStatus.USED):
                _release(db, ticket.ticket_type_id, ticket.session_id, 1)
            for checkin in db.scalars(select(Checkin).where(Checkin.ticket_id == ticket.id)):
                db.delete(checkin)
            db.delete(ticket)
        db.delete(order)
    db.commit()
    if orders:
        logger.info("Teste geral: %d inscrição(ões) de teste removida(s)", len(orders))
    return len(orders)
