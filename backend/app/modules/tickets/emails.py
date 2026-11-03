"""E-mail do ingresso: um QR Code por pessoa, como imagem embutida (funciona offline)."""

import io
from datetime import datetime
from html import escape

import segno

from app.core.config import get_settings
from app.modules.notifications.email import Attachment, OutgoingEmail
from app.modules.tickets.schemas import OrderOut

WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]  # fmt: skip
AGE_LABEL = {"adulto": "Adulto", "crianca": "Criança", "idoso": "Idoso"}


def format_when(value: datetime) -> str:
    return (
        (
            f"{WEEKDAYS[value.weekday()]}-feira, {value.day} de {MONTHS[value.month - 1]}"
            f" às {value:%H:%M}"
        )
        .replace("sábado-feira", "sábado")
        .replace("domingo-feira", "domingo")
    )


def qr_png(content: str) -> bytes:
    buffer = io.BytesIO()
    segno.make(content, error="m").save(buffer, kind="png", scale=8, border=2)
    return buffer.getvalue()


def ticket_link(token: str) -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/ingresso/{token}"


def build_ticket_email(order: OrderOut) -> OutgoingEmail:
    event = order.event
    link = ticket_link(order.token)
    when = format_when(event.starts_at)
    doors = f" (portas abrem às {event.doors_open_at:%H:%M})" if event.doors_open_at else ""
    place = ", ".join(filter(None, [event.venue_name, event.venue_address]))
    valid = [t for t in order.tickets if t.qr]

    attachments: list[Attachment] = []
    cards_html, lines_text = [], []
    for index, ticket in enumerate(valid, start=1):
        cid = f"qr-{index}@eventmer"
        attachments.append(Attachment(f"ingresso-{index}.png", qr_png(ticket.qr), "image/png", cid))
        badge = (
            '<div style="display:inline-block;margin-top:6px;padding:2px 8px;border-radius:99px;'
            'background:#fef3c7;color:#92400e;font-size:12px;font-weight:600">'
            "Atendimento prioritário</div>"
            if ticket.priority
            else ""
        )
        cards_html.append(
            f"""
<td style="padding:8px;width:50%;vertical-align:top">
  <div style="border:1px solid #e7e5e4;border-radius:16px;padding:16px;text-align:center">
    <img src="cid:{cid}" width="200" height="200" alt="QR Code de {escape(ticket.attendee_name)}"
         style="display:block;margin:0 auto 8px">
    <div style="font-size:16px;font-weight:700">{escape(ticket.attendee_name)}</div>
    <div style="font-size:13px;color:#6b7280">{AGE_LABEL.get(ticket.age_group, "")}
      · Ingresso {index} de {len(valid)}</div>
    {badge}
  </div>
</td>"""
        )
        lines_text.append(f"- {ticket.attendee_name}")

    rows = "".join(
        "<tr>" + "".join(cards_html[i : i + 2]) + "</tr>" for i in range(0, len(cards_html), 2)
    )
    first_name = escape(order.buyer_name.split()[0])
    html = f"""<!doctype html>
<html lang="pt-BR"><body style="margin:0;background:#fafaf9;font-family:Arial,Helvetica,sans-serif;color:#1c1917">
<div style="max-width:560px;margin:0 auto;padding:24px 16px">
  <p style="margin:0;color:#4338ca;font-size:12px;font-weight:700;letter-spacing:2px">INGRESSO CONFIRMADO</p>
  <h1 style="margin:8px 0 4px;font-size:26px">{escape(event.title)}</h1>
  <p style="margin:0;color:#6b7280">{escape(event.subtitle or "")}</p>
  <div style="margin:20px 0;padding:16px;border-radius:16px;background:#fff;border:1px solid #e7e5e4">
    <p style="margin:0 0 6px"><strong>Quando:</strong> {when.capitalize()}{doors}</p>
    {f'<p style="margin:0 0 6px"><strong>Onde:</strong> {escape(place)}</p>' if place else ""}
    <p style="margin:0"><strong>Inscrição:</strong> {order.code}</p>
  </div>
  <p>Olá, {first_name}! Sua inscrição está confirmada. Na entrada, mostre o QR Code de cada
     pessoa (pode ser na tela do celular).</p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">{rows}</table>
  <p style="text-align:center;margin:24px 0">
    <a href="{link}" style="display:inline-block;background:#4338ca;color:#fff;text-decoration:none;
       padding:14px 24px;border-radius:12px;font-weight:700">Ver meus ingressos</a>
  </p>
  <p style="font-size:14px;color:#6b7280">Não poderá ir? Cancele pelo botão acima para liberar
     a vaga para outra família. A entrada é gratuita e os lugares são limitados — chegue cedo.</p>
  <hr style="border:none;border-top:1px solid #e7e5e4;margin:24px 0">
  <p style="font-size:12px;color:#9ca3af">Enviado pelo EVENTMER para {escape(order.buyer_email)}.
     Este e-mail contém seus ingressos: não compartilhe com quem não vai com você.</p>
</div></body></html>"""

    text = (
        f"Ingresso confirmado — {event.title}\n\n"
        f"Quando: {when.capitalize()}{doors}\n"
        + (f"Onde: {place}\n" if place else "")
        + f"Inscrição: {order.code}\n\nPessoas:\n"
        + "\n".join(lines_text)
        + f"\n\nSeus ingressos com QR Code: {link}\n"
        "Não poderá ir? Cancele pelo link acima para liberar a vaga.\n"
    )
    return OutgoingEmail(
        to=order.buyer_email,
        subject=f"Seu ingresso · {event.title} · {order.code}",
        html=html,
        text=text,
        attachments=attachments,
    )
