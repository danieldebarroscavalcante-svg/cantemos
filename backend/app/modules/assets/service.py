"""Logos enviados pelo painel: validação do arquivo, gravação no banco e entrega pública."""

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.modules.assets.models import Asset

MAX_BYTES = 1024 * 1024  # 1 MB
RASTER = {"image/png", "image/jpeg", "image/webp"}
EMAIL_SAFE = {"image/png", "image/jpeg"}  # o que os programas de e-mail exibem


def detect_type(data: bytes) -> str | None:
    """Identifica o formato pelo conteúdo (não confia na extensão nem no navegador)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    head = data[:1024].lstrip().lower()
    if (head.startswith(b"<svg") or head.startswith(b"<?xml")) and b"<svg" in data[:4096].lower():
        return "image/svg+xml"
    return None


BANNER_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


async def read_upload(file: UploadFile, max_bytes: int = MAX_BYTES) -> tuple[bytes, str]:
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo maior que {max_bytes // (1024 * 1024)} MB. Reduza o tamanho da imagem e "
            "tente de novo.",
        )
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Arquivo vazio.")
    content_type = detect_type(data)
    if content_type is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Formato não aceito. Envie PNG, JPG, WEBP ou SVG.",
        )
    return data, content_type


def save(db: Session, organization_id: int, data: bytes, content_type: str, filename: str | None):
    asset = Asset(
        organization_id=organization_id,
        content_type=content_type,
        size=len(data),
        filename=(filename or "")[:200] or None,
        data=data,
    )
    db.add(asset)
    db.flush()
    return asset


def url(asset_public_id: str | None) -> str | None:
    return f"/api/v1/public/assets/{asset_public_id}" if asset_public_id else None
