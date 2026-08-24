"""Shared pytest fixtures."""

import mongomock
import pytest

from src.api import create_app
from src import db as db_module


@pytest.fixture
def app(monkeypatch):
    """Flask app backed by an in-memory MongoDB substitute."""
    client = mongomock.MongoClient()

    def fake_init_db(app):
        db_module._client = client
        db_module._db = client["test_helpdesk"]
        db_module._db.users.create_index("email", unique=True)
        return db_module._db

    monkeypatch.setattr(db_module, "init_db", fake_init_db)

    app = create_app("development")
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    app.config["RATELIMIT_ENABLED"] = False
    yield app

    db_module._db = None
    db_module._client = None


@pytest.fixture
def client(app):
    return app.test_client()


def _register_and_login(client, email, role):
    client.post("/api/auth/register", json={
        "email": email, "password": "password123",
        "full_name": f"Test {role}", "role": role,
    })
    res = client.post("/api/auth/login", json={
        "email": email, "password": "password123",
    })
    return res.get_json()["token"]


@pytest.fixture
def client_headers(client):
    token = _register_and_login(client, "client@test.local", "client")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers(client):
    token = _register_and_login(client, "agent@test.local", "agent")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    token = _register_and_login(client, "admin@test.local", "admin")
    return {"Authorization": f"Bearer {token}"}