from datetime import datetime

from app.modules.tickets.emails import build_ticket_email, format_when
from app.modules.tickets.schemas import OrderOut, PublicEvent, TicketOut


def test_format_when_in_portuguese():
    assert format_when(datetime(2026, 11, 19, 18, 30)) == "quinta-feira, 19 de novembro às 18:30"
    assert format_when(datetime(2026, 11, 21, 9, 0)) == "sábado, 21 de novembro às 09:00"


def test_ticket_email_has_one_inline_qr_per_valid_ticket():
    event = PublicEvent(
        slug="cantemos-2026", title="CANTEMOS 2026", subtitle=None, description=None,
        venue_name="Templo", venue_address="Rua X, 1", status="open",
        starts_at=datetime(2026, 11, 19, 18, 30), doors_open_at=datetime(2026, 11, 19, 18),
        max_tickets_per_order=5, available=100, priority_available=10,
    )  # fmt: skip
    tickets = [
        TicketOut(id="a", attendee_name="Maria <b>", age_group="adulto", type_name="Geral",
                  priority=False, accessibility_need=None, status="valid", qr="EVM1.a.x"),
        TicketOut(id="b", attendee_name="João", age_group="crianca", type_name="Geral",
                  priority=False, accessibility_need=None, status="cancelled", qr=None),
    ]  # fmt: skip
    order = OrderOut(
        code="CAN-ABCDE", token="tok.123", status="confirmed", buyer_name="Maria Silva",
        buyer_email="maria@example.com", created_at=datetime(2026, 11, 9), email_sent=False,
        event=event, tickets=tickets,
    )  # fmt: skip
    message = build_ticket_email(order)
    assert message.subject == "Seu ingresso · CANTEMOS 2026 · CAN-ABCDE"
    assert len(message.attachments) == 1
    assert message.attachments[0].content.startswith(b"\x89PNG")
    assert "Maria &lt;b&gt;" in message.html  # nomes escapados
    assert "/ingresso/tok.123" in message.html
    assert "Quinta-feira, 19 de novembro às 18:30 (portas abrem às 18:00)" in message.text
