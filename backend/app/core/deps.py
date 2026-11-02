from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.organizations.models import OrganizationMember, Role

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_org_role(*roles: Role) -> Callable[..., OrganizationMember]:
    """Garante que o usuário tem um dos papéis na organização informada."""

    def dependency(
        organization_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OrganizationMember:
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id,
            )
        )
        if member is None or member.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta ação.")
        return member

    return dependency
