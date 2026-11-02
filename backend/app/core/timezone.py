"""O banco guarda datas em UTC sem fuso; a interface fala no horário do evento (Brasília)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def local_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=_tz())
    return value.astimezone(UTC).replace(tzinfo=None)


def utc_to_local(value: datetime) -> datetime:
    """Retorna o horário local sem fuso (para inputs datetime-local)."""
    return value.replace(tzinfo=UTC).astimezone(_tz()).replace(tzinfo=None)
