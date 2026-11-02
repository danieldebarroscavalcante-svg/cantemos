import pytest
from sqlalchemy.orm import sessionmaker

import app.cli as cli_module
from app.core.config import get_settings
from app.core.security import verify_password
from app.modules.auth.models import User
from app.modules.events.models import Event
from app.modules.organizations.models import Role
from tests.conftest import PASSWORD, make_member


@pytest.fixture
def bootstrap_env(db, monkeypatch):
    monkeypatch.setattr(cli_module, "SessionLocal", sessionmaker(bind=db.get_bind()))
    settings = get_settings()
    monkeypatch.setattr(settings, "bootstrap_admin_email", "Daniel@Igreja.org")
    monkeypatch.setattr(settings, "bootstrap_admin_name", "Daniel")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "senha-inicial-123")


def test_bootstrap_creates_admin_and_event_once(db, bootstrap_env):
    cli_module.bootstrap()
    cli_module.bootstrap()  # segunda execução (novo deploy) não duplica nada

    users = db.query(User).all()
    assert [u.email for u in users] == ["daniel@igreja.org"]
    assert db.query(Event).count() == 1


def test_bootstrap_never_overwrites_existing_password(db, org, bootstrap_env):
    make_member(db, org, "daniel@igreja.org", Role.OWNER)
    cli_module.bootstrap()
    user = db.query(User).filter_by(email="daniel@igreja.org").one()
    assert verify_password(PASSWORD, user.password_hash)
