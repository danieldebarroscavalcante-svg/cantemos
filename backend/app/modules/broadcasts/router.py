from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import get_current_user
from app.core.timezone import utc_to_local
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.broadcasts import service
from app.modules.broadcasts.models import Broadcast, BroadcastKind, BroadcastStatus
from app.modules.events.router import EDIT_ROLES, VIEW_ROLES, _event_for
from app.modules.waitlist import service as waitlist
from app.modules.waitlist.schemas import NotifyOut, WaitlistRow

router = APIRouter(prefix="/org/events/{slug}", tags=["organizador · comunicação"])


class BroadcastIn(BaseModel):
    kind: BroadcastKind


class BroadcastOut(BaseModel):
    id: int
    kind: BroadcastKind
    status: BroadcastStatus
    requested_by: str
    total: int
    sent: int
    failed: int
    created_at: datetime
    finished_at: datetime | None


def _out(b: Broadcast) -> BroadcastOut:
    return BroadcastOut(
        id=b.id,
        kind=b.kind,
        status=b.status,
        requested_by=b.requested_by,
        total=b.total,
        sent=b.sent,
        failed=b.failed,
        created_at=utc_to_local(b.created_at),
        finished_at=utc_to_local(b.finished_at) if b.finished_at else None,
    )


@router.get("/broadcasts", response_model=list[BroadcastOut])
def list_broadcasts(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, VIEW_ROLES)
    items = db.scalars(
        select(Broadcast)
        .where(Broadcast.event_id == event.id)
        .order_by(Broadcast.id.desc())
        .limit(10)
        .execution_options(populate_existing=True)
    )
    return [_out(b) for b in items]


@router.get("/broadcasts/recipients")
def count_recipients(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, VIEW_ROLES)
    return {"recipients": len(service.recipients(db, event))}


@router.post("/broadcasts", response_model=BroadcastOut, status_code=202)
def send_broadcast(
    slug: str,
    payload: BroadcastIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    broadcast = service.start(db, event, payload.kind, user.name)
    background.add_task(service.run, broadcast.id, sessionmaker(bind=db.get_bind()))
    return _out(broadcast)


@router.get("/waitlist", response_model=list[WaitlistRow])
def list_waitlist(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, VIEW_ROLES)
    waitlist.expire_holds(db, event)
    return waitlist.rows(db, event)


@router.post("/waitlist/notify", response_model=NotifyOut)
def notify_waitlist(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    notified, free = waitlist.notify_next(db, event)
    return NotifyOut(notified=notified, free_seats=free)
