from app.modules.auth.router import REFRESH_COOKIE
from tests.conftest import PASSWORD


def login(client, email="admin@igreja.org", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_returns_access_token_and_refresh_cookie(client, admin):
    response = login(client, email="ADMIN@igreja.org")
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert REFRESH_COOKIE in response.cookies


def test_login_with_wrong_password_is_rejected(client, admin):
    assert login(client, password="errada").status_code == 401


def test_login_with_unknown_email_is_rejected(client, admin):
    assert login(client, email="ninguem@igreja.org").status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_user_and_role(client, admin):
    token = login(client).json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@igreja.org"
    assert body["memberships"][0]["role"] == "owner"


def test_refresh_rotates_token_and_old_one_stops_working(client, admin):
    old = login(client).cookies[REFRESH_COOKIE]

    client.cookies.set(REFRESH_COOKIE, old, path="/api/v1/auth")
    first = client.post("/api/v1/auth/refresh")
    assert first.status_code == 200
    new = first.cookies[REFRESH_COOKIE]
    assert new != old

    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, old, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token(client, admin):
    token = login(client).cookies[REFRESH_COOKIE]
    client.cookies.set(REFRESH_COOKIE, token, path="/api/v1/auth")
    assert client.post("/api/v1/auth/logout").status_code == 204

    client.cookies.set(REFRESH_COOKIE, token, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401
