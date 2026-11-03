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


def test_update_profile_name(client, admin):
    headers = {"Authorization": f"Bearer {login(client).json()['access_token']}"}
    body = client.put("/api/v1/auth/me", json={"name": "  Daniel   Cavalcante "}, headers=headers)
    assert body.status_code == 200
    assert body.json()["name"] == "Daniel Cavalcante"
    assert client.put("/api/v1/auth/me", json={"name": "D"}, headers=headers).status_code == 422


def test_change_password_requires_current_and_logs_out_other_devices(client, admin):
    other_device = login(client).cookies[REFRESH_COOKIE]
    current = login(client)
    headers = {"Authorization": f"Bearer {current.json()['access_token']}"}
    wrong = client.post(
        "/api/v1/auth/password",
        json={"current_password": "errada", "new_password": "nova-senha-123"},
        headers=headers,
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "nova-senha-123"},
        headers=headers,
    )
    assert changed.status_code == 204
    assert REFRESH_COOKIE in changed.cookies  # este aparelho continua logado

    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, other_device, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401  # outro aparelho saiu
    assert login(client).status_code == 401  # senha antiga não vale mais
    assert login(client, password="nova-senha-123").status_code == 200


def test_new_password_must_have_8_chars(client, admin):
    headers = {"Authorization": f"Bearer {login(client).json()['access_token']}"}
    short = client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "curta"},
        headers=headers,
    )
    assert short.status_code == 422
