import pytest

from app.modules.notifications.email import EmailError
from app.modules.organizations.models import Role
from app.modules.tickets import org_router
from app.modules.tickets import router as tickets_router
from app.modules.waitlist import service as waitlist_service
from tests.conftest import auth_headers, make_member
from tests.test_orders import ORDERS, SLUG, make_event, payload

REGS = f"/api/v1/org/events/{SLUG}/registrations"


@pytest.fixture
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr(tickets_router, "send_email", lambda m: None)
    monkeypatch.setattr(org_router, "send_email", sent.append)
    monkeypatch.setattr(waitlist_service, "send_email", lambda m: None)
    tickets_router.order_limiter.reset()
    return sent


def register(client, email="maria@example.com", people=("Maria Silva", "João Silva")):
    return client.post(ORDERS, json=payload(email=email, people=people)).json()


def test_lists_registrations_grouped_by_family_newest_first(client, db, org, admin, mails):
    make_event(db, org)
    first = register(client)
    second = register(client, email="ana@example.com", people=("Ana Souza",))
    regs = client.get(REGS, headers=auth_headers(client)).json()
    assert [r["code"] for r in regs] == [second["code"], first["code"]]
    maria = regs[1]
    assert (maria["buyer_email"], maria["buyer_phone"], maria["status"]) == (
        "maria@example.com", "(11) 99999-0000", "confirmed",
    )  # fmt: skip
    assert [t["attendee_name"] for t in maria["tickets"]] == ["Maria Silva", "João Silva"]
    assert maria["tickets"][0]["status"] == "valid" and maria["is_test"] is False


def test_fix_contact_and_names(client, db, org, admin, mails):
    make_event(db, org)
    order = register(client)
    headers = auth_headers(client)
    joao = order["tickets"][1]["id"]
    body = {
        "buyer_name": "  Maria   da Silva ",
        "buyer_email": "Maria.Nova@Example.com",
        "buyer_phone": "",
        "attendees": [{"id": joao, "name": "João Pedro Silva"}],
    }
    response = client.put(f"{REGS}/{order['code']}", json=body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert (data["buyer_name"], data["buyer_email"], data["buyer_phone"]) == (
        "Maria da Silva", "maria.nova@example.com", None,
    )  # fmt: skip
    assert data["tickets"][1]["attendee_name"] == "João Pedro Silva"

    # o e-mail novo vale para a regra de uma inscrição por e-mail
    other = register(client, email="ana@example.com", people=("Ana Souza",))
    body["buyer_email"] = "ana@example.com"
    response = client.put(f"{REGS}/{order['code']}", json=body, headers=headers)
    assert response.status_code == 409 and other["code"] in response.json()["detail"]


def test_resend_and_cancel_one_person_then_all(client, db, org, admin, mails):
    make_event(db, org)
    order = register(client)
    headers = auth_headers(client)
    response = client.post(f"{REGS}/{order['code']}/resend", headers=headers)
    assert response.status_code == 200 and mails[0].to == "maria@example.com"

    joao = order["tickets"][1]["id"]
    response = client.post(f"{REGS}/{order['code']}/cancel", json={"ticket_ids": [joao]},
                           headers=headers)  # fmt: skip
    assert [t["status"] for t in response.json()["tickets"]] == ["valid", "cancelled"]
    response = client.post(f"{REGS}/{order['code']}/cancel", json={"ticket_ids": []},
                           headers=headers)  # fmt: skip
    assert response.json()["status"] == "cancelled"
    resp = client.post(f"{REGS}/{order['code']}/resend", headers=headers)
    assert resp.status_code == 409


def test_resend_reports_email_failure(client, db, org, admin, mails, monkeypatch):
    make_event(db, org)
    order = register(client)

    def fail(message):
        raise EmailError("sem conexão")

    monkeypatch.setattr(org_router, "send_email", fail)
    resp = client.post(f"{REGS}/{order['code']}/resend", headers=auth_headers(client))
    assert resp.status_code == 502


def test_permissions_by_level(client, db, org, admin, mails):
    make_event(db, org)
    order = register(client)
    make_member(db, org, "prod@igreja.org", Role.MANAGER)
    make_member(db, org, "porta@igreja.org", Role.CHECKIN)

    prod = auth_headers(client, "prod@igreja.org")
    assert client.get(REGS, headers=prod).status_code == 200
    assert client.post(f"{REGS}/{order['code']}/resend", headers=prod).status_code == 200
    cancel = client.post(f"{REGS}/{order['code']}/cancel", json={"ticket_ids": []}, headers=prod)
    assert cancel.status_code == 403

    porta = auth_headers(client, "porta@igreja.org")
    assert client.get(REGS, headers=porta).status_code == 403  # recepção não vê contatos
    assert client.get(f"{REGS}/XXX-00000", headers=prod).status_code == 405
    resp = client.post(f"{REGS}/XXX-00000/resend", headers=prod)
    assert resp.status_code == 404
