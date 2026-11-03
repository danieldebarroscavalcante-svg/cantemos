"""Utilitários dos e-mails de ingresso: QR Code em PNG e data por extenso.
O layout fica em notifications/layout.py e os textos em messages/service.py."""

import io
from datetime import datetime

import segno

WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]  # fmt: skip
AGE_LABEL = {"adulto": "Adulto", "crianca": "Criança", "idoso": "Idoso"}


def format_when(value: datetime) -> str:
    return (
        (
            f"{WEEKDAYS[value.weekday()]}-feira, {value.day} de {MONTHS[value.month - 1]}"
            f" às {value:%H:%M}"
        )
        .replace("sábado-feira", "sábado")
        .replace("domingo-feira", "domingo")
    )


def qr_png(content: str) -> bytes:
    buffer = io.BytesIO()
    segno.make(content, error="m").save(buffer, kind="png", scale=8, border=2)
    return buffer.getvalue()
