import pytest

from app.modules.organizations.models import Role
from app.modules.tickets import router as tickets_router
from tests.conftest import auth_headers, make_member
from tests.test_orders import ORDERS, SLUG, make_event, payload

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
SVG = (
    b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
)
EVENT_LOGO = f"/api/v1/org/events/{SLUG}/logo"


@pytest.fixture
def event(db, org):
    return make_event(db, org)


def upload(client, url, content, name="logo.png", headers=None):
    return client.post(url, files={"file": (name, content, "image/png")}, headers=headers)


def test_event_logo_upload_appears_publicly_and_replaces_old(client, admin, event):
    headers = auth_headers(client)
    first = upload(client, EVENT_LOGO, PNG, headers=headers).json()["logo_url"]
    assert first.startswith("/api/v1/public/assets/")
    image = client.get(first)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert "immutable" in image.headers["cache-control"]
    assert client.get(f"/api/v1/public/events/{SLUG}").json()["logo_url"] == first

    second = upload(client, EVENT_LOGO, PNG + b"x", headers=headers).json()["logo_url"]
    assert second != first
    assert client.get(first).status_code == 404  # a imagem antiga é apagada
    assert (
        client.get(f"/api/v1/org/events/{SLUG}/settings", headers=headers).json()["logo_url"]
        == second
    )

    assert client.delete(EVENT_LOGO, headers=headers).json() == {"logo_url": None}
    assert client.get(second).status_code == 404


def test_rejects_wrong_format_and_large_files(client, admin, event):
    headers = auth_headers(client)
    fake = upload(client, EVENT_LOGO, b"%PDF-1.4 nao e imagem", "logo.png", headers)
    assert fake.status_code == 415
    big = upload(client, EVENT_LOGO, PNG + b"0" * (1024 * 1024), headers=headers)
    assert big.status_code == 413


def test_svg_is_served_sandboxed(client, admin, event):
    url = upload(client, EVENT_LOGO, SVG, "logo.svg", auth_headers(client)).json()["logo_url"]
    response = client.get(url)
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in response.headers["content-security-policy"]


def test_only_admins_can_change_logos(client, db, org, event):
    make_member(db, org, "producao@igreja.org", Role.MANAGER)
    headers = auth_headers(client, "producao@igreja.org")
    assert upload(client, EVENT_LOGO, PNG, headers=headers).status_code == 403
    assert upload(client, "/api/v1/org/organization/logo", PNG, headers=headers).status_code == 403
    assert (
        client.put("/api/v1/org/organization", json={"name": "Outro"}, headers=headers).status_code
        == 403
    )


def test_organization_name_and_logo(client, admin, event):
    headers = auth_headers(client)
    body = client.put(
        "/api/v1/org/organization", json={"name": "  Ministério  Estabelecendo o Reino "},
        headers=headers,
    ).json()  # fmt: skip
    assert body["name"] == "Ministério Estabelecendo o Reino"
    logo = upload(client, "/api/v1/org/organization/logo", PNG, headers=headers).json()["logo_url"]
    public = client.get("/api/v1/public/organization").json()
    assert public == {"name": "Ministério Estabelecendo o Reino", "logo_url": logo}
    event_page = client.get(f"/api/v1/public/events/{SLUG}").json()
    assert event_page["organization_name"] == "Ministério Estabelecendo o Reino"
    assert event_page["organization_logo_url"] == logo


def test_ticket_email_carries_event_logo_and_organizer(client, admin, event, monkeypatch):
    sent = []
    monkeypatch.setattr(tickets_router, "send_email", sent.append)
    tickets_router.order_limiter.reset()
    headers = auth_headers(client)
    upload(client, EVENT_LOGO, PNG, headers=headers)
    client.put("/api/v1/org/organization", json={"name": "Ministério Estabelecendo o Reino"},
               headers=headers)  # fmt: skip
    client.post(ORDERS, json=payload())
    message = sent[0]
    assert message.attachments[0].inline_cid == "logo@eventmer"
    assert "cid:logo@eventmer" in message.html
    assert "Realização" in message.html and "Ministério Estabelecendo o Reino" in message.html


def test_svg_logo_is_left_out_of_email(client, admin, event, monkeypatch):
    sent = []
    monkeypatch.setattr(tickets_router, "send_email", sent.append)
    tickets_router.order_limiter.reset()
    upload(client, EVENT_LOGO, SVG, "logo.svg", auth_headers(client))
    client.post(ORDERS, json=payload())
    assert "cid:logo@eventmer" not in sent[0].html
