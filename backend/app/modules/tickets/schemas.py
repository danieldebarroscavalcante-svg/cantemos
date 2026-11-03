from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.events.models import EventStatus
from app.modules.tickets.models import AgeGroup, OrderStatus, TicketStatus


class WaitlistInvite(BaseModel):
    name: str
    quantity: int
    hold_until: datetime  # horário local


class PublicEvent(BaseModel):
    slug: str
    title: str
    subtitle: str | None
    description: str | None
    venue_name: str | None
    venue_address: str | None
    status: EventStatus
    starts_at: datetime  # horário local do evento
    doors_open_at: datetime | None
    max_tickets_per_order: int
    available: int  # vagas na inscrição pública (gerais + prioridade), já sem as guardadas
    priority_available: int
    waitlist_waiting: int = 0  # pessoas/grupos aguardando na lista de espera
    invite: WaitlistInvite | None = None  # quando acessado pelo link da lista de espera


class AttendeeIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    age_group: AgeGroup = AgeGroup.ADULT
    priority: bool = False
    accessibility_need: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Informe o nome.")
        return value


class OrderIn(BaseModel):
    buyer_name: str = Field(min_length=2, max_length=150)
    buyer_email: EmailStr
    buyer_phone: str | None = Field(default=None, max_length=30)
    attendees: list[AttendeeIn] = Field(min_length=1, max_length=50)
    consent: bool
    source: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, description="Honeypot: deve ficar vazio")
    waitlist_token: str | None = Field(default=None, max_length=120)


class TicketOut(BaseModel):
    id: str
    attendee_name: str
    age_group: AgeGroup
    type_name: str
    priority: bool
    accessibility_need: str | None
    status: TicketStatus
    qr: str | None  # conteúdo do QR Code (só para ingressos válidos)


class OrderOut(BaseModel):
    code: str
    token: str
    status: OrderStatus
    buyer_name: str
    buyer_email: str
    created_at: datetime
    email_sent: bool
    event: PublicEvent
    tickets: list[TicketOut]


class CancelIn(BaseModel):
    ticket_ids: list[str] = Field(
        default_factory=list, description="Vazio = cancelar a inscrição inteira"
    )


class ResendIn(BaseModel):
    email: EmailStr
