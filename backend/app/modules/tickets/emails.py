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

# Tema escuro com cor de ação laranja (espelho de frontend/styles/tokens.css — e-mail não aceita variáveis CSS).
C = {
    "bg": "#000000",  # --bg-base
    "card": "#0B0D0E",  # --bg-surface-2
    "line": "#1E2523",  # --border-default sobre o fundo escuro
    "brand": "#FF8A3D",  # --brand (laranja)
    "on_brand": "#1A0B02",  # --on-brand
    "strong": "#FFFFFF",  # --text-strong
    "text": "#F3F8F6",  # --text-primary
    "muted": "#9EB4A9",  # --text-muted
    "subtle": "#A0AAA4",  # --text-subtle
    "warn": "#FBBF24",  # estado de aviso (badge de prioridade)
}
FONT = "'Sora',Arial,Helvetica,sans-serif"


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


def build_ticket_email(
    order: OrderOut,
    *,
    heading: str = "INGRESSO CONFIRMADO",
    intro: str | None = None,
    subject: str | None = None,
    logo: Attachment | None = None,
) -> OutgoingEmail:
    event = order.event
    link = ticket_link(order.token)
    when = format_when(event.starts_at)
    doors = f" · portas abrem às {event.doors_open_at:%H:%M}" if event.doors_open_at else ""
    place = ", ".join(filter(None, [event.venue_name, event.venue_address]))
    valid = [t for t in order.tickets if t.qr]

    attachments: list[Attachment] = []
    cards_html, lines_text = [], []
    for index, ticket in enumerate(valid, start=1):
        cid = f"qr-{index}@eventmer"
        attachments.append(Attachment(f"ingresso-{index}.png", qr_png(ticket.qr), "image/png", cid))
        badge = (
            f'<div style="display:inline-block;margin-top:8px;padding:3px 10px;border-radius:5px;'
            f'background:#2A2410;color:{C["warn"]};font-size:12px;font-weight:600">'
            "Atendimento prioritário</div>"
            if ticket.priority
            else ""
        )
        cards_html.append(
            f"""
<td style="padding:6px;width:50%;vertical-align:top">
  <div style="background:{C["card"]};border:1px solid {C["line"]};border-radius:12px;padding:16px;text-align:center">
    <img src="cid:{cid}" width="200" height="200" alt="QR Code de {escape(ticket.attendee_name)}"
         style="display:block;margin:0 auto 10px;border-radius:8px;background:#FFFFFF">
    <div style="font-size:17px;font-weight:600;letter-spacing:-0.3px;color:{C["text"]}">{escape(ticket.attendee_name)}</div>
    <div style="font-size:13px;color:{C["subtle"]};margin-top:2px">{AGE_LABEL.get(ticket.age_group, "")}
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
<html lang="pt-BR"><head><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"></head>
<body style="margin:0;background:{C["bg"]};font-family:{FONT};color:{C["text"]}">
<div style="max-width:560px;margin:0 auto;padding:28px 16px;background:{C["bg"]}">
  {f'<img src="cid:{logo.inline_cid}" alt="{escape(event.title)}" style="display:block;max-width:240px;max-height:120px;margin:0 0 20px">' if logo else ""}
  <p style="margin:0;color:{C["brand"]};font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase">{escape(heading)}</p>
  <h1 style="margin:10px 0 4px;font-size:32px;line-height:1.15;font-weight:400;color:{C["strong"]}">{escape(event.title)}</h1>
  <p style="margin:0;color:{C["muted"]}">{escape(event.subtitle or "")}</p>
  <div style="margin:22px 0;padding:18px;border-radius:12px;background:{C["card"]};border:1px solid {C["line"]};line-height:1.7">
    <p style="margin:0"><span style="color:{C["subtle"]}">Quando</span><br><strong style="color:{C["text"]}">{when.capitalize()}</strong>{doors}</p>
    {f'<p style="margin:12px 0 0"><span style="color:{C["subtle"]}">Onde</span><br><strong style="color:{C["text"]}">{escape(place)}</strong></p>' if place else ""}
    <p style="margin:12px 0 0"><span style="color:{C["subtle"]}">Inscrição</span><br><strong style="color:{C["text"]};letter-spacing:1px">{order.code}</strong></p>
  </div>
  <p style="line-height:1.85;color:{C["muted"]}">Olá, {first_name}! {escape(intro) if intro else "Sua inscrição está confirmada."}
     Na entrada, mostre o QR Code de cada pessoa (pode ser na tela do celular).</p>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">{rows}</table>
  <p style="text-align:center;margin:28px 0">
    <a href="{link}" style="display:inline-block;background:{C["brand"]};background-image:linear-gradient(115deg,#FFB37A,#FF8A3D 48%,#F26B1D);
       color:{C["on_brand"]};text-decoration:none;padding:16px 26px;border-radius:9px;font-weight:700;
       text-transform:uppercase;letter-spacing:0.5px">Ver meus ingressos</a>
  </p>
  <p style="font-size:14px;line-height:1.85;color:{C["muted"]}">Não poderá ir? Cancele pelo botão acima para liberar
     a vaga para outra família. A entrada é gratuita e os lugares são limitados — chegue cedo.</p>
  <div style="height:1px;margin:24px 0;background:{C["line"]};background-image:linear-gradient(90deg,#241B14,#BF956E 30%,#413125 58%,#171412)"></div>
  {f'<p style="font-size:13px;color:{C["muted"]};margin:0 0 8px">Realização: <strong style="color:{C["text"]}">{escape(event.organization_name)}</strong></p>' if event.organization_name else ""}
  <p style="font-size:12px;color:{C["subtle"]}">Enviado pelo EVENTMER para {escape(order.buyer_email)}.
     Este e-mail contém seus ingressos: não compartilhe com quem não vai com você.</p>
</div></body></html>"""

    text = (
        f"{heading.capitalize()} — {event.title}\n\n"
        + (f"{intro}\n\n" if intro else "")
        + f"Ingresso(s) de {order.buyer_name}\n\n"
        f"Quando: {when.capitalize()}{doors}\n"
        + (f"Onde: {place}\n" if place else "")
        + f"Inscrição: {order.code}\n\nPessoas:\n"
        + "\n".join(lines_text)
        + f"\n\nSeus ingressos com QR Code: {link}\n"
        "Não poderá ir? Cancele pelo link acima para liberar a vaga.\n"
    )
    if logo:
        attachments.insert(0, logo)
    return OutgoingEmail(
        to=order.buyer_email,
        subject=subject or f"Seu ingresso · {event.title} · {order.code}",
        html=html,
        text=text,
        attachments=attachments,
    )
