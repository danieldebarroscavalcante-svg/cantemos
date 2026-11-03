from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.assets import service
from app.modules.assets.models import Asset
from app.modules.auth.models import User
from app.modules.events.router import EDIT_ROLES, _event_for
from app.modules.organizations.models import Organization, OrganizationMember, Role

public_router = APIRouter(prefix="/public", tags=["público"])
org_router = APIRouter(prefix="/org", tags=["organizador · identidade"])


# ------------------------------------------------------------------ entrega


@public_router.get("/assets/{public_id}")
def get_asset(public_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(
        select(Asset).where(Asset.public_id == public_id).options(undefer(Asset.data))
    )
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagem não encontrada.")
    headers = {
        # O endereço muda a cada novo envio, então a imagem pode ficar em cache "para sempre".
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    }
    if asset.content_type == "image/svg+xml":
        # SVG pode conter script: se alguém abrir o arquivo direto, nada executa.
        headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        )
    return Response(content=asset.data, media_type=asset.content_type, headers=headers)


@public_router.get("/organization")
def public_organization(db: Session = Depends(get_db)):
    """Nome e logo da organização (para rodapé, Privacidade e Termos)."""
    row = db.execute(
        select(Organization, Asset.public_id)
        .outerjoin(Asset, Asset.id == Organization.logo_asset_id)
        .order_by(Organization.id)
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organização não encontrada.")
    org, logo = row
    return {"name": org.name, "logo_url": service.url(logo)}


# ------------------------------------------------------------------ logo do evento


class LogoOut(BaseModel):
    logo_url: str | None


@org_router.post("/events/{slug}/logo", response_model=LogoOut)
async def upload_event_logo(
    slug: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    data, content_type = await service.read_upload(file)
    old = event.logo_asset_id
    asset = service.save(db, event.organization_id, data, content_type, file.filename)
    event.logo_asset_id = asset.id
    if old:
        db.delete(db.get(Asset, old))
    db.commit()
    return LogoOut(logo_url=service.url(asset.public_id))


@org_router.delete("/events/{slug}/logo", response_model=LogoOut)
def delete_event_logo(
    slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    event = _event_for(db, user, slug, EDIT_ROLES)
    if event.logo_asset_id:
        asset = db.get(Asset, event.logo_asset_id)
        event.logo_asset_id = None
        db.flush()
        db.delete(asset)
        db.commit()
    return LogoOut(logo_url=None)


# ------------------------------------------------------------------ igreja / organização


class OrganizationOut(BaseModel):
    name: str
    logo_url: str | None
    can_edit: bool


class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)


def _my_org(db: Session, user: User, edit: bool = False) -> tuple[Organization, bool]:
    row = db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(Organization.id)
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organização não encontrada.")
    org, role = row
    can_edit = role in (Role.OWNER, Role.ADMIN)
    if edit and not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta ação.")
    return org, can_edit


def _org_out(db: Session, org: Organization, can_edit: bool) -> OrganizationOut:
    logo = db.scalar(select(Asset.public_id).where(Asset.id == org.logo_asset_id))
    return OrganizationOut(name=org.name, logo_url=service.url(logo), can_edit=can_edit)


@org_router.get("/organization", response_model=OrganizationOut)
def get_organization(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org, can_edit = _my_org(db, user)
    return _org_out(db, org, can_edit)


@org_router.put("/organization", response_model=OrganizationOut)
def update_organization(
    payload: OrganizationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    org, _ = _my_org(db, user, edit=True)
    org.name = " ".join(payload.name.split())
    db.commit()
    return _org_out(db, org, True)


@org_router.post("/organization/logo", response_model=OrganizationOut)
async def upload_organization_logo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org, _ = _my_org(db, user, edit=True)
    data, content_type = await service.read_upload(file)
    old = org.logo_asset_id
    asset = service.save(db, org.id, data, content_type, file.filename)
    org.logo_asset_id = asset.id
    if old:
        db.delete(db.get(Asset, old))
    db.commit()
    return _org_out(db, org, True)


@org_router.delete("/organization/logo", response_model=OrganizationOut)
def delete_organization_logo(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org, _ = _my_org(db, user, edit=True)
    if org.logo_asset_id:
        asset = db.get(Asset, org.logo_asset_id)
        org.logo_asset_id = None
        db.flush()
        db.delete(asset)
        db.commit()
    return _org_out(db, org, True)
