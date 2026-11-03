"""Importa todos os modelos para que o Alembic e os testes enxerguem o metadata completo."""

from app.db.base import Base
from app.modules.auth.models import RefreshToken, User
from app.modules.broadcasts.models import Broadcast
from app.modules.checkin.models import Checkin
from app.modules.events.models import Event, EventSession
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.tickets.models import Order, Ticket, TicketType
from app.modules.waitlist.models import WaitlistEntry

__all__ = [
    "Base",
    "Broadcast",
    "Checkin",
    "Event",
    "EventSession",
    "Order",
    "Organization",
    "OrganizationMember",
    "RefreshToken",
    "Ticket",
    "TicketType",
    "User",
    "WaitlistEntry",
]
