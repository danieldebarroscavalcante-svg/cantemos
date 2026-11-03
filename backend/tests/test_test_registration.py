import pytest

from app.modules.broadcasts import service as broadcast_service
from app.modules.checkin.models import Checkin
from app.modules.notifications import email as email_module
from app.modules.organizations.models import Role
from app.modules.tickets import router as tickets_router
from app.modules.tickets.models import Order, TicketKind
from tests.conftest import auth_headers, make_member
from tests.test_orders import ORDERS, SLUG, counts, make_event, payload

ORG = f"/api/v1/org/events/{SLUG}"


@pytest.fixture
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr(email_module, "send_email", sent.append)
    monkeypatch.setattr(tickets_router, "send_email", sent.append)
    monkeypatch.setattr(broadcast_service, "PAUSE_SECONDS", 0)
    tickets_router.order_limiter.reset()
    return sent


def test_full_flow_with_test_registration(client, db, org, admin, mails):
    event = make_event(db, org, capacity=10, priority=2, status="draft")
    event.checkin_code = "K7P3QX"
    db.commit()
    headers = auth_headers(client)

    # 1) cria mesmo com o evento em rascunho e envia o e-mail para quem está no painel
    created = client.post(f"{ORG}/test-registration", headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert (body["email"], body["people"], body["email_sent"]) == ("admin@igreja.org", 3, True)
    assert mails[0].to == "admin@igreja.org" and len(mails[0].attachments) == 3
    types, session_total = counts(db)
    assert session_total == 3 and types[TicketKind.PRIORITY] == 1  # idosa na cota de prioridade

    # 2) ingressos abrem pelo link e a recepção lê o QR
    order = client.get(f"/api/v1/public/orders/{body['token']}").json()
    assert [t["attendee_name"] for t in order["tickets"]][0].startswith("TESTE · ")
    volunteer = client.post(
        f"/api/v1/checkin/events/{SLUG}/login", json={"code": "K7P3QX", "name": "Ana"}
    ).json()["token"]
    scan = client.post(
        f"/api/v1/checkin/events/{SLUG}/scan",
        json={"qr": order["tickets"][0]["qr"]},
        headers={"Authorization": f"Bearer {volunteer}"},
    ).json()
    assert scan["result"] == "ok"
    assert client.get(f"{ORG}/test-registrations", headers=headers).json()[0]["present"] == 1

    # 3) não impede a inscrição real com o mesmo e-mail e não recebe lembretes
    event.status = "open"
    db.commit()
    real = client.post(ORDERS, json=payload(email="admin@igreja.org", people=("Admin Real",)))
    assert real.status_code == 201
    mails.clear()
    client.post(f"{ORG}/broadcasts", json={"kind": "tomorrow"}, headers=headers)
    assert len(mails) == 1  # só a inscrição real

    # 4) remover devolve as vagas e apaga o histórico de entrada do teste
    assert client.delete(f"{ORG}/test-registrations", headers=headers).json() == {"removed": 1}
    types, session_total = counts(db)
    assert session_total == 1 and types[TicketKind.PRIORITY] == 0
    assert db.query(Checkin).count() == 0
    assert db.query(Order).count() == 1


def test_only_admins_create_or_remove_tests(client, db, org, mails):
    make_event(db, org)
    make_member(db, org, "producao@igreja.org", Role.MANAGER)
    headers = auth_headers(client, "producao@igreja.org")
    assert client.post(f"{ORG}/test-registration", headers=headers).status_code == 403
    assert client.delete(f"{ORG}/test-registrations", headers=headers).status_code == 403
    assert client.get(f"{ORG}/test-registrations", headers=headers).status_code == 200
