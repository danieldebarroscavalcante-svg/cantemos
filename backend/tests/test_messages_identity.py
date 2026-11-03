import pytest

from app.modules.notifications import email as email_module
from app.modules.organizations.models import Role
from app.modules.tickets import router as tickets_router
from tests.conftest import auth_headers, make_member
from tests.test_orders import ORDERS, SLUG, make_event, payload

MSG = f"/api/v1/org/events/{SLUG}/messages"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
TEXTS = {
    "subject": "Olá {nome}, seu lugar no {evento} ({codigo})",
    "heading": "Tudo certo, {nome}!",
    "body": "Linha 1 com {data}.\n\nLinha 2 com {hora}.",
    "button_label": "Abrir ingressos",
}


@pytest.fixture
def event(db, org):
    return make_event(db, org)


def test_lists_all_messages_with_defaults_and_fields(client, admin, event):
    items = client.get(MSG, headers=auth_headers(client)).json()
    kinds = [i["kind"] for i in items]
    assert kinds == [
        "confirmation",
        "reminder_confirm",
        "reminder_tomorrow",
        "waitlist_joined",
        "waitlist_invite",
    ]
    confirmation = items[0]
    assert confirmation["custom"] is False
    assert confirmation["subject"] == "Seu ingresso · {evento} · {codigo}"
    assert {"key": "codigo", "label": "Código da inscrição"} in confirmation["fields"]
    invite = items[-1]
    assert {"key": "prazo", "label": "Prazo da vaga guardada"} in invite["fields"]


def test_preview_renders_live_draft_with_sample_data(client, admin, event):
    body = client.post(f"{MSG}/confirmation/preview", json=TEXTS, headers=auth_headers(client))
    preview = body.json()
    assert preview["subject"] == "Olá Maria, seu lugar no CANTEMOS 2026 (CAN-EXEMP)"
    assert "Tudo certo, Maria!" in preview["html"]
    assert "data:image/png;base64," in preview["html"]  # QR de exemplo embutido
    waitlist = client.post(f"{MSG}/waitlist_invite/preview", json={
        **TEXTS, "body": "Vaga até {prazo} para {pessoas}.",
    }, headers=auth_headers(client)).json()  # fmt: skip
    assert "Vaga até " in waitlist["html"] and "para 2." in waitlist["html"]


def test_saved_template_is_used_on_real_email_and_can_be_reset(client, admin, event, monkeypatch):
    sent = []
    monkeypatch.setattr(tickets_router, "send_email", sent.append)
    tickets_router.order_limiter.reset()
    headers = auth_headers(client)
    saved = client.put(f"{MSG}/confirmation", json=TEXTS, headers=headers).json()
    assert saved["custom"] is True
    order = client.post(ORDERS, json=payload()).json()
    assert sent[0].subject == f"Olá Maria, seu lugar no CANTEMOS 2026 ({order['code']})"
    assert "Abrir ingressos" in sent[0].html

    reset = client.delete(f"{MSG}/confirmation", headers=headers).json()
    assert reset["custom"] is False and reset["subject"].startswith("Seu ingresso")


def test_send_test_message_to_myself(client, admin, event, monkeypatch):
    sent = []
    monkeypatch.setattr(email_module, "send_email", sent.append)
    response = client.post(
        f"{MSG}/reminder_tomorrow/test", json=TEXTS, headers=auth_headers(client)
    )
    assert response.json() == {"sent_to": "admin@igreja.org"}
    assert sent[0].to == "admin@igreja.org" and sent[0].subject.startswith("[TESTE] ")
    assert sent[0].attachments  # QR de exemplo como anexo embutido


def test_manager_can_preview_but_not_save(client, db, org, event):
    make_member(db, org, "producao@igreja.org", Role.MANAGER)
    headers = auth_headers(client, "producao@igreja.org")
    assert (
        client.post(f"{MSG}/confirmation/preview", json=TEXTS, headers=headers).status_code == 200
    )
    assert client.put(f"{MSG}/confirmation", json=TEXTS, headers=headers).status_code == 403
    assert client.get(f"{MSG}/inexistente/preview", headers=headers).status_code in (404, 405)


def test_event_identity_name_theme_and_banner(client, admin, event):
    headers = auth_headers(client)
    url = f"/api/v1/org/events/{SLUG}"
    identity = {"title": " CANTEMOS  2026 ", "subtitle": "O maior presente"}
    body = client.put(f"{url}/identity", json=identity, headers=headers).json()
    assert (body["title"], body["subtitle"]) == ("CANTEMOS 2026", "O maior presente")
    banner = client.post(f"{url}/banner", files={"file": ("b.png", PNG, "image/png")},
                         headers=headers).json()["banner_url"]  # fmt: skip
    public = client.get(f"/api/v1/public/events/{SLUG}").json()
    assert public["banner_url"] == banner and public["subtitle"] == "O maior presente"
    too_big = PNG + b"0" * (2 * 1024 * 1024)
    big = client.post(
        f"{url}/banner", files={"file": ("b.png", too_big, "image/png")}, headers=headers
    )
    assert big.status_code == 413
    assert client.delete(f"{url}/banner", headers=headers).json()["banner_url"] is None
