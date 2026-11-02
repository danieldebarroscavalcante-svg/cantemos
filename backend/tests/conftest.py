from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.models import Base
from app.db.session import get_db
from app.main import app
from app.modules.auth.models import User
from app.modules.organizations.models import Organization, OrganizationMember, Role

PASSWORD = "senha-forte-123"


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_member(db: Session, org: Organization, email: str, role: Role) -> User:
    user = User(email=email, name=email.split("@")[0], password_hash=hash_password(PASSWORD))
    db.add(user)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=role))
    db.commit()
    return user


@pytest.fixture
def org(db: Session) -> Organization:
    organization = Organization(name="Igreja", slug="igreja")
    db.add(organization)
    db.commit()
    return organization


@pytest.fixture
def admin(db: Session, org: Organization) -> User:
    return make_member(db, org, "admin@igreja.org", Role.OWNER)


def auth_headers(client: TestClient, email: str = "admin@igreja.org") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
