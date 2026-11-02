import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# BIGINT no MySQL, INTEGER no SQLite (necessário para autoincremento nos testes)
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def new_public_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)


class PublicIdMixin:
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=new_public_id
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
