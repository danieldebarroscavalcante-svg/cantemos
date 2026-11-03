import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def checkin_code_fingerprint(code: str) -> str:
    return hashlib.sha256(f"checkin:{code}".encode()).hexdigest()[:12]


def create_checkin_token(event_id: int, name: str, code: str, hours: int = 14) -> str:
    """Token do voluntário da recepção: vale só para o check-in de um evento e deixa de
    valer quando o código da recepção é trocado."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "type": "checkin",
        "event": event_id,
        "name": name,
        "cv": checkin_code_fingerprint(code),
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return int(payload["sub"])


def new_opaque_token() -> str:
    """Token aleatório para refresh / link mágico. Guardamos só o hash."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sign_qr(ticket_public_id: str) -> str:
    """Conteúdo do QR Code: id público + assinatura HMAC truncada. Sem dados pessoais."""
    secret = get_settings().qr_secret.encode()
    signature = hmac.new(secret, ticket_public_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"EVM1.{ticket_public_id}.{signature}"


def verify_qr(qr_content: str) -> str | None:
    """Retorna o id público do ingresso se a assinatura for válida."""
    parts = qr_content.strip().split(".")
    if len(parts) != 3 or parts[0] != "EVM1":
        return None
    expected = sign_qr(parts[1])
    return parts[1] if hmac.compare_digest(expected, qr_content.strip()) else None


def sign_order_token(order_public_id: str) -> str:
    """Token do link "meus ingressos" enviado por e-mail (acesso sem senha)."""
    secret = get_settings().qr_secret.encode()
    signature = hmac.new(secret, f"order:{order_public_id}".encode(), hashlib.sha256)
    return f"{order_public_id}.{signature.hexdigest()[:24]}"


def verify_order_token(token: str) -> str | None:
    public_id, _, _ = token.partition(".")
    if not public_id:
        return None
    return public_id if hmac.compare_digest(sign_order_token(public_id), token) else None


def sign_waitlist_token(entry_public_id: str) -> str:
    """Link pessoal de quem foi chamado da lista de espera."""
    secret = get_settings().qr_secret.encode()
    signature = hmac.new(secret, f"wait:{entry_public_id}".encode(), hashlib.sha256)
    return f"{entry_public_id}.{signature.hexdigest()[:24]}"


def verify_waitlist_token(token: str) -> str | None:
    public_id, _, _ = token.partition(".")
    if not public_id:
        return None
    return public_id if hmac.compare_digest(sign_waitlist_token(public_id), token) else None


def _password_fingerprint(password_hash: str | None) -> str:
    return hashlib.sha256(f"pw:{password_hash or ''}".encode()).hexdigest()[:12]


def create_invite_token(user_id: int, password_hash: str | None, days: int = 7) -> str:
    """Convite para criar a senha. Deixa de valer quando a senha muda (uso único)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "type": "invite",
        "sub": str(user_id),
        "pv": _password_fingerprint(password_hash),
        "iat": now,
        "exp": now + timedelta(days=days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_invite_token(token: str) -> tuple[int, str] | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "invite":
        return None
    return int(payload["sub"]), str(payload.get("pv", ""))


def invite_matches(fingerprint: str, password_hash: str | None) -> bool:
    return hmac.compare_digest(fingerprint, _password_fingerprint(password_hash))
