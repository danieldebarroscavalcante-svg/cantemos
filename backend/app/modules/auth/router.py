from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, MembershipOut, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "eventmer_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 24 * 3600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=get_settings().access_token_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    _set_refresh_cookie(response, service.issue_refresh_token(db, user))
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    rotated = service.rotate_refresh_token(db, refresh_token) if refresh_token else None
    if rotated is None:
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada. Entre novamente.")
    user, new_token = rotated
    _set_refresh_cookie(response, new_token)
    return _token_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if refresh_token:
        service.revoke_refresh_token(db, refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserOut(
        id=user.public_id,
        name=user.name,
        email=user.email,
        memberships=[
            MembershipOut(
                organization_id=org.public_id, organization_name=org.name, role=member.role
            )
            for org, member in service.memberships_of(db, user)
        ],
    )
