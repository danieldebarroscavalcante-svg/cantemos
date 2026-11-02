import base64
import email
import json

import httpx
import pytest

from app.core.config import get_settings
from app.modules.notifications import email as email_module
from app.modules.notifications.email import Attachment, OutgoingEmail, build_mime, send_email

MESSAGE = OutgoingEmail(
    to="maria@example.com",
    subject="Seu ingresso",
    text="Olá",
    html='<p>Olá</p><img src="cid:qr">',
    attachments=[Attachment("qr.png", b"\x89PNG", "image/png", inline_cid="qr")],
)


@pytest.fixture
def gmail_settings(monkeypatch):
    settings = get_settings()
    for key, value in {
        "email_backend": "gmail_api",
        "email_from_address": "cantemos@gmail.com",
        "email_from_name": "CANTEMOS",
        "gmail_client_id": "id",
        "gmail_client_secret": "secret",
        "gmail_refresh_token": "refresh",
    }.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr(email_module._token_cache, "access_token", None)
    return settings


def test_build_mime_has_text_html_and_inline_image(gmail_settings):
    mime = build_mime(MESSAGE, gmail_settings)
    assert mime["From"] == "CANTEMOS <cantemos@gmail.com>"
    types = [part.get_content_type() for part in mime.walk()]
    assert {"text/plain", "text/html", "image/png"} <= set(types)


def test_gmail_api_backend_refreshes_token_and_sends(gmail_settings):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url == email_module.GOOGLE_TOKEN_URL:
            return httpx.Response(200, json={"access_token": "abc", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer abc"
        return httpx.Response(200, json={"id": "1"})

    send_email(MESSAGE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert len(calls) == 2
    sent = email.message_from_bytes(base64.urlsafe_b64decode(json.loads(calls[1].content)["raw"]))
    assert sent["To"] == "maria@example.com"


def test_gmail_api_error_is_reported(gmail_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    with pytest.raises(email_module.EmailError, match="token"):
        send_email(MESSAGE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_console_backend_does_not_need_configuration(monkeypatch):
    monkeypatch.setattr(get_settings(), "email_backend", "console")
    send_email(MESSAGE)
