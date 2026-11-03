from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.events.router import EDIT_ROLES, VIEW_ROLES, _event_for
from app.modules.messages import service
from app.modules.messages.models import MessageKind
from app.modules.notifications import email as email_module

router = APIRouter(prefix="/org/events/{slug}/messages", tags=["organizador · mensagens"])


class Texts(BaseModel):
    subject: str = Field(min_length=2, max_length=200)
    heading: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2, max_length=5000)
    button_label: str = Field(min_length=2, max_length=60)


class FieldOut(BaseModel):
    key: str
    label: str


class MessageOut(Texts):
    kind: MessageKind
    title: str
    description: str
    custom: bool
    fields: list[FieldOut]


class PreviewOut(BaseModel):
    subject: str
    html: str


def _out(db: Session, event, kind: MessageKind) -> MessageOut:
    texts = service.get_texts(db, event, kind)
    title, description = service.INFO[kind]
    return MessageOut(
        kind=kind,
        title=title,
        description=description,
        fields=[FieldOut(key=k, label=label) for k, label in service.fields_for(kind)],
        **texts,
    )


@router.get("", response_model=list[MessageOut])
def list_messages(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, VIEW_ROLES)
    return [_out(db, event, kind) for kind in MessageKind]


@router.put("/{kind}", response_model=MessageOut)
def save_message(
    slug: str,
    kind: str,
    payload: Texts,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    message_kind = service.ensure_kind(kind)
    service.save_texts(db, event, message_kind, payload.model_dump())
    return _out(db, event, message_kind)


@router.delete("/{kind}", response_model=MessageOut)
def reset_message(
    slug: str, kind: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    message_kind = service.ensure_kind(kind)
    service.reset_texts(db, event, message_kind)
    return _out(db, event, message_kind)


@router.post("/{kind}/preview", response_model=PreviewOut)
def preview_message(
    slug: str,
    kind: str,
    payload: Texts,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, VIEW_ROLES)
    return service.preview(db, event, service.ensure_kind(kind), payload.model_dump())


@router.post("/{kind}/test")
def send_test(
    slug: str,
    kind: str,
    payload: Texts,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envia a mensagem (com dados de exemplo) para o e-mail de quem está no painel."""
    event = _event_for(db, user, slug, EDIT_ROLES)
    message = service.sample_email(
        db, event, service.ensure_kind(kind), payload.model_dump(), user.email
    )
    try:
        email_module.send_email(message)
    except email_module.EmailError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return {"sent_to": user.email}
