from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK, IdMixin, PublicIdMixin, TimestampMixin

# MEDIUMBLOB no MySQL (até 16 MB); o BLOB comum só guarda 64 KB.
Blob = LargeBinary().with_variant(mysql.MEDIUMBLOB(), "mysql")


class Asset(IdMixin, PublicIdMixin, TimestampMixin, Base):
    """Imagem enviada pelo painel (logo do evento ou da igreja), guardada no banco:
    a hospedagem gratuita apaga arquivos do disco a cada atualização."""

    __tablename__ = "assets"

    organization_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(40))
    size: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str | None] = mapped_column(String(200))
    data: Mapped[bytes] = mapped_column(Blob, deferred=True)
