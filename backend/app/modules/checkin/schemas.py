from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.tickets.models import AgeGroup, TicketStatus


class ReceptionLoginIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    name: str = Field(min_length=2, max_length=60, description="Nome do voluntário")


class ReceptionLoginOut(BaseModel):
    token: str
    event_slug: str
    event_title: str
    operator_name: str


class Summary(BaseModel):
    capacity: int  # lugares físicos
    registration_limit: int
    registered: int  # ingressos válidos + já utilizados
    present: int
    priority_present: int


class AttendeeOut(BaseModel):
    id: str
    name: str
    age_group: AgeGroup
    type_name: str
    priority: bool
    accessibility_need: str | None
    status: TicketStatus
    checked_in_at: datetime | None  # horário local
    checked_in_by: str | None


class OrderBrief(BaseModel):
    code: str
    buyer_name: str
    tickets: list[AttendeeOut]


class CheckinResult(BaseModel):
    result: Literal["ok", "already", "cancelled", "invalid", "other_event"]
    message: str
    ticket: AttendeeOut | None = None
    order: OrderBrief | None = None
    summary: Summary


class ScanIn(BaseModel):
    qr: str = Field(min_length=1, max_length=200)
    device_id: str | None = Field(default=None, max_length=64)


class OperatorOut(BaseModel):
    name: str
    event_slug: str
    event_title: str
    can_undo: bool


class ReceptionInfo(BaseModel):
    code: str | None
    checkin_path: str
