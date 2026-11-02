"""Envio de e-mail com três backends:

- ``console``: não envia; registra no log (desenvolvimento e testes).
- ``smtp``: Gmail via SMTP + senha de app. Simples, mas **bloqueado em hospedagens
  gratuitas como o Render** (portas 25/465/587).
- ``gmail_api``: Gmail via API HTTPS com OAuth (refresh token). Funciona em
  hospedagem gratuita.
"""

import base64
import logging
import smtplib
import time
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, make_msgid

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("eventmer.email")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class EmailError(RuntimeError):
    pass


@dataclass
class Attachment:
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"
    inline_cid: str | None = None  # para imagens no corpo (ex.: QR Code)


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    html: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)


def build_mime(message: OutgoingEmail, settings: Settings) -> MimeMessage:
    sender = settings.email_from_address or settings.smtp_username
    if not sender:
        raise EmailError("EMAIL_FROM_ADDRESS não configurado.")
    mime = MimeMessage()
    mime["From"] = formataddr((settings.email_from_name, sender))
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    if settings.email_reply_to:
        mime["Reply-To"] = settings.email_reply_to
    mime.set_content(message.text)
    mime.add_alternative(message.html, subtype="html")
    html_part = mime.get_payload()[-1]

    for attachment in message.attachments:
        maintype, subtype = attachment.mime_type.split("/", 1)
        if attachment.inline_cid:
            html_part.add_related(
                attachment.content, maintype, subtype, cid=f"<{attachment.inline_cid}>"
            )
        else:
            mime.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename,
            )
    return mime


class _GmailTokenCache:
    access_token: str | None = None
    expires_at: float = 0.0


_token_cache = _GmailTokenCache()


def _gmail_access_token(settings: Settings, client: httpx.Client) -> str:
    if _token_cache.access_token and time.time() < _token_cache.expires_at - 60:
        return _token_cache.access_token
    response = client.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "refresh_token": settings.gmail_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        raise EmailError(f"Falha ao renovar o token do Gmail: {response.text[:300]}")
    body = response.json()
    _token_cache.access_token = body["access_token"]
    _token_cache.expires_at = time.time() + int(body.get("expires_in", 3600))
    return _token_cache.access_token


def _send_gmail_api(mime: MimeMessage, settings: Settings, client: httpx.Client) -> None:
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    token = _gmail_access_token(settings, client)
    response = client.post(
        GMAIL_SEND_URL, json={"raw": raw}, headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 401:  # token revogado/expirado antes do previsto
        _token_cache.access_token = None
        token = _gmail_access_token(settings, client)
        response = client.post(
            GMAIL_SEND_URL, json={"raw": raw}, headers={"Authorization": f"Bearer {token}"}
        )
    if response.status_code >= 300:
        raise EmailError(f"Gmail recusou o envio: {response.text[:300]}")


def _send_smtp(mime: MimeMessage, settings: Settings) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(mime)


def send_email(message: OutgoingEmail, http_client: httpx.Client | None = None) -> None:
    settings = get_settings()
    backend = settings.email_backend

    if backend == "console":
        logger.info(
            "[email:console] para=%s assunto=%s\n%s", message.to, message.subject, message.text
        )
        return

    mime = build_mime(message, settings)
    try:
        if backend == "smtp":
            _send_smtp(mime, settings)
        elif backend == "gmail_api":
            with http_client or httpx.Client(timeout=20) as client:
                _send_gmail_api(mime, settings, client)
        else:
            raise EmailError(f"EMAIL_BACKEND desconhecido: {backend}")
    except (OSError, smtplib.SMTPException, httpx.HTTPError) as exc:
        raise EmailError(f"Não foi possível enviar o e-mail: {exc}") from exc
    logger.info("E-mail enviado para %s (%s)", message.to, message.subject)
