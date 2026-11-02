"""Comandos administrativos.

python -m app.cli bootstrap            # roda sozinho a cada deploy (ver Dockerfile)
python -m app.cli create-admin --email ... --name ...
python -m app.cli seed-cantemos
python -m app.cli send-test-email --to ...
"""

from datetime import datetime

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.timezone import local_to_utc
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event, EventSession, EventStatus
from app.modules.events.schemas import EventSettingsIn
from app.modules.events.service import update_settings
from app.modules.notifications.email import send_email, test_message
from app.modules.organizations.models import Organization, OrganizationMember, Role

cli = typer.Typer(help="Comandos administrativos do EVENTMER", no_args_is_help=True)

ORG_SLUG = "igreja"
CANTEMOS_SLUG = "cantemos-2026"


def _get_or_create_org(db: Session, name: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
    if org is None:
        org = Organization(name=name, slug=ORG_SLUG)
        db.add(org)
        db.flush()
    return org


def upsert_member(
    db: Session,
    org: Organization,
    email: str,
    name: str,
    role: Role,
    password: str,
    *,
    overwrite_password: bool = True,
) -> bool:
    """Cria ou atualiza um membro da equipe. Retorna True se o usuário foi criado."""
    email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == email))
    created = user is None
    if user is None:
        user = User(email=email, name=name, password_hash=hash_password(password))
        db.add(user)
    elif overwrite_password:
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
    elif overwrite_password:
        member.role = role
    db.commit()
    return created


def seed_cantemos_event(
    db: Session,
    org: Organization,
    *,
    starts_at: str = "2026-11-19T18:30",
    doors_open_at: str = "2026-11-19T18:00",
    capacity: int = 120,
    overbooking_percent: int = 20,
    priority_quota: int = 10,
    max_per_order: int = 5,
) -> str:
    if db.scalar(select(Event).where(Event.slug == CANTEMOS_SLUG)):
        return f"Evento '{CANTEMOS_SLUG}' já existe — ajuste as configurações pelo painel."
    event = Event(
        organization_id=org.id,
        slug=CANTEMOS_SLUG,
        title="CANTEMOS 2026",
        subtitle="Uma história contada em música",
        description="Cantata de final de ano. Entrada gratuita mediante inscrição.",
        status=EventStatus.DRAFT,
        max_tickets_per_order=max_per_order,
    )
    db.add(event)
    db.flush()
    db.add(
        EventSession(
            event_id=event.id,
            name="Quinta, 19/11",
            starts_at=local_to_utc(datetime.fromisoformat(starts_at)),
            capacity=capacity,
        )
    )
    db.flush()
    result = update_settings(
        db,
        event,
        EventSettingsIn(
            starts_at=datetime.fromisoformat(starts_at),
            doors_open_at=datetime.fromisoformat(doors_open_at),
            capacity=capacity,
            overbooking_percent=overbooking_percent,
            max_tickets_per_order=max_per_order,
            priority_quota=priority_quota,
        ),
    )
    return (
        f"✔ CANTEMOS 2026 criado em rascunho: {capacity} lugares + {overbooking_percent}% de "
        f"margem = {result.registration_limit} inscrições "
        f"({result.general.quantity} gerais + {result.priority.quantity} prioridade)."
    )


@cli.command("bootstrap")
def bootstrap() -> None:
    """Prepara um banco novo: organização, primeiro administrador e evento CANTEMOS.

    Idempotente: roda a cada deploy e nunca sobrescreve senha ou configurações existentes.
    O administrador vem de BOOTSTRAP_ADMIN_EMAIL / _NAME / _PASSWORD.
    """
    settings = get_settings()
    with SessionLocal() as db:
        org = _get_or_create_org(db, settings.organization_name)
        email, password = settings.bootstrap_admin_email, settings.bootstrap_admin_password
        if email and password:
            if len(password) < 8:
                typer.echo(
                    "⚠ BOOTSTRAP_ADMIN_PASSWORD precisa ter 8+ caracteres; admin não criado."
                )
            elif upsert_member(
                db,
                org,
                email,
                settings.bootstrap_admin_name,
                Role.OWNER,
                password,
                overwrite_password=False,
            ):
                typer.echo(f"✔ Administrador {email} criado.")
            else:
                typer.echo(f"Administrador {email} já existe — senha mantida.")
        typer.echo(seed_cantemos_event(db, org))


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
        upsert_member(db, _get_or_create_org(db, org_name), email, name, role, password)
    typer.echo(f"✔ {normalize_email(email)} agora é {role.value} em '{org_name}'.")


@cli.command("seed-cantemos")
def seed_cantemos(
    org_name: str = typer.Option("Igreja", help="Nome da organização"),
    starts_at: str = typer.Option("2026-11-19T18:30", help="Início (horário de Brasília)"),
    doors_open_at: str = typer.Option("2026-11-19T18:00", help="Abertura das portas"),
    capacity: int = typer.Option(120, help="Lugares físicos"),
    overbooking_percent: int = typer.Option(20, help="Margem de inscrições acima da lotação (%)"),
    priority_quota: int = typer.Option(10, help="Lugares para PCD / idosos / gestantes"),
    max_per_order: int = typer.Option(5, help="Máximo de ingressos por inscrição"),
) -> None:
    """Cria o evento CANTEMOS 2026 (idempotente). Tudo é ajustável depois pelo painel."""
    with SessionLocal() as db:
        message = seed_cantemos_event(
            db,
            _get_or_create_org(db, org_name),
            starts_at=starts_at,
            doors_open_at=doors_open_at,
            capacity=capacity,
            overbooking_percent=overbooking_percent,
            priority_quota=priority_quota,
            max_per_order=max_per_order,
        )
    typer.echo(message)


@cli.command("send-test-email")
def send_test_email(to: str = typer.Option(..., help="Destinatário do teste")) -> None:
    """Envia um e-mail de teste com o backend configurado em EMAIL_BACKEND."""
    send_email(test_message(to))
    typer.echo(f"✔ E-mail enviado para {to} via {get_settings().email_backend}.")


if __name__ == "__main__":
    cli()
