from datetime import timedelta

import pytest

from app.core.security import sign_waitlist_token
from app.db.base import utcnow
from app.modules.tickets import router as tickets_router
from app.modules.waitlist import service as waitlist_service
from app.modules.waitlist.models import WaitlistEntry, WaitlistStatus
from tests.conftest import auth_headers
from tests.test_orders import ORDERS, SLUG, make_event, payload

EVENT = f"/api/v1/public/events/{SLUG}"


@pytest.fixture
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr(tickets_router, "send_email", lambda m: None)
    monkeypatch.setattr(waitlist_service, "send_email", sent.append)
    tickets_router.order_limiter.reset()
    tickets_router.waitlist_limiter.reset()
    return sent


def join(client, email, quantity=1, name="Fila Silva"):
    return client.post(
        f"{EVENT}/waitlist",
        json={"name": name, "email": email, "quantity": quantity, "consent": True},
    )


def fill(client, n_people=4):
    people = [f"Pessoa {i}" for i in range(n_people)]
    return client.post(ORDERS, json=payload(email="cheio@x.com", people=people)).json()


def test_cannot_join_while_seats_are_available(client, db, org, mails):
    make_event(db, org, capacity=4, priority=0)
    response = join(client, "a@x.com")
    assert response.status_code == 409
    assert "Ainda há vagas" in response.json()["detail"]


def test_join_when_sold_out_returns_position_and_is_idempotent(client, db, org, mails):
    make_event(db, org, capacity=4, priority=0)
    fill(client)
    first = join(client, "a@x.com", 2).json()
    second = join(client, "b@x.com").json()
    again = join(client, "A@x.com").json()
    assert (first["position"], second["position"]) == (1, 2)
    assert again == {"position": 1, "quantity": 2, "already": True}
    assert [m.subject for m in mails] == ["Lista de espera · CANTEMOS 2026"] * 2
    assert client.get(EVENT).json()["waitlist_waiting"] == 2


def test_cancellation_invites_next_and_holds_the_seats(client, db, org, mails):
    make_event(db, org, capacity=4, priority=0)
    order = fill(client)
    join(client, "a@x.com", 2)
    join(client, "b@x.com", 1)
    mails.clear()

    # Duas pessoas cancelam: a primeira da fila (2 pessoas) é chamada.
    ids = [t["id"] for t in order["tickets"][:2]]
    client.post(f"/api/v1/public/orders/{order['token']}/cancel", json={"ticket_ids": ids})
    assert [m.to for m in mails] == ["a@x.com"]
    assert mails[0].subject.startswith("Abriu vaga!")
    entry = db.query(WaitlistEntry).filter_by(email="a@x.com").one()
    token = sign_waitlist_token(entry.public_id)
    assert token in mails[0].html

    # Para o público as vagas guardadas não aparecem…
    public = client.get(EVENT).json()
    assert public["available"] == 0 and public["invite"] is None
    blocked = client.post(ORDERS, json=payload(email="intruso@x.com", people=("Intruso",)))
    assert blocked.json()["detail"] == "Inscrições esgotadas."

    # …mas quem tem o link vê e consegue se inscrever.
    invited_view = client.get(EVENT, params={"lista": token}).json()
    assert invited_view["available"] == 2
    assert invited_view["invite"]["quantity"] == 2
    data = payload(email="a@x.com", people=("Ana", "Beto"), waitlist_token=token)
    assert client.post(ORDERS, json=data).status_code == 201
    db.refresh(entry)
    assert entry.status == WaitlistStatus.REGISTERED


def test_expired_hold_passes_to_next(client, db, org, mails):
    make_event(db, org, capacity=4, priority=0)
    order = fill(client)
    join(client, "a@x.com", 1)
    join(client, "b@x.com", 1)
    client.post(
        f"/api/v1/public/orders/{order['token']}/cancel",
        json={"ticket_ids": [order["tickets"][0]["id"]]},
    )
    first = db.query(WaitlistEntry).filter_by(email="a@x.com").one()
    first.hold_until = utcnow() - timedelta(minutes=1)  # passou o prazo de 24 h
    db.commit()
    mails.clear()

    client.get(EVENT)  # abrir a página repassa a vaga vencida
    db.refresh(first)
    assert first.status == WaitlistStatus.EXPIRED
    assert [m.to for m in mails] == ["b@x.com"]
    old_link = client.get(EVENT, params={"lista": sign_waitlist_token(first.public_id)}).json()
    assert old_link["invite"] is None


def test_larger_group_waits_while_smaller_fits(client, db, org, mails):
    make_event(db, org, capacity=4, priority=0)
    order = fill(client)
    join(client, "grupo@x.com", 3)
    join(client, "sozinho@x.com", 1)
    mails.clear()
    client.post(
        f"/api/v1/public/orders/{order['token']}/cancel",
        json={"ticket_ids": [order["tickets"][0]["id"]]},
    )
    assert [m.to for m in mails] == ["sozinho@x.com"]


def test_admin_sees_queue_and_can_notify_after_raising_capacity(client, db, org, admin, mails):
    make_event(db, org, capacity=4, priority=0)
    fill(client)
    join(client, "a@x.com", 2)
    headers = auth_headers(client)
    rows = client.get(f"/api/v1/org/events/{SLUG}/waitlist", headers=headers).json()
    assert rows[0]["position"] == 1 and rows[0]["email"] == "a@x.com"

    settings = client.get(f"/api/v1/org/events/{SLUG}/settings", headers=headers).json()
    body = {k: settings[k] for k in (
        "starts_at", "doors_open_at", "capacity", "overbooking_percent",
        "max_tickets_per_order", "priority_quota", "reserved_quotas",
    )}  # fmt: skip
    body["capacity"] = 6
    mails.clear()
    client.put(f"/api/v1/org/events/{SLUG}/settings", json=body, headers=headers)
    assert [m.to for m in mails] == ["a@x.com"]  # aumentar a lotação chama a fila
    result = client.post(f"/api/v1/org/events/{SLUG}/waitlist/notify", headers=headers).json()
    assert result == {"notified": 0, "free_seats": 0}
