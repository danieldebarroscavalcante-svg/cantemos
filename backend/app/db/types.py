from enum import StrEnum

from sqlalchemy import Enum


def str_enum(enum_cls: type[StrEnum]) -> Enum:
    """Enum guardado como VARCHAR (portável e fácil de migrar), validado pelo SQLAlchemy."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )
