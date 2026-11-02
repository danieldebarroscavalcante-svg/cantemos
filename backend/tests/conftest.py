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


@pytest.fixture
def admin(db: Session) -> User:
    org = Organization(name="Igreja", slug="igreja")
    user = User(email="admin@igreja.org", name="Admin", password_hash=hash_password(PASSWORD))
    db.add_all([org, user])
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=Role.OWNER))
    db.commit()
    return user
