"""Lista de espera: fila por ordem de chegada; vaga liberada fica guardada por 24 h
para quem foi chamado, e passa para o próximo se não for usada."""

import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import sign_waitlist_token, verify_waitlist_token
from app.core.timezone import utc_to_local
from app.db.base import utcnow
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event, EventStatus
from app.modules.events.service import main_session
from app.modules.notifications.email import EmailError, OutgoingEmail, send_email
from app.modules.tickets.models import TicketKind, TicketType
from app.modules.waitlist.models import WaitlistEntry, WaitlistStatus
from app.modules.waitlist.schemas import WaitlistIn

logger = logging.getLogger("eventmer.waitlist")
HOLD_HOURS = 24
ACTIVE = (WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED)


def raw_remaining(db: Session, event: Event) -> int:
    """Vagas da inscrição pública (geral + prioridade), sem considerar a lista de espera."""
    session = main_session(db, event)
    row = db.execute(
        select(func.coalesce(func.sum(TicketType.quantity - TicketType.reserved_count), 0)).where(
            TicketType.session_id == session.id,
            TicketType.kind.in_((TicketKind.GENERAL, TicketKind.PRIORITY)),
        )
    ).scalar_one()
    return max(0, int(row))


def active_holds(db: Session, event: Event, exclude_id: int | None = None) -> int:
    query = select(func.coalesce(func.sum(WaitlistEntry.quantity), 0)).where(
        WaitlistEntry.event_id == event.id,
        WaitlistEntry.status == WaitlistStatus.NOTIFIED,
        WaitlistEntry.hold_until > utcnow(),
    )
    if exclude_id is not None:
        query = query.where(WaitlistEntry.id != exclude_id)
    return int(db.execute(query).scalar_one())


def available_for_public(db: Session, event: Event, exclude_id: int | None = None) -> int:
    return max(0, raw_remaining(db, event) - active_holds(db, event, exclude_id))


def expire_holds(db: Session, event: Event) -> int:
    expired = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.event_id == event.id,
            WaitlistEntry.status == WaitlistStatus.NOTIFIED,
            WaitlistEntry.hold_until <= utcnow(),
        )
    ).all()
    for entry in expired:
        entry.status = WaitlistStatus.EXPIRED
    if expired:
        db.commit()
    return len(expired)


def position_of(db: Session, entry: WaitlistEntry) -> int:
    return int(
        db.execute(
            select(func.count()).where(
                WaitlistEntry.event_id == entry.event_id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
                WaitlistEntry.id <= entry.id,
            )
        ).scalar_one()
    )


def entry_from_token(db: Session, event: Event, token: str | None) -> WaitlistEntry | None:
    public_id = verify_waitlist_token(token) if token else None
    if not public_id:
        return None
    entry = db.scalar(select(WaitlistEntry).where(WaitlistEntry.public_id == public_id))
    if (
        entry is None
        or entry.event_id != event.id
        or entry.status != WaitlistStatus.NOTIFIED
        or entry.hold_until is None
        or entry.hold_until <= utcnow()
    ):
        return None
    return entry


def mark_registered(db: Session, event: Event, email: str, invited: WaitlistEntry | None) -> None:
    entries = list(
        db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.event_id == event.id,
                WaitlistEntry.email == normalize_email(email),
                WaitlistEntry.status.in_(ACTIVE),
            )
        )
    )
    if invited is not None and invited not in entries:
        entries.append(invited)
    for entry in entries:
        entry.status = WaitlistStatus.REGISTERED


# ---------------------------------------------------------------- e-mails


def _event_link(event: Event, entry: WaitlistEntry | None = None) -> str:
    base = f"{get_settings().frontend_url.rstrip('/')}/e/{event.slug}"
    return f"{base}?lista={sign_waitlist_token(entry.public_id)}" if entry else base


def _send(message: OutgoingEmail) -> None:
    try:
        send_email(message)
    except EmailError:
        logger.exception("Falha ao enviar e-mail da lista de espera para %s", message.to)


def _joined_email(event: Event, entry: WaitlistEntry, position: int) -> OutgoingEmail:
    first = entry.name.split()[0]
    text = (
        f"Olá, {first}! Você está na lista de espera do {event.title} "
        f"(posição {position}, {entry.quantity} pessoa(s)).\n\n"
        "Se abrir vaga, enviaremos um e-mail com um link para você se inscrever. "
        f"A vaga fica guardada por {HOLD_HOURS} horas a partir do aviso.\n"
    )
    html = (
        '<div style="background:#000000;color:#F3F8F6;font-family:Arial,Helvetica,sans-serif;'
        'max-width:520px;margin:0 auto;padding:28px 16px;line-height:1.85">'
        '<p style="margin:0;color:#36EDB3;font-weight:700;letter-spacing:1.5px;font-size:11px;'
        'text-transform:uppercase">Lista de espera</p>'
        f'<h1 style="margin:10px 0 14px;font-size:28px;font-weight:400;color:#FFFFFF">{event.title}</h1>'
        f'<p style="color:#9EB4A9">Olá, {first}! Você está na posição '
        f'<strong style="color:#F3F8F6">{position}</strong> ({entry.quantity} pessoa(s)).</p>'
        '<p style="color:#9EB4A9">Se abrir vaga, enviaremos um e-mail com um link para você se '
        f"inscrever. A vaga fica guardada por {HOLD_HOURS} horas a partir do aviso.</p></div>"
    )
    return OutgoingEmail(
        to=entry.email, subject=f"Lista de espera · {event.title}", html=html, text=text
    )


def _invite_email(event: Event, entry: WaitlistEntry) -> OutgoingEmail:
    first = entry.name.split()[0]
    link = _event_link(event, entry)
    until = utc_to_local(entry.hold_until)
    deadline = f"{until:%d/%m} às {until:%H:%M}"
    text = (
        f"Olá, {first}! Abriu vaga no {event.title}.\n\n"
        f"Guardamos {entry.quantity} lugar(es) para você até {deadline}. "
        f"Faça a inscrição por este link: {link}\n\n"
        "Depois desse prazo, a vaga passa para a próxima pessoa da lista.\n"
    )
    # Cores do tema (espelho de frontend/styles/tokens.css).
    html = f"""<div style="background:#000000;color:#F3F8F6;font-family:'Sora',Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;padding:28px 16px">
<p style="margin:0;color:#36EDB3;font-weight:700;letter-spacing:1.5px;font-size:11px;text-transform:uppercase">Abriu vaga</p>
<h1 style="margin:10px 0 14px;font-size:30px;font-weight:400;color:#FFFFFF">{event.title}</h1>
<p style="line-height:1.85;color:#9EB4A9">Olá, {first}! Guardamos <strong style="color:#F3F8F6">{entry.quantity} lugar(es)</strong>
para você até <strong style="color:#F3F8F6">{deadline}</strong>.</p>
<p style="text-align:center;margin:28px 0"><a href="{link}" style="display:inline-block;background:#36EDB3;
background-image:linear-gradient(115deg,#8AF7D3,#36EDB3 48%,#29DBA4);color:#020706;text-decoration:none;
padding:16px 26px;border-radius:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">Fazer minha inscrição</a></p>
<p style="color:#9EB4A9;font-size:14px;line-height:1.85">Depois desse prazo, a vaga passa para a próxima pessoa
da lista.</p></div>"""
    return OutgoingEmail(
        to=entry.email,
        subject=f"Abriu vaga! · {event.title} · inscreva-se até {deadline}",
        html=html,
        text=text,
    )


# ---------------------------------------------------------------- operações


def join(db: Session, event: Event, data: WaitlistIn) -> tuple[WaitlistEntry, int, bool]:
    if event.status != EventStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "As inscrições não estão abertas.")
    if not data.consent:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "É preciso aceitar os termos de uso e a política de privacidade.",
        )
    if data.quantity > event.max_tickets_per_order:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Máximo de {event.max_tickets_per_order} pessoas por inscrição.",
        )
    email = normalize_email(str(data.email))
    existing = db.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.event_id == event.id,
            WaitlistEntry.email == email,
            WaitlistEntry.status.in_(ACTIVE),
        )
    )
    if existing:
        return existing, position_of(db, existing), True

    expire_holds(db, event)
    if available_for_public(db, event) >= data.quantity:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ainda há vagas! Recarregue a página e faça sua inscrição."
        )
    entry = WaitlistEntry(
        event_id=event.id,
        name=" ".join(data.name.split()),
        email=email,
        phone=(data.phone or "").strip() or None,
        quantity=data.quantity,
        consent_at=utcnow(),
    )
    db.add(entry)
    db.commit()
    position = position_of(db, entry)
    _send(_joined_email(event, entry, position))
    return entry, position, False


def notify_next(db: Session, event: Event) -> tuple[int, int]:
    """Chama os próximos da fila para as vagas livres. Retorna (avisados, vagas livres)."""
    expire_holds(db, event)
    if event.status != EventStatus.OPEN:
        return 0, available_for_public(db, event)
    free = available_for_public(db, event)
    if free <= 0:
        return 0, 0
    now = utcnow()
    invited: list[WaitlistEntry] = []
    waiting = db.scalars(
        select(WaitlistEntry)
        .where(WaitlistEntry.event_id == event.id, WaitlistEntry.status == WaitlistStatus.WAITING)
        .order_by(WaitlistEntry.id)
    )
    for entry in waiting:
        if free <= 0:
            break
        if entry.quantity > free:
            continue  # grupo maior que as vagas: espera a próxima liberação
        entry.status = WaitlistStatus.NOTIFIED
        entry.notified_at = now
        entry.hold_until = now + timedelta(hours=HOLD_HOURS)
        free -= entry.quantity
        invited.append(entry)
    db.commit()
    for entry in invited:
        _send(_invite_email(event, entry))
    if invited:
        logger.info("Lista de espera: %d pessoa(s)/grupo(s) avisados", len(invited))
    return len(invited), free


def rows(db: Session, event: Event) -> list[dict]:
    entries = db.scalars(
        select(WaitlistEntry).where(WaitlistEntry.event_id == event.id).order_by(WaitlistEntry.id)
    ).all()
    position = 0
    result = []
    for e in entries:
        if e.status == WaitlistStatus.WAITING:
            position += 1
        result.append(
            {
                "id": e.public_id,
                "position": position if e.status == WaitlistStatus.WAITING else None,
                "name": e.name,
                "email": e.email,
                "phone": e.phone,
                "quantity": e.quantity,
                "status": e.status,
                "created_at": utc_to_local(e.created_at),
                "hold_until": utc_to_local(e.hold_until) if e.hold_until else None,
            }
        )
    return result
