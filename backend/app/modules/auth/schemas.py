from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.organizations.models import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MembershipOut(BaseModel):
    organization_id: str
    organization_name: str
    role: Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    memberships: list[MembershipOut] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
