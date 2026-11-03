from datetime import datetime

import pytest

from app.core.security import verify_qr
from app.modules.events.models import Event, EventSession, EventStatus
from app.modules.events.schemas import EventSettingsIn
from app.modules.events.service import update_settings
from app.modules.notifications import email as email_module
from app.modules.tickets import router as tickets_router
from app.modules.tickets.models import Order, Ticket, TicketKind, TicketType

SLUG = "cantemos-2026"
ORDERS = f"/api/v1/public/events/{SLUG}/orders"


@pytest.fixture(autouse=True)
def _reset_limits():
    tickets_router.order_limiter.reset()
    tickets_router.resend_limiter.reset()


@pytest.fixture
def sent(monkeypatch):
    """Captura os e-mails enviados."""
    messages = []
    monkeypatch.setattr(tickets_router, "send_email", messages.append)
    return messages


def make_event(db, org, *, capacity=10, overbooking=0, priority=2, reserved=(), status="open"):
    ev = Event(
        organization_id=org.id,
        slug=SLUG,
        title="CANTEMOS 2026",
        venue_name="Templo",
        status=EventStatus(status),
    )
    db.add(ev)
    db.flush()
    db.add(
        EventSession(event_id=ev.id, name="Quinta", starts_at=datetime(2026, 11, 19), capacity=1)
    )
    db.flush()
    update_settings(
        db,
        ev,
        EventSettingsIn(
            starts_at=datetime(2026, 11, 19, 18, 30),
            doors_open_at=datetime(2026, 11, 19, 18, 0),
            capacity=capacity,
            overbooking_percent=overbooking,
            max_tickets_per_order=5,
            priority_quota=priority,
            reserved_quotas=[{"name": n, "quantity": q} for n, q in reserved],
        ),
    )
    return ev


def payload(email="maria@example.com", people=("Maria Silva", "João Silva"), **extra):
    return {
        "buyer_name": "Maria Silva",
        "buyer_email": email,
        "buyer_phone": "(11) 99999-0000",
        "attendees": [{"name": n, "age_group": "adulto"} for n in people],
        "consent": True,
        **extra,
    }


def counts(db):
    db.expire_all()
    types = {t.kind: t.reserved_count for t in db.query(TicketType).all()}
    return types, db.query(EventSession).one().reserved_count


def test_public_event_hides_drafts(client, db, org):
    make_event(db, org, status="draft")
    assert client.get(f"/api/v1/public/events/{SLUG}").status_code == 404


def test_public_event_shows_availability_without_reserved_quotas(client, db, org):
    make_event(db, org, capacity=10, overbooking=20, priority=2, reserved=[("Coral", 3)])
    body = client.get(f"/api/v1/public/events/{SLUG}").json()
    # 10 + 20% = 12 aceitas; 3 reservadas ficam fora da inscrição pública
    assert body["available"] == 9
    assert body["priority_available"] == 2
    assert body["starts_at"] == "2026-11-19T18:30:00"


def test_family_registration_creates_tickets_and_sends_email(client, db, org, sent):
    make_event(db, org)
    response = client.post(ORDERS, json=payload(people=("Maria", "João", "Ana")))
    assert response.status_code == 201
    body = response.json()
    assert body["code"].startswith("CAN-")
    assert [t["attendee_name"] for t in body["tickets"]] == ["Maria", "João", "Ana"]
    assert all(verify_qr(t["qr"]) == t["id"] for t in body["tickets"])
    assert body["email_sent"] is True
    assert body["event"]["available"] == 10 - 3
    assert len(sent) == 1
    message = sent[0]
    assert message.to == "maria@example.com"
    assert len(message.attachments) == 3  # um QR por pessoa
    assert body["token"] in message.html


def test_priority_attendees_use_priority_quota(client, db, org, sent):
    make_event(db, org, priority=2)
    data = payload(people=("Maria", "Vovó Rosa"))
    data["attendees"][1].update(priority=True, age_group="idoso", accessibility_need="Cadeirante")
    body = client.post(ORDERS, json=data).json()
    assert [t["priority"] for t in body["tickets"]] == [False, True]
    types, session_total = counts(db)
    assert types[TicketKind.PRIORITY] == 1
    assert types[TicketKind.GENERAL] == 1
    assert session_total == 2


def test_priority_falls_back_to_general_when_quota_is_full(client, db, org, sent):
    make_event(db, org, priority=1)
    data = payload(people=("Ana", "Bia"))
    for attendee in data["attendees"]:
        attendee["priority"] = True
    body = client.post(ORDERS, json=data).json()
    assert all(t["priority"] for t in body["tickets"])  # continua marcado para a recepção
    types, _ = counts(db)
    assert types[TicketKind.PRIORITY] == 0
    assert types[TicketKind.GENERAL] == 2


def test_cannot_exceed_capacity(client, db, org, sent):
    make_event(db, org, capacity=4, priority=0)
    assert client.post(ORDERS, json=payload("a@x.com", ("Ana", "Bia", "Caio"))).status_code == 201
    response = client.post(ORDERS, json=payload("b@x.com", ("Davi", "Eva")))
    assert response.status_code == 409
    assert "Restam apenas 1" in response.json()["detail"]
    assert client.post(ORDERS, json=payload("c@x.com", ("Davi",))).status_code == 201
    response = client.post(ORDERS, json=payload("d@x.com", ("Fábio",)))
    assert response.json()["detail"] == "Inscrições esgotadas."
    types, session_total = counts(db)
    assert types[TicketKind.GENERAL] == 4
    assert session_total == 4


def test_overbooking_margin_allows_more_registrations_than_seats(client, db, org, sent):
    make_event(db, org, capacity=4, overbooking=50, priority=0)
    assert client.post(ORDERS, json=payload("a@x.com", ("Ana", "Bia", "Caio"))).status_code == 201
    assert client.post(ORDERS, json=payload("b@x.com", ("Davi", "Eva", "Fábio"))).status_code == 201
    assert client.post(ORDERS, json=payload("c@x.com", ("Gabi",))).status_code == 409


def test_limit_per_order_and_one_order_per_email(client, db, org, sent):
    make_event(db, org)
    too_many = payload(people=[f"P{i}" for i in range(6)])
    assert client.post(ORDERS, json=too_many).status_code == 422
    assert client.post(ORDERS, json=payload()).status_code == 201
    again = client.post(ORDERS, json=payload(email="MARIA@example.com"))
    assert again.status_code == 409
    assert "Já existe uma inscrição" in again.json()["detail"]


def test_registration_requires_open_status_and_consent(client, db, org, sent):
    event = make_event(db, org, status="published")
    assert client.post(ORDERS, json=payload()).status_code == 409
    event.status = EventStatus.OPEN
    db.commit()
    assert client.post(ORDERS, json=payload(consent=False)).status_code == 422


def test_honeypot_blocks_bots(client, db, org, sent):
    make_event(db, org)
    assert client.post(ORDERS, json=payload(website="spam")).status_code == 400
    assert db.query(Order).count() == 0


def test_email_failure_keeps_the_registration(client, db, org, monkeypatch):
    make_event(db, org)

    def fail(message):
        raise email_module.EmailError("Gmail fora do ar")

    monkeypatch.setattr(tickets_router, "send_email", fail)
    response = client.post(ORDERS, json=payload())
    assert response.status_code == 201
    assert response.json()["email_sent"] is False


def test_view_and_cancel_one_ticket_then_all(client, db, org, sent):
    make_event(db, org)
    body = client.post(ORDERS, json=payload(people=("Maria", "João"))).json()
    token = body["token"]

    assert client.get(f"/api/v1/public/orders/{token}").json()["code"] == body["code"]
    assert client.get("/api/v1/public/orders/forjado.123").status_code == 404

    joao = body["tickets"][1]["id"]
    after = client.post(f"/api/v1/public/orders/{token}/cancel", json={"ticket_ids": [joao]})
    assert [t["status"] for t in after.json()["tickets"]] == ["valid", "cancelled"]
    assert after.json()["tickets"][1]["qr"] is None
    assert after.json()["status"] == "confirmed"
    _, session_total = counts(db)
    assert session_total == 1

    final = client.post(f"/api/v1/public/orders/{token}/cancel", json={"ticket_ids": []}).json()
    assert final["status"] == "cancelled"
    types, session_total = counts(db)
    assert types[TicketKind.GENERAL] == 0 and session_total == 0

    # Vaga liberada: o mesmo e-mail pode se inscrever de novo.
    assert client.post(ORDERS, json=payload()).status_code == 201


def test_used_ticket_cannot_be_cancelled(client, db, org, sent):
    make_event(db, org)
    body = client.post(ORDERS, json=payload(people=("Maria",))).json()
    ticket = db.query(Ticket).one()
    ticket.status = "used"
    db.commit()
    response = client.post(f"/api/v1/public/orders/{body['token']}/cancel", json={})
    assert response.status_code == 409


def test_resend_is_generic_and_sends_only_when_registered(client, db, org, sent):
    make_event(db, org)
    client.post(ORDERS, json=payload())
    sent.clear()
    url = f"/api/v1/public/events/{SLUG}/resend"
    unknown = client.post(url, json={"email": "ninguem@example.com"})
    known = client.post(url, json={"email": "maria@example.com"})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert [m.to for m in sent] == ["maria@example.com"]


def test_settings_can_open_registrations_and_set_venue(client, admin, db, org):
    from tests.conftest import auth_headers

    make_event(db, org, status="draft")
    url = f"/api/v1/org/events/{SLUG}/settings"
    current = client.get(url, headers=auth_headers(client)).json()
    data = {
        **{
            k: current[k]
            for k in (
                "starts_at",
                "doors_open_at",
                "capacity",
                "overbooking_percent",
                "max_tickets_per_order",
                "priority_quota",
                "reserved_quotas",
            )
        },  # fmt: skip
        "status": "open",
        "venue_name": "Igreja Estabelecendo o Reino",
        "venue_address": "Rua Exemplo, 123 — São Paulo/SP",
    }
    body = client.put(url, json=data, headers=auth_headers(client)).json()
    assert body["status"] == "open"
    assert body["venue_name"] == "Igreja Estabelecendo o Reino"
    public = client.get(f"/api/v1/public/events/{SLUG}").json()
    assert public["venue_address"] == "Rua Exemplo, 123 — São Paulo/SP"
