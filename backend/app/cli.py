"""Comandos administrativos.

python -m app.cli create-admin --email ... --name ...
python -m app.cli seed-cantemos
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import typer
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event, EventSession, EventStatus
from app.modules.organizations.models import Organization, OrganizationMember, Role
from app.modules.tickets.models import TicketType

cli = typer.Typer(help="Comandos administrativos do EVENTMER", no_args_is_help=True)

ORG_SLUG = "igreja"


def _local_to_utc(value: str) -> datetime:
    """Converte 'AAAA-MM-DDTHH:MM' no fuso do evento para UTC sem tzinfo (padrão do banco)."""
    local = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(get_settings().timezone))
    return local.astimezone(UTC).replace(tzinfo=None)


def _get_or_create_org(db, name: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
    if org is None:
        org = Organization(name=name, slug=ORG_SLUG)
        db.add(org)
        db.flush()
    return org


@cli.command("create-admin")
def create_admin(
    email: str = typer.Option(..., help="E-mail de login"),
    name: str = typer.Option(..., help="Nome completo"),
    role: Role = typer.Option(Role.ADMIN, help="owner | admin | manager | checkin"),
    org_name: str = typer.Option("Igreja", help="Nome da organização (criada se não existir)"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=True, help="Senha (mín. 8)"
    ),
) -> None:
    """Cria (ou atualiza) um membro da equipe com senha e papel na organização."""
    if len(password) < 8:
        raise typer.BadParameter("A senha precisa ter pelo menos 8 caracteres.")
    with SessionLocal() as db:
        org = _get_or_create_org(db, org_name)
        email = normalize_email(email)
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, name=name)
            db.add(user)
        user.name = name
        user.password_hash = hash_password(password)
        db.flush()
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
            )
        )
        if member is None:
            db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=role))
        else:
            member.role = role
        db.commit()
    typer.echo(f"✔ {email} agora é {role.value} em '{org_name}'.")


@cli.command("seed-cantemos")
def seed_cantemos(
    org_name: str = typer.Option("Igreja", help="Nome da organização"),
    starts_at: str = typer.Option("2026-11-19T19:30", help="Início (horário de Brasília)"),
    doors_open_at: str = typer.Option("2026-11-19T19:00", help="Abertura das portas"),
    capacity: int = typer.Option(120, help="Lotação total"),
    priority_quota: int = typer.Option(10, help="Lugares para PCD / idosos / gestantes"),
    max_per_order: int = typer.Option(5, help="Máximo de ingressos por inscrição"),
) -> None:
    """Cria o evento CANTEMOS 2026 (idempotente: não duplica se já existir)."""
    slug = "cantemos-2026"
    with SessionLocal() as db:
        if db.scalar(select(Event).where(Event.slug == slug)):
            typer.echo(f"Evento '{slug}' já existe — nada a fazer.")
            return
        org = _get_or_create_org(db, org_name)
        event = Event(
            organization_id=org.id,
            slug=slug,
            title="CANTEMOS 2026",
            subtitle="Uma história contada em música",
            description="Cantata de final de ano. Entrada gratuita mediante inscrição.",
            status=EventStatus.DRAFT,
            max_tickets_per_order=max_per_order,
        )
        db.add(event)
        db.flush()
        session = EventSession(
            event_id=event.id,
            name="Quinta, 19/11",
            starts_at=_local_to_utc(starts_at),
            doors_open_at=_local_to_utc(doors_open_at),
            capacity=capacity,
        )
        db.add(session)
        db.flush()
        db.add_all(
            [
                TicketType(
                    session_id=session.id,
                    name="Entrada gratuita",
                    quantity=capacity - priority_quota,
                    sort_order=1,
                ),
                TicketType(
                    session_id=session.id,
                    name="Prioridade (PCD, idosos, gestantes)",
                    description="Lugares reservados com acesso facilitado.",
                    quantity=priority_quota,
                    is_priority=True,
                    sort_order=2,
                ),
            ]
        )
        db.commit()
    typer.echo(
        f"✔ CANTEMOS 2026 criado em rascunho: {capacity} lugares "
        f"({capacity - priority_quota} gerais + {priority_quota} prioridade)."
    )


if __name__ == "__main__":
    cli()
