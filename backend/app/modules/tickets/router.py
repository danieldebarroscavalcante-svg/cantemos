import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.ratelimit import RateLimiter, client_ip
from app.db.base import utcnow
from app.db.session import get_db
from app.modules.events.models import Event
from app.modules.messages.service import ticket_email
from app.modules.notifications.email import EmailError, send_email
from app.modules.tickets import service
from app.modules.tickets.models import Order
from app.modules.tickets.schemas import CancelIn, OrderIn, OrderOut, PublicEvent, ResendIn
from app.modules.waitlist import service as waitlist
from app.modules.waitlist.schemas import WaitlistIn, WaitlistJoinOut

logger = logging.getLogger("eventmer.tickets")
router = APIRouter(prefix="/public", tags=["público"])

# Generoso por IP: no culto, muitas famílias se inscrevem pelo mesmo Wi-Fi.
order_limiter = RateLimiter(max_calls=60, per_seconds=60)
resend_limiter = RateLimiter(max_calls=5, per_seconds=600)


def _send_ticket_email(db: Session, order: Order) -> None:
    """Envia o ingresso. Uma falha no e-mail não desfaz a inscrição: o ingresso
    também aparece na tela de confirmação e pode ser reenviado."""
    try:
        send_email(ticket_email(db, service.order_out(db, order)))
    except EmailError:
        logger.exception("Falha ao enviar o ingresso da inscrição %s", order.code)
        return
    order.email_sent_at = utcnow()
    db.commit()


waitlist_limiter = RateLimiter(max_calls=20, per_seconds=600)


@router.get("/events/{slug}", response_model=PublicEvent)
def get_event(
    slug: str,
    lista: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    event = service.get_public_event(db, slug)
    # Sem agendador: vagas guardadas vencidas são repassadas quando alguém abre a página.
    if waitlist.expire_holds(db, event):
        waitlist.notify_next(db, event)
    invited = waitlist.entry_from_token(db, event, lista)
    return service.public_event_out(db, event, invited)


@router.post("/events/{slug}/waitlist", response_model=WaitlistJoinOut, status_code=201)
def join_waitlist(slug: str, payload: WaitlistIn, request: Request, db: Session = Depends(get_db)):
    waitlist_limiter.hit(client_ip(request))
    if payload.website:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não foi possível concluir.")
    entry, position, already = waitlist.join(db, service.get_public_event(db, slug), payload)
    return WaitlistJoinOut(position=position, quantity=entry.quantity, already=already)


@router.post("/events/{slug}/orders", response_model=OrderOut, status_code=201)
def create_order(slug: str, payload: OrderIn, request: Request, db: Session = Depends(get_db)):
    order_limiter.hit(client_ip(request))
    if payload.website:  # robô preencheu o campo invisível
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não foi possível concluir a inscrição.")
    order = service.create_order(db, slug, payload)
    _send_ticket_email(db, order)
    return service.order_out(db, order)


@router.post("/events/{slug}/resend", status_code=202)
def resend(slug: str, payload: ResendIn, request: Request, db: Session = Depends(get_db)):
    """Reenvia o ingresso. A resposta é sempre a mesma, para não revelar quem está inscrito."""
    resend_limiter.hit(f"{client_ip(request)}:{payload.email.lower()}")
    order = service.find_active_order(db, slug, str(payload.email))
    if order is not None:
        _send_ticket_email(db, order)
    return {
        "detail": "Se houver uma inscrição com este e-mail, enviaremos o ingresso em instantes."
    }


@router.get("/orders/{token}", response_model=OrderOut)
def get_order(token: str, db: Session = Depends(get_db)):
    return service.order_out(db, service.order_from_token(db, token))


@router.post("/orders/{token}/cancel", response_model=OrderOut)
def cancel_order(token: str, payload: CancelIn, db: Session = Depends(get_db)):
    order = service.cancel(db, service.order_from_token(db, token), payload.ticket_ids)
    waitlist.notify_next(db, db.get(Event, order.event_id))  # vaga liberada → próximo da fila
    return service.order_out(db, order)
