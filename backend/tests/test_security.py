from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    sign_qr,
    verify_password,
    verify_qr,
)


def test_password_hash_roundtrip():
    hashed = hash_password("segredo-123")
    assert hashed.startswith("$2b$12$")
    assert verify_password("segredo-123", hashed)
    assert not verify_password("outro", hashed)
    assert not verify_password("qualquer", None)


def test_access_token_roundtrip():
    assert decode_access_token(create_access_token(42)) == 42
    assert decode_access_token("token-invalido") is None


def test_qr_signature_detects_tampering():
    content = sign_qr("abc123")
    assert verify_qr(content) == "abc123"
    tampered = content.replace("abc123", "abc124")
    assert verify_qr(tampered) is None
    assert verify_qr("qualquer coisa") is None
