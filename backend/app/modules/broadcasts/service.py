"""Lembretes em massa para os inscritos, enviados em segundo plano com contagem de progresso."""

import logging
import time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.timezone import utc_to_local
from app.db.base import utcnow
from app.modules.broadcasts.models import Broadcast, BroadcastKind, BroadcastStatus
from app.modules.events.models import Event
from app.modules.events.service import main_session
from app.modules.notifications import email as email_module
from app.modules.tickets.emails import build_ticket_email, format_when
from app.modules.tickets.models import Order, OrderStatus, Ticket, TicketStatus
from app.modules.tickets.service import email_logo, order_out

logger = logging.getLogger("eventmer.broadcasts")
PAUSE_SECONDS = 0.5  # gentil com o limite do Gmail


def recipients(db: Session, event: Event) -> list[int]:
    """Inscrições confirmadas com pelo menos um ingresso válido."""
    return list(
        db.scalars(
            select(Order.id)
            .join(Ticket, Ticket.order_id == Order.id)
            .where(
                Order.event_id == event.id,
                Order.status == OrderStatus.CONFIRMED,
                Ticket.status == TicketStatus.VALID,
            )
            .group_by(Order.id)
            .order_by(Order.id)
        )
    )


def _texts(kind: BroadcastKind, event: Event, starts_local) -> tuple[str, str, str]:
    when = format_when(starts_local)
    if kind == BroadcastKind.CONFIRM:
        return (
            "FALTAM POUCOS DIAS",
            f"O {event.title} será {when}. Seus ingressos estão abaixo. Se não puder ir, "
            "cancele pelo botão “Ver meus ingressos” para liberar a vaga para outra família "
            "— há pessoas esperando.",
            f"Faltam poucos dias · {event.title} · confirme sua presença",
        )
    return (
        "É AMANHÃ",
        f"O {event.title} é amanhã, {when}. Chegue cedo: a entrada é por ordem de chegada e "
        "os lugares são limitados.",
        f"É amanhã! · {event.title}",
    )


def start(db: Session, event: Event, kind: BroadcastKind, requested_by: str) -> Broadcast:
    running = db.scalar(
        select(Broadcast).where(
            Broadcast.event_id == event.id, Broadcast.status == BroadcastStatus.RUNNING
        )
    )
    if running:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe um envio em andamento. Aguarde terminar."
        )
    broadcast = Broadcast(
        event_id=event.id,
        kind=kind,
        requested_by=requested_by,
        total=len(recipients(db, event)),
    )
    db.add(broadcast)
    db.commit()
    return broadcast


def run(broadcast_id: int, session_factory: sessionmaker) -> None:
    """Executa o envio (chamado em segundo plano, com sessão própria)."""
    with session_factory() as db:
        broadcast = db.get(Broadcast, broadcast_id)
        event = db.get(Event, broadcast.event_id)
        heading, intro, subject = _texts(
            broadcast.kind, event, utc_to_local(main_session(db, event).starts_at)
        )
        logo = email_logo(db, event)
        for order_id in recipients(db, event):
            try:
                message = build_ticket_email(
                    order_out(db, db.get(Order, order_id)),
                    heading=heading,
                    intro=intro,
                    subject=subject,
                    logo=logo,
                )
                email_module.send_email(message)
                broadcast.sent += 1
            except Exception:  # um e-mail com problema não interrompe os demais
                logger.exception("Lembrete não enviado (inscrição %s)", order_id)
                broadcast.failed += 1
            db.commit()
            if PAUSE_SECONDS:
                time.sleep(PAUSE_SECONDS)
        broadcast.status = BroadcastStatus.DONE
        broadcast.finished_at = utcnow()
        db.commit()
        logger.info(
            "Lembrete %s: %d enviados, %d falhas", broadcast.kind, broadcast.sent, broadcast.failed
        )
