from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, hash_token, new_opaque_token, verify_password
from app.db.base import utcnow
from app.modules.auth.models import RefreshToken, User
from app.modules.organizations.models import Organization, OrganizationMember

# Hash fixo usado quando o e-mail não existe, para o tempo de resposta não revelar contas.
_DUMMY_HASH = hash_password("eventmer-dummy-password")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def issue_refresh_token(db: Session, user: User) -> str:
    token = new_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days),
        )
    )
    db.commit()
    return token


def rotate_refresh_token(db: Session, token: str) -> tuple[User, str] | None:
    """Invalida o refresh token recebido e emite um novo (rotação)."""
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if stored is None or stored.revoked_at is not None or stored.expires_at <= utcnow():
        return None
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        return None
    stored.revoked_at = utcnow()
    db.commit()
    return user, issue_refresh_token(db, user)


def revoke_refresh_token(db: Session, token: str) -> None:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        db.commit()


def memberships_of(db: Session, user: User) -> list[tuple[Organization, OrganizationMember]]:
    rows = db.execute(
        select(Organization, OrganizationMember)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
    )
    return [(org, member) for org, member in rows]


def revoke_all_refresh_tokens(db: Session, user: User) -> None:
    """Encerra as sessões de todos os aparelhos (usado ao trocar a senha)."""
    for token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ):
        token.revoked_at = utcnow()
    db.commit()
