import pytest

from app.modules.checkin import router as checkin_router
from app.modules.checkin.models import Checkin
from app.modules.organizations.models import Role
from app.modules.tickets import router as tickets_router
from app.modules.tickets.models import Ticket
from tests.conftest import auth_headers, make_member
from tests.test_orders import ORDERS, SLUG, make_event, payload

BASE = f"/api/v1/checkin/events/{SLUG}"


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setattr(tickets_router, "send_email", lambda m: None)
    checkin_router.login_limiter.reset()
    tickets_router.order_limiter.reset()


@pytest.fixture
def event(db, org):
    ev = make_event(db, org, capacity=10, priority=2)
    ev.checkin_code = "K7P3QX"
    db.commit()
    return ev


def volunteer(client, name="Ana", code="k7p3qx"):
    response = client.post(f"{BASE}/login", json={"code": code, "name": name})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def register(client, email="maria@example.com", people=("Maria", "João", "Vovó Rosa")):
    data = payload(email=email, people=people)
    data["attendees"][-1]["priority"] = True
    return client.post(ORDERS, json=data).json()


def test_volunteer_login_requires_correct_code(client, event):
    bad = client.post(f"{BASE}/login", json={"code": "ERRADO", "name": "Ana"})
    assert bad.status_code == 401
    headers = volunteer(client)
    me = client.get(f"{BASE}/me", headers=headers).json()
    assert me == {
        "name": "Ana",
        "event_slug": SLUG,
        "event_title": "CANTEMOS 2026",
        "can_undo": False,
    }


def test_regenerating_code_logs_out_volunteers(client, db, event, admin):
    headers = volunteer(client)
    new = client.post(
        f"/api/v1/org/events/{SLUG}/reception/code", headers=auth_headers(client)
    ).json()
    assert new["code"] != "K7P3QX" and len(new["code"]) == 6
    assert client.get(f"{BASE}/summary", headers=headers).status_code == 401
    volunteer(client, code=new["code"])


def test_scan_ok_then_already_then_family(client, event):
    order = register(client)
    headers = volunteer(client)
    maria = order["tickets"][0]

    first = client.post(f"{BASE}/scan", json={"qr": maria["qr"]}, headers=headers).json()
    assert first["result"] == "ok"
    assert first["ticket"]["name"] == "Maria"
    assert first["summary"]["present"] == 1
    assert first["summary"]["registered"] == 3
    family = {t["name"]: t["status"] for t in first["order"]["tickets"]}
    assert family == {"Maria": "used", "João": "valid", "Vovó Rosa": "valid"}

    again = client.post(f"{BASE}/scan", json={"qr": maria["qr"]}, headers=headers).json()
    assert again["result"] == "already"
    assert again["message"].startswith("Já entrou às ")
    assert again["message"].endswith("por Ana")

    brief = client.post(f"{BASE}/orders/{order['code']}/checkin", headers=headers).json()
    assert all(t["status"] == "used" for t in brief["tickets"])
    summary = client.get(f"{BASE}/summary", headers=headers).json()
    assert summary["present"] == 3
    assert summary["priority_present"] == 1


def test_invalid_and_cancelled_tickets(client, event):
    order = register(client)
    headers = volunteer(client)
    fake = client.post(f"{BASE}/scan", json={"qr": "EVM1.abc.0000"}, headers=headers).json()
    assert fake["result"] == "invalid"
    garbage = client.post(f"{BASE}/scan", json={"qr": "https://exemplo.com"}, headers=headers)
    assert garbage.json()["result"] == "invalid"

    joao = order["tickets"][1]
    client.post(f"/api/v1/public/orders/{order['token']}/cancel", json={"ticket_ids": [joao["id"]]})
    cancelled = client.post(f"{BASE}/scan", json={"qr": joao["qr"]}, headers=headers).json()
    assert cancelled["result"] == "cancelled"
    assert cancelled["summary"]["registered"] == 2


def test_ticket_from_another_event_is_rejected(client, db, org, event):
    from datetime import datetime

    from app.core.security import sign_qr
    from app.modules.events.models import Event, EventSession
    from app.modules.tickets.models import Order, TicketType

    other = Event(organization_id=org.id, slug="outro", title="Outro")
    db.add(other)
    db.flush()
    session = EventSession(event_id=other.id, name="X", starts_at=datetime(2026, 12, 1), capacity=5)
    db.add(session)
    db.flush()
    tt = TicketType(session_id=session.id, name="Geral", quantity=5)
    order = Order(
        code="OUT-AAAAA", organization_id=org.id, event_id=other.id, buyer_user_id=1,
        buyer_name="X", buyer_email="x@x.com",
    )  # fmt: skip
    db.add_all([tt, order])
    db.flush()
    ticket = Ticket(
        order_id=order.id, ticket_type_id=tt.id, session_id=session.id, attendee_name="X"
    )
    db.add(ticket)
    db.commit()
    headers = volunteer(client)
    result = client.post(f"{BASE}/scan", json={"qr": sign_qr(ticket.public_id)}, headers=headers)
    assert result.json()["result"] == "other_event"


def test_search_by_attendee_buyer_or_code_without_contact_data(client, event):
    order = register(client)
    register(client, email="pedro@example.com", people=("Pedro Lima",))
    headers = volunteer(client)
    by_kid = client.get(f"{BASE}/search", params={"q": "joão"}, headers=headers).json()
    assert [o["code"] for o in by_kid] == [order["code"]]
    by_code = client.get(f"{BASE}/search", params={"q": order["code"].lower()}, headers=headers)
    assert len(by_code.json()) == 1
    assert "maria@example.com" not in by_code.text  # voluntário não vê e-mail
    assert (
        client.get(f"{BASE}/search", params={"q": "lima"}, headers=headers).json()[0]["buyer_name"]
        == "Maria Silva"
    )


def test_volunteer_undoes_only_own_checkin_staff_undoes_any(client, db, org, event, admin):
    order = register(client)
    ana, bia = volunteer(client, "Ana"), volunteer(client, "Bia")
    maria = order["tickets"][0]
    client.post(f"{BASE}/scan", json={"qr": maria["qr"]}, headers=ana)

    assert client.post(f"{BASE}/tickets/{maria['id']}/undo", headers=bia).status_code == 403
    assert client.post(f"{BASE}/tickets/{maria['id']}/undo", headers=ana).status_code == 200
    client.post(f"{BASE}/scan", json={"qr": maria["qr"]}, headers=bia)
    staff = auth_headers(client)
    brief = client.post(f"{BASE}/tickets/{maria['id']}/undo", headers=staff).json()
    assert brief["tickets"][0]["status"] == "valid"
    history = db.query(Checkin).order_by(Checkin.id).all()
    assert [(c.operator_name, c.undone_by_name) for c in history] == [
        ("Ana", "Ana"),
        ("Bia", "admin"),
    ]


def test_staff_login_works_for_reception_but_not_strangers(client, db, org, event, admin):
    assert client.get(f"{BASE}/me", headers=auth_headers(client)).json()["can_undo"] is True
    assert client.get(f"{BASE}/summary").status_code == 401

    other_org_user_headers = None
    from app.modules.organizations.models import Organization

    other = Organization(name="Outra", slug="outra")
    db.add(other)
    db.commit()
    make_member(db, other, "estranho@x.com", Role.OWNER)
    other_org_user_headers = auth_headers(client, "estranho@x.com")
    assert client.get(f"{BASE}/summary", headers=other_org_user_headers).status_code == 403


def test_attendee_export_for_staff_only(client, db, org, event, admin):
    register(client)
    headers = auth_headers(client)
    rows = client.get(f"/api/v1/org/events/{SLUG}/attendees", headers=headers).json()
    assert [r["attendee_name"] for r in rows] == ["Maria", "João", "Vovó Rosa"]
    csv = client.get(f"/api/v1/org/events/{SLUG}/attendees.csv", headers=headers)
    assert csv.status_code == 200
    text = csv.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Inscrição;Responsável;E-mail")
    assert "Vovó Rosa" in text and "Sim" in text
    make_member(db, org, "recepcao@igreja.org", Role.CHECKIN)
    denied = client.get(
        f"/api/v1/org/events/{SLUG}/attendees", headers=auth_headers(client, "recepcao@igreja.org")
    )
    assert denied.status_code == 403
