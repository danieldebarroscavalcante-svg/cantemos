from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.events import service
from app.modules.events.models import Event
from app.modules.events.schemas import EventSettingsIn, EventSettingsOut, EventSummary
from app.modules.organizations.models import OrganizationMember, Role

router = APIRouter(prefix="/org/events", tags=["organizador · eventos"])

VIEW_ROLES = (Role.OWNER, Role.ADMIN, Role.MANAGER)
EDIT_ROLES = (Role.OWNER, Role.ADMIN)


def _event_for(db: Session, user: User, slug: str, roles: tuple[Role, ...]) -> Event:
    row = db.execute(
        select(Event, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Event.organization_id)
        .where(Event.slug == slug, OrganizationMember.user_id == user.id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    event, role = row
    if role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta ação.")
    return event


@router.get("", response_model=list[EventSummary])
def list_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = db.scalars(
        select(Event)
        .join(OrganizationMember, OrganizationMember.organization_id == Event.organization_id)
        .where(OrganizationMember.user_id == user.id, OrganizationMember.role.in_(VIEW_ROLES))
        .order_by(Event.created_at.desc())
    )
    return [service.summarize(db, event) for event in events]


@router.get("/{slug}/settings", response_model=EventSettingsOut)
def get_event_settings(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return service.get_settings_out(db, _event_for(db, user, slug, VIEW_ROLES))


@router.put("/{slug}/settings", response_model=EventSettingsOut)
def update_event_settings(
    slug: str,
    payload: EventSettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    result = service.update_settings(db, event, payload)
    # Lotação aumentada ou inscrições reabertas: chama a lista de espera.
    from app.modules.waitlist.service import notify_next

    notify_next(db, event)
    return result
