from datetime import datetime

from app.modules.messages.models import MessageKind
from app.modules.messages.service import DEFAULTS, fill, ticket_parts
from app.modules.notifications.layout import render_html, render_text
from app.modules.tickets.emails import format_when
from app.modules.tickets.schemas import OrderOut, PublicEvent, TicketOut


def make_order():
    event = PublicEvent(
        slug="cantemos-2026", title="CANTEMOS 2026", subtitle="Uma história", description=None,
        venue_name="Templo", venue_address="Rua X, 1", status="open",
        starts_at=datetime(2026, 11, 19, 18, 30), doors_open_at=datetime(2026, 11, 19, 18),
        max_tickets_per_order=5, available=100, priority_available=10,
        organization_name="Ministério Estabelecendo o Reino",
    )  # fmt: skip
    tickets = [
        TicketOut(id="a", attendee_name="Maria <b>", age_group="adulto", type_name="Geral",
                  priority=False, accessibility_need=None, status="valid", qr="EVM1.a.x"),
        TicketOut(id="b", attendee_name="Rosa", age_group="idoso", type_name="Prioridade",
                  priority=True, accessibility_need="Cadeirante", status="valid", qr="EVM1.b.x"),
        TicketOut(id="c", attendee_name="João", age_group="crianca", type_name="Geral",
                  priority=False, accessibility_need=None, status="cancelled", qr=None),
    ]  # fmt: skip
    return OrderOut(
        code="CAN-ABCDE", token="tok.123", status="confirmed", buyer_name="Maria Silva",
        buyer_email="maria@example.com", created_at=datetime(2026, 11, 9), email_sent=False,
        event=event, tickets=tickets,
    )  # fmt: skip


def test_format_when_in_portuguese():
    assert format_when(datetime(2026, 11, 19, 18, 30)) == "quinta-feira, 19 de novembro às 18:30"
    assert format_when(datetime(2026, 11, 21, 9, 0)) == "sábado, 21 de novembro às 09:00"


def test_fill_replaces_known_fields_and_keeps_unknown():
    assert fill("Olá, {nome}! {desconhecido}", {"nome": "Ana"}) == "Olá, Ana! {desconhecido}"


def test_confirmation_layout_has_card_blocks_qr_and_footer():
    subject, parts, attachments = ticket_parts(
        DEFAULTS[MessageKind.CONFIRMATION], MessageKind.CONFIRMATION, make_order(), logo=None
    )
    assert subject == "Seu ingresso · CANTEMOS 2026 · CAN-ABCDE"
    html = render_html(parts)
    assert len(attachments) == 2  # um QR por ingresso válido
    assert attachments[0].content.startswith(b"\x89PNG")
    assert "Maria &lt;b&gt;" in html  # nomes escapados
    assert "Responsável pela inscrição" in html and "Maria Silva" in html
    assert "/ingresso/tok.123" in html
    assert "border-top:4px solid #FF8A3D" in html  # faixa laranja do topo
    assert "Realização: Ministério Estabelecendo o Reino" in html
    text = render_text(parts)
    assert "Quinta-feira, 19 de novembro às 18:30 (portas às 18h)" in text
    assert "Olá, Maria!" in text


def test_custom_texts_with_fields_are_applied():
    texts = {
        "subject": "{nome}, faltam 3 dias para o {evento}",
        "heading": "Tema: {tema}",
        "body": "Código {codigo}\n\nSão {pessoas} pessoas. Portas às {portas}.",
        "button_label": "Abrir",
    }
    subject, parts, _ = ticket_parts(texts, MessageKind.REMINDER_CONFIRM, make_order(), logo=None)
    assert subject == "Maria, faltam 3 dias para o CANTEMOS 2026"
    html = render_html(parts)
    assert "Tema: Uma história" in html
    assert "Código CAN-ABCDE" in html and "São 2 pessoas. Portas às 18h." in html
