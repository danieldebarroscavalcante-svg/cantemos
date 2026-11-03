import re

import pytest

from app.modules.organizations.models import Role
from app.modules.team import service as team_service
from tests.conftest import PASSWORD, auth_headers, make_member
from tests.test_orders import SLUG, make_event

ORG = f"/api/v1/org/events/{SLUG}"


@pytest.fixture
def mails(monkeypatch):
    sent = []
    monkeypatch.setattr(team_service, "send_email", sent.append)
    return sent


@pytest.fixture
def event(db, org):
    ev = make_event(db, org)
    ev.checkin_code = "K7P3QX"
    db.commit()
    return ev


def invite_token(message) -> str:
    return re.search(r"/convite/([\w\-\.]+)", message.html).group(1)


def accept(client, token, name="Nova Pessoa", password="senha-nova-123"):
    return client.post(f"/api/v1/auth/invite/{token}", json={"name": name, "password": password})


def add(client, headers, email, role, name="Fulana da Silva"):
    return client.post(f"{ORG}/team", json={"name": name, "email": email, "role": role},
                       headers=headers)  # fmt: skip


def test_invite_new_person_who_creates_password_and_gets_event_admin(client, admin, event, mails):
    response = add(client, auth_headers(client), "nova@igreja.org", "admin")
    assert response.status_code == 201
    member = next(m for m in response.json()["members"] if m["email"] == "nova@igreja.org")
    assert (member["label"], member["pending"], member["source"]) == (
        "Administrador do evento", True, "evento",
    )  # fmt: skip
    assert mails[0].to == "nova@igreja.org" and "Criar minha senha" in mails[0].html

    token = invite_token(mails[0])
    assert client.get(f"/api/v1/auth/invite/{token}").json()["email"] == "nova@igreja.org"
    created = accept(client, token)
    assert created.status_code == 200
    assert accept(client, token).status_code == 410  # convite é de uso único

    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    access = client.get(f"{ORG}/access", headers=headers).json()
    assert access["role"] == "admin" and access["permissions"]["edit_event"] is True
    assert client.get("/api/v1/org/events", headers=headers).json()[0]["my_role"] == "admin"
    # administra o evento, mas não a igreja
    assert client.get(f"{ORG}/settings", headers=headers).status_code == 200
    resp = client.put("/api/v1/org/organization", json={"name": "Outro nome"}, headers=headers)
    assert resp.status_code == 404


def test_levels_and_permissions(client, db, org, admin, event, mails):
    headers = auth_headers(client)
    for email, role in [("prod@x.org", "manager"), ("porta@x.org", "checkin")]:
        add(client, headers, email, role)
        accept(client, invite_token(mails[-1]), password="senha-forte-999")

    prod = {"Authorization": "Bearer " + client.post("/api/v1/auth/login", json={
        "email": "prod@x.org", "password": "senha-forte-999"}).json()["access_token"]}  # fmt: skip
    porta = {"Authorization": "Bearer " + client.post("/api/v1/auth/login", json={
        "email": "porta@x.org", "password": "senha-forte-999"}).json()["access_token"]}  # fmt: skip

    # Produção: vê números e inscritos, não edita nem gerencia equipe
    assert client.get(f"{ORG}/stats", headers=prod).status_code == 200
    assert client.get(f"{ORG}/attendees", headers=prod).status_code == 200
    assert client.post(f"{ORG}/reception/code", headers=prod).status_code == 403
    assert add(client, prod, "z@x.org", "checkin").status_code == 403
    # Recepção com login: só o check-in
    assert client.get(f"{ORG}/stats", headers=porta).status_code == 403
    me = client.get(f"/api/v1/checkin/events/{SLUG}/me", headers=porta).json()
    assert me["can_undo"] is False
    assert client.get(f"/api/v1/checkin/events/{SLUG}/me", headers=prod).json()["can_undo"] is True
    assert client.get("/api/v1/org/events", headers=porta).json()[0]["my_role"] == "checkin"


def test_existing_account_gets_notice_and_role_changes(client, db, org, admin, event, mails):
    from app.modules.organizations.models import Organization

    other = Organization(name="Outra", slug="outra")
    db.add(other)
    db.commit()
    make_member(db, other, "ja@tenho.org", Role.CHECKIN)  # conta existente, outra igreja
    headers = auth_headers(client)
    team = add(client, headers, "ja@tenho.org", "checkin").json()
    assert "Entrar no painel" in mails[0].html  # já tem senha: só o aviso
    member = next(m for m in team["members"] if m["email"] == "ja@tenho.org")
    assert member["pending"] is False

    changed = client.put(f"{ORG}/team/{member['id']}", json={"role": "manager"}, headers=headers)
    assert (
        next(m for m in changed.json()["members"] if m["id"] == member["id"])["role"] == "manager"
    )
    assert add(client, headers, "ja@tenho.org", "admin").status_code == 409  # já na equipe

    removed = client.delete(f"{ORG}/team/{member['id']}", headers=headers).json()
    assert all(m["email"] != "ja@tenho.org" for m in removed["members"])
    user_headers = auth_headers(client, "ja@tenho.org")
    assert client.get(f"{ORG}/access", headers=user_headers).status_code == 404


def test_church_owners_listed_read_only_and_cannot_be_added(client, admin, event, mails):
    team = client.get(f"{ORG}/team", headers=auth_headers(client)).json()
    owner = team["members"][0]
    assert (owner["source"], owner["editable"], owner["is_me"]) == ("igreja", False, True)
    assert add(client, auth_headers(client), "admin@igreja.org", "admin").status_code in (409, 422)


def test_event_admin_cannot_change_own_level(client, admin, event, mails):
    add(client, auth_headers(client), "adm@x.org", "admin")
    token = accept(client, invite_token(mails[-1])).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = next(m for m in client.get(f"{ORG}/team", headers=headers).json()["members"] if m["is_me"])
    assert me["editable"] is False
    assert (
        client.put(f"{ORG}/team/{me['id']}", json={"role": "checkin"}, headers=headers).status_code
        == 403
    )
    assert client.delete(f"{ORG}/team/{me['id']}", headers=headers).status_code == 403


def test_invalid_invite_token(client):
    assert client.get("/api/v1/auth/invite/token-falso").status_code == 410
    assert PASSWORD
