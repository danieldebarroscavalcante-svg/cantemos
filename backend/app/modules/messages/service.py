"""Textos dos e-mails do evento: padrão + personalização, campos automáticos e montagem."""

import base64
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.events.models import Event
from app.modules.messages.models import MessageKind, MessageTemplate
from app.modules.notifications.email import Attachment, OutgoingEmail
from app.modules.notifications.layout import (
    EmailParts,
    InfoRow,
    TicketCard,
    render_html,
    render_text,
)

AGE_LABEL = {"adulto": "Adulto", "crianca": "Criança", "idoso": "Idoso"}

INFO = {
    MessageKind.CONFIRMATION: ("Ingresso confirmado", "Enviado na hora da inscrição, com os QR Codes."),
    MessageKind.REMINDER_CONFIRM: ("Lembrete: faltam poucos dias", "Botão “Faltam poucos dias” em Números e lembretes."),
    MessageKind.REMINDER_TOMORROW: ("Lembrete: é amanhã", "Botão “É amanhã!” em Números e lembretes."),
    MessageKind.WAITLIST_JOINED: ("Lista de espera: confirmação", "Quando a pessoa entra na fila."),
    MessageKind.WAITLIST_INVITE: ("Lista de espera: abriu vaga", "Quando a vaga é guardada para a pessoa."),
}  # fmt: skip

DEFAULTS: dict[MessageKind, dict[str, str]] = {
    MessageKind.CONFIRMATION: {
        "subject": "Seu ingresso · {evento} · {codigo}",
        "heading": "Inscrição confirmada",
        "body": "Olá, {nome}!\n\nSua inscrição para o {evento} está confirmada. Na entrada, "
        "mostre o QR Code de cada pessoa — pode ser na tela do celular.\n\nNão poderá ir? "
        "Cancele pelo botão abaixo para liberar a vaga para outra família.",
        "button_label": "Ver meus ingressos",
    },
    MessageKind.REMINDER_CONFIRM: {
        "subject": "Faltam poucos dias · {evento}",
        "heading": "Faltam poucos dias",
        "body": "Olá, {nome}!\n\nO {evento} será {data}, às {hora}. Seus ingressos estão "
        "abaixo.\n\nSe não puder ir, cancele pelo botão para liberar a vaga — há famílias "
        "esperando.",
        "button_label": "Ver ou cancelar ingressos",
    },
    MessageKind.REMINDER_TOMORROW: {
        "subject": "É amanhã! · {evento}",
        "heading": "É amanhã!",
        "body": "Olá, {nome}!\n\nO {evento} é amanhã, {data}. As portas abrem às {portas} e "
        "começamos às {hora}. Chegue cedo: os lugares são limitados.\n\nTenha os QR Codes "
        "abaixo em mãos (pode ser na tela do celular).",
        "button_label": "Ver meus ingressos",
    },
    MessageKind.WAITLIST_JOINED: {
        "subject": "Lista de espera · {evento}",
        "heading": "Você está na lista de espera",
        "body": "Olá, {nome}!\n\nVocê entrou na lista de espera do {evento}. Se abrir vaga, "
        "enviaremos um e-mail com um link para você se inscrever — a vaga fica guardada por "
        "24 horas a partir do aviso.",
        "button_label": "Ver página do evento",
    },
    MessageKind.WAITLIST_INVITE: {
        "subject": "Abriu vaga! · {evento} · inscreva-se até {prazo}",
        "heading": "Abriu vaga para você",
        "body": "Olá, {nome}!\n\nGuardamos {pessoas} lugar(es) para você no {evento} até "
        "{prazo}. Faça a inscrição pelo botão abaixo.\n\nDepois desse prazo, a vaga passa "
        "para a próxima pessoa da lista.",
        "button_label": "Fazer minha inscrição",
    },
}

COMMON_FIELDS = [
    ("nome", "Primeiro nome"),
    ("nome_completo", "Nome completo"),
    ("evento", "Nome do evento"),
    ("tema", "Tema do evento"),
    ("data", "Data por extenso"),
    ("hora", "Horário de início"),
    ("portas", "Abertura das portas"),
    ("local", "Local"),
    ("igreja", "Nome da igreja"),
]
EXTRA_FIELDS = {
    MessageKind.CONFIRMATION: [("codigo", "Código da inscrição"), ("pessoas", "Nº de pessoas")],
    MessageKind.REMINDER_CONFIRM: [("codigo", "Código da inscrição"), ("pessoas", "Nº de pessoas")],
    MessageKind.REMINDER_TOMORROW: [
        ("codigo", "Código da inscrição"),
        ("pessoas", "Nº de pessoas"),
    ],
    MessageKind.WAITLIST_JOINED: [("posicao", "Posição na fila"), ("pessoas", "Nº de pessoas")],
    MessageKind.WAITLIST_INVITE: [
        ("prazo", "Prazo da vaga guardada"),
        ("pessoas", "Nº de pessoas"),
    ],
}

_FIELD = re.compile(r"\{(\w+)\}")


def fields_for(kind: MessageKind) -> list[tuple[str, str]]:
    return COMMON_FIELDS + EXTRA_FIELDS[kind]


def fill(template: str, values: dict[str, str]) -> str:
    return _FIELD.sub(lambda m: values.get(m.group(1), m.group(0)), template)


# ---------------------------------------------------------------- textos


def get_texts(db: Session, event: Event, kind: MessageKind) -> dict:
    custom = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.event_id == event.id, MessageTemplate.kind == kind
        )
    )
    if custom is None:
        return {**DEFAULTS[kind], "custom": False}
    return {
        "subject": custom.subject,
        "heading": custom.heading,
        "body": custom.body,
        "button_label": custom.button_label,
        "custom": True,
    }


def save_texts(db: Session, event: Event, kind: MessageKind, data: dict) -> None:
    custom = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.event_id == event.id, MessageTemplate.kind == kind
        )
    )
    if custom is None:
        custom = MessageTemplate(event_id=event.id, kind=kind)
        db.add(custom)
    for key in ("subject", "heading", "body", "button_label"):
        setattr(custom, key, data[key].strip())
    db.commit()


def reset_texts(db: Session, event: Event, kind: MessageKind) -> None:
    custom = db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.event_id == event.id, MessageTemplate.kind == kind
        )
    )
    if custom is not None:
        db.delete(custom)
        db.commit()


# ---------------------------------------------------------------- dados


def _time(value: datetime) -> str:
    return f"{value:%H}h{value:%M}" if value.minute else f"{value:%H}h"


def event_values(event_out) -> dict[str, str]:
    from app.modules.tickets.emails import format_when

    when = format_when(event_out.starts_at)
    place = ", ".join(filter(None, [event_out.venue_name, event_out.venue_address]))
    return {
        "evento": event_out.title,
        "tema": event_out.subtitle or "",
        "data": when.split(" às ")[0],
        "hora": _time(event_out.starts_at),
        "portas": _time(event_out.doors_open_at) if event_out.doors_open_at else "",
        "local": place,
        "igreja": event_out.organization_name or "",
    }


def _event_rows(event_out, code: str | None = None) -> list[InfoRow]:
    from app.modules.tickets.emails import format_when

    when = format_when(event_out.starts_at).capitalize()
    if event_out.doors_open_at:
        when += f" (portas às {_time(event_out.doors_open_at)})"
    rows = [InfoRow("Quando", when)]
    place = ", ".join(filter(None, [event_out.venue_name, event_out.venue_address]))
    if place:
        rows.append(InfoRow("Onde", place))
    if code:
        rows.append(InfoRow("Inscrição", code, mono=True))
    return rows


def _footer(event_out, reason: str) -> str:
    org = f" Realização: {event_out.organization_name}." if event_out.organization_name else ""
    return f"Você recebe este e-mail porque {reason} {event_out.title}.{org}"


def _base_url() -> str:
    return get_settings().frontend_url.rstrip("/")


def _logo(logo: Attachment | None, inline: bool) -> str | None:
    if logo is None:
        return None
    if inline:
        return f"cid:{logo.inline_cid}"
    return f"data:{logo.mime_type};base64,{base64.b64encode(logo.content).decode()}"


def _qr_src(png: bytes, cid: str, inline: bool) -> str:
    return f"cid:{cid}" if inline else f"data:image/png;base64,{base64.b64encode(png).decode()}"


# ---------------------------------------------------------------- montagem


def ticket_parts(
    texts: dict, kind: MessageKind, order, logo: Attachment | None, inline: bool = True
) -> tuple[str, EmailParts, list[Attachment]]:
    from app.modules.tickets.emails import qr_png

    event = order.event
    valid = [t for t in order.tickets if t.qr]
    values = {
        **event_values(event),
        "nome": order.buyer_name.split()[0],
        "nome_completo": order.buyer_name,
        "codigo": order.code,
        "pessoas": str(len(valid)),
    }
    attachments: list[Attachment] = [logo] if (logo and inline) else []
    cards = []
    for i, t in enumerate(valid, start=1):
        png, cid = qr_png(t.qr), f"qr-{i}@eventmer"
        if inline:
            attachments.append(Attachment(f"ingresso-{i}.png", png, "image/png", cid))
        cards.append(
            TicketCard(
                name=t.attendee_name,
                detail=f"{AGE_LABEL.get(t.age_group, '')} · Ingresso {i} de {len(valid)}",
                qr_src=_qr_src(png, cid, inline),
                priority=t.priority,
            )
        )
    parts = EmailParts(
        heading=fill(texts["heading"], values),
        body=fill(texts["body"], values),
        info_title=event.title,
        info_rows=_event_rows(event, order.code),
        highlight_label="Responsável pela inscrição",
        highlight_lines=[order.buyer_name],
        tickets=cards,
        button_label=fill(texts["button_label"], values),
        button_url=f"{_base_url()}/ingresso/{order.token}",
        footer=_footer(event, "fez inscrição no"),
        logo_src=_logo(logo, inline),
        logo_alt=event.title,
        brand_text=event.title.upper(),
    )
    return fill(texts["subject"], values), parts, attachments


def waitlist_parts(
    texts: dict,
    kind: MessageKind,
    event_out,
    *,
    name: str,
    quantity: int,
    position: int | None = None,
    deadline: str | None = None,
    link: str,
    logo: Attachment | None,
    inline: bool = True,
) -> tuple[str, EmailParts, list[Attachment]]:
    values = {
        **event_values(event_out),
        "nome": name.split()[0],
        "nome_completo": name,
        "pessoas": str(quantity),
        "posicao": str(position or ""),
        "prazo": deadline or "",
    }
    if kind == MessageKind.WAITLIST_INVITE:
        label, lines = "Vaga guardada até", [deadline or ""]
    else:
        label = "Sua posição na fila"
        lines = [f"{position}º lugar · {quantity} {'pessoa' if quantity == 1 else 'pessoas'}"]
    parts = EmailParts(
        heading=fill(texts["heading"], values),
        body=fill(texts["body"], values),
        info_title=event_out.title,
        info_rows=_event_rows(event_out),
        highlight_label=label,
        highlight_lines=lines,
        button_label=fill(texts["button_label"], values),
        button_url=link,
        footer=_footer(event_out, "entrou na lista de espera do"),
        logo_src=_logo(logo, inline),
        logo_alt=event_out.title,
        brand_text=event_out.title.upper(),
    )
    return fill(texts["subject"], values), parts, ([logo] if (logo and inline) else [])


def to_email(to: str, subject: str, parts: EmailParts, attachments: list[Attachment]):
    return OutgoingEmail(
        to=to,
        subject=subject,
        html=render_html(parts),
        text=render_text(parts),
        attachments=attachments,
    )


# ---------------------------------------------------------------- uso


def ticket_email(db: Session, order, kind: MessageKind = MessageKind.CONFIRMATION):
    from app.modules.tickets.service import email_logo

    event = db.get(Event, db.scalar(select(Event.id).where(Event.slug == order.event.slug)))
    subject, parts, attachments = ticket_parts(
        get_texts(db, event, kind), kind, order, email_logo(db, event)
    )
    return to_email(order.buyer_email, subject, parts, attachments)


def preview(db: Session, event: Event, kind: MessageKind, texts: dict) -> dict:
    """Mensagem com dados de exemplo (imagens embutidas como data:), para a prévia no painel."""
    subject, parts, _ = sample_parts(db, event, kind, texts, inline=False)
    return {"subject": subject, "html": render_html(parts)}


def sample_email(db: Session, event: Event, kind: MessageKind, texts: dict, to: str):
    """Mesma mensagem de exemplo, pronta para envio de teste (imagens como anexo embutido)."""
    subject, parts, attachments = sample_parts(db, event, kind, texts, inline=True)
    return to_email(to, f"[TESTE] {subject}", parts, attachments)


def sample_parts(db: Session, event: Event, kind: MessageKind, texts: dict, inline: bool):
    from datetime import timedelta

    from app.core.timezone import utc_to_local
    from app.db.base import utcnow
    from app.modules.tickets.schemas import OrderOut, TicketOut
    from app.modules.tickets.service import email_logo, public_event_out

    event_out = public_event_out(db, event)
    logo = email_logo(db, event)
    if kind in (MessageKind.WAITLIST_JOINED, MessageKind.WAITLIST_INVITE):
        deadline = utc_to_local(utcnow() + timedelta(hours=24))
        subject, parts, _ = waitlist_parts(
            texts,
            kind,
            event_out,
            name="Maria Souza",
            quantity=2,
            position=3,
            deadline=f"{deadline:%d/%m} às {deadline:%H:%M}",
            link=f"{_base_url()}/e/{event.slug}",
            logo=logo,
            inline=inline,
        )
    else:
        sample = OrderOut(
            code="CAN-EXEMP",
            token="exemplo",
            status="confirmed",
            buyer_name="Maria Souza",
            buyer_email="maria@exemplo.com",
            created_at=datetime(2026, 11, 9, 10, 0),
            email_sent=True,
            event=event_out,
            tickets=[
                TicketOut(id="a", attendee_name="Maria Souza", age_group="adulto",
                          type_name="Entrada gratuita", priority=False, accessibility_need=None,
                          status="valid", qr="EVM1.exemplo-a.0000000000000000"),
                TicketOut(id="b", attendee_name="Rosa Souza", age_group="idoso",
                          type_name="Prioridade", priority=True, accessibility_need="Cadeirante",
                          status="valid", qr="EVM1.exemplo-b.0000000000000000"),
            ],
        )  # fmt: skip
        return ticket_parts(texts, kind, sample, logo, inline=inline)
    return subject, parts, ([logo] if (logo and inline) else [])


def ensure_kind(kind: str) -> MessageKind:
    try:
        return MessageKind(kind)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de mensagem desconhecido.") from exc
