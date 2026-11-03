"""Equipe e níveis de acesso por evento.

Nível efetivo de alguém num evento = o maior entre o papel na igreja (organização) e o papel
na equipe do evento. Responsáveis/administradores da igreja valem para todos os eventos."""

import logging

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_invite_token
from app.modules.auth.models import User
from app.modules.events.models import Event
from app.modules.notifications.email import EmailError, send_email
from app.modules.notifications.layout import EmailParts, InfoRow, render_html, render_text
from app.modules.organizations.models import Organization, OrganizationMember, Role
from app.modules.team.models import EventMember, EventRole

logger = logging.getLogger("eventmer.team")

RANK = {Role.CHECKIN: 1, Role.MANAGER: 2, Role.ADMIN: 3, Role.OWNER: 4}
FROM_EVENT_ROLE = {
    EventRole.ADMIN: Role.ADMIN,
    EventRole.MANAGER: Role.MANAGER,
    EventRole.CHECKIN: Role.CHECKIN,
}
ROLE_LABEL = {
    Role.OWNER: "Responsável",
    Role.ADMIN: "Administrador",
    Role.MANAGER: "Produção",
    Role.CHECKIN: "Recepção",
}
EVENT_ROLE_LABEL = {
    EventRole.ADMIN: "Administrador do evento",
    EventRole.MANAGER: "Produção",
    EventRole.CHECKIN: "Recepção",
}


def effective_role(db: Session, user: User, event: Event) -> Role | None:
    roles: list[Role] = []
    org_role = db.scalar(
        select(OrganizationMember.role).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == event.organization_id,
        )
    )
    if org_role:
        roles.append(org_role)
    event_role = db.scalar(
        select(EventMember.role).where(
            EventMember.user_id == user.id, EventMember.event_id == event.id
        )
    )
    if event_role:
        roles.append(FROM_EVENT_ROLE[event_role])
    return max(roles, key=RANK.__getitem__) if roles else None


def permissions(role: Role | None) -> dict[str, bool]:
    rank = RANK.get(role, 0) if role else 0
    return {
        "edit_event": rank >= RANK[Role.ADMIN],  # configurações, identidade, mensagens
        "manage_team": rank >= RANK[Role.ADMIN],
        "send_messages": rank >= RANK[Role.ADMIN],  # lembretes, lista de espera, teste geral
        "view_reports": rank >= RANK[Role.MANAGER],  # números, inscritos, planilha, lista
        "checkin": rank >= RANK[Role.CHECKIN],
        "undo_any_checkin": rank >= RANK[Role.MANAGER],
    }


def events_for(db: Session, user: User) -> list[tuple[Event, Role]]:
    """Eventos que a pessoa enxerga no painel, com o nível efetivo em cada um."""
    org_ids = list(
        db.scalars(
            select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id)
        )
    )
    event_ids = list(db.scalars(select(EventMember.event_id).where(EventMember.user_id == user.id)))
    conditions = []
    if org_ids:
        conditions.append(Event.organization_id.in_(org_ids))
    if event_ids:
        conditions.append(Event.id.in_(event_ids))
    if not conditions:
        return []
    result = []
    for event in db.scalars(
        select(Event).where(or_(*conditions)).order_by(Event.created_at.desc())
    ):
        role = effective_role(db, user, event)
        if role:
            result.append((event, role))
    return result


# ---------------------------------------------------------------- e-mails


def _invite_email(event: Event, user: User, role: EventRole, invited_by: User, pending: bool):
    base = get_settings().frontend_url.rstrip("/")
    org = None
    if pending:
        link = f"{base}/convite/{create_invite_token(user.id, user.password_hash)}"
        body = (
            f"Olá, {user.name.split()[0]}!\n\n{invited_by.name} adicionou você à equipe do "
            f"{event.title}. Para acessar o painel, crie sua senha pelo botão abaixo — o link "
            "vale por 7 dias."
        )
        button = "Criar minha senha"
    else:
        link = f"{base}/login"
        body = (
            f"Olá, {user.name.split()[0]}!\n\n{invited_by.name} adicionou você à equipe do "
            f"{event.title}. Entre no painel com o seu e-mail e senha de sempre."
        )
        button = "Entrar no painel"
    parts = EmailParts(
        heading="Você foi adicionado à equipe",
        body=body,
        info_title=event.title,
        info_rows=[InfoRow("Acesso", user.email)],
        highlight_label="Seu nível",
        highlight_lines=[EVENT_ROLE_LABEL[role]],
        button_label=button,
        button_url=link,
        footer="Você recebe este e-mail porque foi adicionado à equipe de um evento no EVENTMER."
        + (f" Realização: {org}." if org else ""),
        brand_text=event.title.upper(),
    )
    from app.modules.notifications.email import OutgoingEmail

    return OutgoingEmail(
        to=user.email,
        subject=f"Equipe do {event.title}: seu acesso ao painel",
        html=render_html(parts),
        text=render_text(parts),
    )


def send_invite(event: Event, user: User, role: EventRole, invited_by: User) -> bool:
    try:
        send_email(_invite_email(event, user, role, invited_by, pending=user.password_hash is None))
        return True
    except EmailError:
        logger.exception("Convite da equipe não enviado para %s", user.email)
        return False


def organization_of(db: Session, event: Event) -> Organization:
    return db.get(Organization, event.organization_id)


def forbid(message: str = "Sem permissão para esta ação.") -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, message)
