"""Lembretes em massa para os inscritos, enviados em segundo plano com contagem de progresso."""

import logging
import time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import utcnow
from app.modules.broadcasts.models import Broadcast, BroadcastKind, BroadcastStatus
from app.modules.events.models import Event
from app.modules.messages.models import MessageKind
from app.modules.messages.service import ticket_email
from app.modules.notifications import email as email_module
from app.modules.tickets.models import Order, OrderStatus, Ticket, TicketStatus
from app.modules.tickets.service import order_out

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
                Order.is_test.is_(False),  # lembretes não vão para inscrições de teste
                Ticket.status == TicketStatus.VALID,
            )
            .group_by(Order.id)
            .order_by(Order.id)
        )
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
        kind = (
            MessageKind.REMINDER_CONFIRM
            if broadcast.kind == BroadcastKind.CONFIRM
            else MessageKind.REMINDER_TOMORROW
        )
        for order_id in recipients(db, event):
            try:
                message = ticket_email(db, order_out(db, db.get(Order, order_id)), kind)
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
