from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.events.models import EventStatus


class EventSummary(BaseModel):
    slug: str
    title: str
    status: EventStatus
    starts_at: datetime | None  # horário local (Brasília)
    capacity: int
    registration_limit: int
    registered: int


class ReservedQuotaIn(BaseModel):
    id: str | None = Field(default=None, description="Vazio para criar uma nova cota")
    name: str = Field(min_length=2, max_length=100)
    quantity: int = Field(ge=0, le=10_000)


class ReservedQuotaOut(ReservedQuotaIn):
    id: str
    issued: int


class EventSettingsIn(BaseModel):
    """Configurações do evento. Datas no horário local do evento (sem fuso)."""

    starts_at: datetime
    doors_open_at: datetime | None = None
    capacity: int = Field(ge=1, le=100_000, description="Lugares físicos")
    overbooking_percent: int = Field(ge=0, le=100, description="Margem acima da lotação")
    max_tickets_per_order: int = Field(ge=1, le=50)
    priority_quota: int = Field(ge=0, le=100_000)
    reserved_quotas: list[ReservedQuotaIn] = Field(default_factory=list, max_length=20)
    # Opcionais: None mantém o valor atual.
    status: EventStatus | None = None
    venue_name: str | None = Field(default=None, max_length=150)
    venue_address: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def doors_before_start(self) -> "EventSettingsIn":
        if self.doors_open_at and self.doors_open_at > self.starts_at:
            raise ValueError("A abertura das portas precisa ser antes do início.")
        return self


class QuotaUsage(BaseModel):
    quantity: int
    issued: int


class EventSettingsOut(BaseModel):
    slug: str
    title: str
    status: EventStatus
    venue_name: str | None
    venue_address: str | None
    description: str | None
    logo_url: str | None = None
    starts_at: datetime
    doors_open_at: datetime | None
    capacity: int
    overbooking_percent: int
    max_tickets_per_order: int
    priority_quota: int
    reserved_quotas: list[ReservedQuotaOut]
    # Calculados
    registration_limit: int
    general: QuotaUsage
    priority: QuotaUsage
    registered: int
