from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.notifications.email import EmailError, send_email, test_message
from app.modules.organizations.models import OrganizationMember, Role

router = APIRouter(prefix="/org", tags=["organizador · e-mail"])


class TestEmailOut(BaseModel):
    sent_to: str
    backend: str


@router.post("/test-email", response_model=TestEmailOut)
def send_test_email(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Envia um e-mail de teste para o próprio usuário (responsável/administrador)."""
    is_admin = db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.role.in_((Role.OWNER, Role.ADMIN)),
        )
    )
    if not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta ação.")
    try:
        send_email(test_message(user.email))
    except EmailError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return TestEmailOut(sent_to=user.email, backend=get_settings().email_backend)
