import pytest

from app.modules.broadcasts import service as broadcast_service
from app.modules.notifications import email as email_module
from app.modules.tickets import router as tickets_router
from tests.conftest import auth_headers
from tests.test_orders import ORDERS, SLUG, make_event, payload

ORG = f"/api/v1/org/events/{SLUG}"


@pytest.fixture
def setup(client, db, org, admin, monkeypatch):
    monkeypatch.setattr(tickets_router, "send_email", lambda m: None)
    monkeypatch.setattr(broadcast_service, "PAUSE_SECONDS", 0)
    tickets_router.order_limiter.reset()
    make_event(db, org, capacity=20, priority=2)
    a = client.post(ORDERS, json=payload("a@x.com", ("Ana", "Bia"), source="instagram")).json()
    client.post(ORDERS, json=payload("b@x.com", ("Caio",)))
    c = client.post(ORDERS, json=payload("c@x.com", ("Davi",))).json()
    client.post(f"/api/v1/public/orders/{c['token']}/cancel", json={})
    return a


def test_reminder_goes_to_active_registrations_with_qr(client, setup, monkeypatch):
    sent = []
    monkeypatch.setattr(email_module, "send_email", sent.append)
    headers = auth_headers(client)
    assert client.get(f"{ORG}/broadcasts/recipients", headers=headers).json() == {"recipients": 2}
    started = client.post(f"{ORG}/broadcasts", json={"kind": "tomorrow"}, headers=headers)
    assert started.status_code == 202
    assert sorted(m.to for m in sent) == ["a@x.com", "b@x.com"]
    assert all(m.subject == "É amanhã! · CANTEMOS 2026" for m in sent)
    assert all(m.attachments for m in sent)  # QR Codes de novo, para usar sem internet
    history = client.get(f"{ORG}/broadcasts", headers=headers).json()
    assert history[0]["status"] == "done"
    assert (history[0]["sent"], history[0]["failed"], history[0]["total"]) == (2, 0, 2)


def test_one_failure_does_not_stop_the_others(client, setup, monkeypatch):
    def flaky(message):
        if message.to == "a@x.com":
            raise email_module.EmailError("falhou")

    monkeypatch.setattr(email_module, "send_email", flaky)
    client.post(f"{ORG}/broadcasts", json={"kind": "confirm"}, headers=auth_headers(client))
    last = client.get(f"{ORG}/broadcasts", headers=auth_headers(client)).json()[0]
    assert (last["sent"], last["failed"]) == (1, 1)


def test_stats(client, setup):
    body = client.get(f"{ORG}/stats", headers=auth_headers(client)).json()
    assert body["registered"] == 3
    assert body["cancelled"] == 1
    assert body["orders"] == 2
    assert {c["label"]: c["people"] for c in body["by_source"]} == {
        "instagram": 2,
        "Link direto": 1,
    }
    assert body["by_age"][0] == {"label": "Adultos", "people": 3}
    assert body["emails_not_sent"] == 0
