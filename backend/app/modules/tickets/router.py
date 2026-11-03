import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.ratelimit import RateLimiter, client_ip
from app.db.base import utcnow
from app.db.session import get_db
from app.modules.notifications.email import EmailError, send_email
from app.modules.tickets import service
from app.modules.tickets.emails import build_ticket_email
from app.modules.tickets.models import Order
from app.modules.tickets.schemas import CancelIn, OrderIn, OrderOut, PublicEvent, ResendIn

logger = logging.getLogger("eventmer.tickets")
router = APIRouter(prefix="/public", tags=["público"])

# Generoso por IP: no culto, muitas famílias se inscrevem pelo mesmo Wi-Fi.
order_limiter = RateLimiter(max_calls=60, per_seconds=60)
resend_limiter = RateLimiter(max_calls=5, per_seconds=600)


def _send_ticket_email(db: Session, order: Order) -> None:
    """Envia o ingresso. Uma falha no e-mail não desfaz a inscrição: o ingresso
    também aparece na tela de confirmação e pode ser reenviado."""
    try:
        send_email(build_ticket_email(service.order_out(db, order)))
    except EmailError:
        logger.exception("Falha ao enviar o ingresso da inscrição %s", order.code)
        return
    order.email_sent_at = utcnow()
    db.commit()


@router.get("/events/{slug}", response_model=PublicEvent)
def get_event(slug: str, db: Session = Depends(get_db)):
    return service.public_event_out(db, service.get_public_event(db, slug))


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
    return service.order_out(db, order)
