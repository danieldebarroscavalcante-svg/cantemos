from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.modules.waitlist.models import WaitlistStatus


class WaitlistIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    quantity: int = Field(ge=1, le=50)
    consent: bool
    website: str | None = None  # honeypot


class WaitlistJoinOut(BaseModel):
    position: int
    quantity: int
    already: bool


class WaitlistRow(BaseModel):
    id: str
    position: int | None
    name: str
    email: str
    phone: str | None
    quantity: int
    status: WaitlistStatus
    created_at: datetime
    hold_until: datetime | None


class NotifyOut(BaseModel):
    notified: int
    free_seats: int
