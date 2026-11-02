from app.modules.organizations.models import Role
from tests.conftest import auth_headers, make_member


def test_admin_can_send_test_email_to_self(client, admin):
    response = client.post("/api/v1/org/test-email", headers=auth_headers(client))
    assert response.status_code == 200
    assert response.json() == {"sent_to": "admin@igreja.org", "backend": "console"}


def test_reception_cannot_send_test_email(db, client, org):
    make_member(db, org, "recepcao@igreja.org", Role.CHECKIN)
    headers = auth_headers(client, "recepcao@igreja.org")
    assert client.post("/api/v1/org/test-email", headers=headers).status_code == 403
