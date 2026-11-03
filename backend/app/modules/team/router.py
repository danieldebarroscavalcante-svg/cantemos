from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.ratelimit import RateLimiter, client_ip
from app.core.security import (
    create_access_token,
    hash_password,
    invite_matches,
    read_invite_token,
)
from app.db.session import get_db
from app.modules.auth import service as auth_service
from app.modules.auth.models import User
from app.modules.auth.router import _set_refresh_cookie
from app.modules.auth.schemas import TokenResponse
from app.modules.events.models import Event
from app.modules.events.router import EDIT_ROLES, _event_for
from app.modules.organizations.models import OrganizationMember, Role
from app.modules.team import service
from app.modules.team.models import EventMember, EventRole

router = APIRouter(prefix="/org/events/{slug}", tags=["organizador · equipe"])
invite_router = APIRouter(prefix="/auth/invite", tags=["auth"])
invite_limiter = RateLimiter(max_calls=20, per_seconds=600)


class AccessOut(BaseModel):
    role: Role
    label: str
    permissions: dict[str, bool]


class MemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str  # owner/admin (igreja) ou admin/manager/checkin (evento)
    label: str
    source: str  # "igreja" | "evento"
    pending: bool  # ainda não criou a senha
    editable: bool
    is_me: bool


class TeamOut(BaseModel):
    members: list[MemberOut]
    can_manage: bool


class MemberIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: EventRole


class RoleIn(BaseModel):
    role: EventRole


def _view_access(db: Session, user: User, slug: str) -> tuple[Event, Role]:
    event = _event_for(db, user, slug, (Role.OWNER, Role.ADMIN, Role.MANAGER, Role.CHECKIN))
    return event, service.effective_role(db, user, event)


@router.get("/access", response_model=AccessOut)
def my_access(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, role = _view_access(db, user, slug)
    return AccessOut(
        role=role, label=service.ROLE_LABEL[role], permissions=service.permissions(role)
    )


def _team(db: Session, event: Event, user: User) -> TeamOut:
    can_manage = service.permissions(service.effective_role(db, user, event))["manage_team"]
    members: list[MemberOut] = []
    org_rows = db.execute(
        select(User, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(
            OrganizationMember.organization_id == event.organization_id,
            OrganizationMember.role.in_((Role.OWNER, Role.ADMIN)),
        )
        .order_by(User.name)
    ).all()
    seen = set()
    for u, role in org_rows:
        seen.add(u.id)
        members.append(
            MemberOut(
                id=u.public_id,
                name=u.name,
                email=u.email,
                role=role.value,
                label=f"{service.ROLE_LABEL[role]} (igreja)",
                source="igreja",
                pending=u.password_hash is None,
                editable=False,
                is_me=u.id == user.id,
            )  # fmt: skip
        )
    rows = db.execute(
        select(User, EventMember.role)
        .join(EventMember, EventMember.user_id == User.id)
        .where(EventMember.event_id == event.id)
        .order_by(EventMember.role, User.name)
    ).all()
    for u, role in rows:
        if u.id in seen:
            continue
        members.append(
            MemberOut(
                id=u.public_id,
                name=u.name,
                email=u.email,
                role=role.value,
                label=service.EVENT_ROLE_LABEL[role],
                source="evento",
                pending=u.password_hash is None,
                editable=can_manage and u.id != user.id,
                is_me=u.id == user.id,
            )  # fmt: skip
        )
    return TeamOut(members=members, can_manage=can_manage)


@router.get("/team", response_model=TeamOut)
def get_team(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = _event_for(db, user, slug, (Role.OWNER, Role.ADMIN, Role.MANAGER))
    return _team(db, event, user)


def _member(db: Session, event: Event, member_id: str) -> tuple[User, EventMember]:
    row = db.execute(
        select(User, EventMember)
        .join(EventMember, EventMember.user_id == User.id)
        .where(User.public_id == member_id, EventMember.event_id == event.id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pessoa não encontrada na equipe.")
    return row[0], row[1]


@router.post("/team", response_model=TeamOut, status_code=201)
def add_member(
    slug: str,
    payload: MemberIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    email = auth_service.normalize_email(str(payload.email))
    member = db.scalar(select(User).where(User.email == email))
    if member is None:
        member = User(email=email, name=" ".join(payload.name.split()))  # conta sem senha
        db.add(member)
        db.flush()
    elif member.id == user.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Você já faz parte da equipe.")
    org_role = db.scalar(
        select(OrganizationMember.role).where(
            OrganizationMember.user_id == member.id,
            OrganizationMember.organization_id == event.organization_id,
        )
    )
    if org_role in (Role.OWNER, Role.ADMIN):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta pessoa já é responsável pela igreja e tem acesso a todos os eventos.",
        )
    existing = db.scalar(
        select(EventMember).where(
            EventMember.event_id == event.id, EventMember.user_id == member.id
        )
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta pessoa já está na equipe. Altere o nível na lista."
        )
    db.add(
        EventMember(
            event_id=event.id, user_id=member.id, role=payload.role, invited_by_user_id=user.id
        )
    )
    db.commit()
    service.send_invite(event, member, payload.role, user)
    return _team(db, event, user)


@router.put("/team/{member_id}", response_model=TeamOut)
def change_role(
    slug: str,
    member_id: str,
    payload: RoleIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    member, link = _member(db, event, member_id)
    if member.id == user.id:
        raise service.forbid("Você não pode alterar o próprio nível.")
    link.role = payload.role
    db.commit()
    return _team(db, event, user)


@router.delete("/team/{member_id}", response_model=TeamOut)
def remove_member(
    slug: str, member_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    member, link = _member(db, event, member_id)
    if member.id == user.id:
        raise service.forbid("Você não pode remover a si mesmo da equipe.")
    db.delete(link)
    db.commit()
    return _team(db, event, user)


@router.post("/team/{member_id}/resend")
def resend_invite(
    slug: str, member_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    member, link = _member(db, event, member_id)
    sent = service.send_invite(event, member, link.role, user)
    if not sent:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Não foi possível enviar o e-mail.")
    return {"sent_to": member.email}


# ------------------------------------------------------------------ convite (criar senha)


class InviteInfo(BaseModel):
    name: str
    email: str


class InviteAccept(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)


def _invited_user(db: Session, token: str) -> User:
    data = read_invite_token(token)
    user = db.get(User, data[0]) if data else None
    if user is None or not user.is_active or not invite_matches(data[1], user.password_hash):
        raise HTTPException(
            status.HTTP_410_GONE,
            "Este convite expirou ou já foi usado. Peça um novo convite ou entre com sua senha.",
        )
    return user


@invite_router.get("/{token}", response_model=InviteInfo)
def invite_info(token: str, request: Request, db: Session = Depends(get_db)):
    invite_limiter.hit(client_ip(request))
    user = _invited_user(db, token)
    return InviteInfo(name=user.name, email=user.email)


@invite_router.post("/{token}", response_model=TokenResponse)
def accept_invite(
    token: str,
    payload: InviteAccept,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    from app.core.config import get_settings

    invite_limiter.hit(client_ip(request))
    user = _invited_user(db, token)
    user.name = " ".join(payload.name.split())
    user.password_hash = hash_password(payload.password)  # o convite deixa de valer
    db.commit()
    _set_refresh_cookie(response, auth_service.issue_refresh_token(db, user))
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=get_settings().access_token_minutes * 60,
    )
