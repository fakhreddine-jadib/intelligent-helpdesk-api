"""Tests for registration, login and access control."""


def test_register_returns_created(client):
    res = client.post("/api/auth/register", json={
        "email": "new@test.local", "password": "password123",
        "full_name": "New User", "role": "client",
    })
    assert res.status_code == 201
    assert "password_hash" not in res.get_json()


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@test.local", "password": "password123",
               "full_name": "Dup", "role": "client"}
    client.post("/api/auth/register", json=payload)
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    assert res.get_json()["error"] == "email_taken"


def test_short_password_rejected(client):
    res = client.post("/api/auth/register", json={
        "email": "weak@test.local", "password": "short",
        "full_name": "Weak", "role": "client",
    })
    assert res.status_code == 400
    assert res.get_json()["error"] == "weak_password"


def test_invalid_email_rejected(client):
    res = client.post("/api/auth/register", json={
        "email": "not-an-email", "password": "password123",
        "full_name": "Bad", "role": "client",
    })
    assert res.status_code == 400


def test_login_returns_token(client):
    client.post("/api/auth/register", json={
        "email": "login@test.local", "password": "password123",
        "full_name": "Login", "role": "client",
    })
    res = client.post("/api/auth/login", json={
        "email": "login@test.local", "password": "password123",
    })
    assert res.status_code == 200
    assert res.get_json()["token"]


def test_wrong_password_rejected(client):
    client.post("/api/auth/register", json={
        "email": "pw@test.local", "password": "password123",
        "full_name": "PW", "role": "client",
    })
    res = client.post("/api/auth/login", json={
        "email": "pw@test.local", "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_error_message_identical_for_unknown_and_wrong_password(client):
    """Prevents account enumeration."""
    client.post("/api/auth/register", json={
        "email": "enum@test.local", "password": "password123",
        "full_name": "Enum", "role": "client",
    })
    wrong_pw = client.post("/api/auth/login", json={
        "email": "enum@test.local", "password": "wrongpassword",
    }).get_json()
    unknown = client.post("/api/auth/login", json={
        "email": "ghost@test.local", "password": "password123",
    }).get_json()
    assert wrong_pw["message"] == unknown["message"]


def test_protected_route_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_invalid_token_rejected(client):
    res = client.get("/api/auth/me",
                     headers={"Authorization": "Bearer not.a.real.token"})
    assert res.status_code == 401