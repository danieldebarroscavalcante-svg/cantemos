"""Comandos administrativos.

python -m app.cli create-admin --email ... --name ...
python -m app.cli seed-cantemos
python -m app.cli send-test-email --to ...
"""

from datetime import datetime

import typer
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.timezone import local_to_utc
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.auth.service import normalize_email
from app.modules.events.models import Event, EventSession, EventStatus
from app.modules.events.schemas import EventSettingsIn
from app.modules.events.service import update_settings
from app.modules.notifications.email import OutgoingEmail, send_email
from app.modules.organizations.models import Organization, OrganizationMember, Role

cli = typer.Typer(help="Comandos administrativos do EVENTMER", no_args_is_help=True)

ORG_SLUG = "igreja"


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
    starts_at: str = typer.Option("2026-11-19T18:30", help="Início (horário de Brasília)"),
    doors_open_at: str = typer.Option("2026-11-19T18:00", help="Abertura das portas"),
    capacity: int = typer.Option(120, help="Lugares físicos"),
    overbooking_percent: int = typer.Option(20, help="Margem de inscrições acima da lotação (%)"),
    priority_quota: int = typer.Option(10, help="Lugares para PCD / idosos / gestantes"),
    max_per_order: int = typer.Option(5, help="Máximo de ingressos por inscrição"),
) -> None:
    """Cria o evento CANTEMOS 2026 (idempotente). Tudo é ajustável depois pelo painel."""
    slug = "cantemos-2026"
    with SessionLocal() as db:
        if db.scalar(select(Event).where(Event.slug == slug)):
            typer.echo(f"Evento '{slug}' já existe — ajuste as configurações pelo painel.")
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
    typer.echo(
        f"✔ CANTEMOS 2026 criado em rascunho: {capacity} lugares + {overbooking_percent}% de "
        f"margem = {result.registration_limit} inscrições "
        f"({result.general.quantity} gerais + {result.priority.quantity} prioridade)."
    )


@cli.command("send-test-email")
def send_test_email(to: str = typer.Option(..., help="Destinatário do teste")) -> None:
    """Envia um e-mail de teste com o backend configurado em EMAIL_BACKEND."""
    send_email(
        OutgoingEmail(
            to=to,
            subject="Teste de envio · EVENTMER",
            text="Se você recebeu esta mensagem, o envio de e-mails do EVENTMER está funcionando.",
            html="<p>Se você recebeu esta mensagem, o envio de e-mails do "
            "<strong>EVENTMER</strong> está funcionando. ✅</p>",
        )
    )
    typer.echo(f"✔ E-mail enviado para {to} via {get_settings().email_backend}.")


if __name__ == "__main__":
    cli()
