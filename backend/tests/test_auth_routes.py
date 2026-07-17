"""Auth route tests.

Supabase Auth's HTTP endpoints (GoTrue) aren't reachable in this
environment, so they're mocked at the httpx boundary with responses
matching their documented contract. Everything else — the business row,
the users mirror row, the first-user rule — runs against the real local
Postgres/PostgREST stack.
"""
import os
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient, Response

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.routes import auth as auth_module
from app.config import settings
from app.db import repos
from app.db.client import service_client
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_gotrue(monkeypatch):
    """Mock Supabase Auth: admin user creation + password grant."""
    created_users = {}

    async def fake_admin_create(email, password, business_id):
        if email in created_users:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Email already registered")
        user = {"id": str(uuid.uuid4()), "email": email,
                "app_metadata": {"business_id": business_id}}
        created_users[email] = {"password": password, **user}
        return user

    async def fake_password_grant(email, password):
        u = created_users.get(email)
        if not u or u["password"] != password:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return {"access_token": f"mock-jwt-for-{u['id']}", "token_type": "bearer"}

    monkeypatch.setattr(auth_module, "_admin_create_auth_user", fake_admin_create)
    monkeypatch.setattr(auth_module, "_password_grant", fake_password_grant)
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://mock.supabase.co")
    return created_users


def unique_phone():
    return "+1713555" + str(uuid.uuid4().int)[:4]


@pytest.mark.anyio
async def test_signup_creates_tenant_and_admin(client, mock_gotrue):
    phone = unique_phone()
    email = f"owner-{uuid.uuid4().hex[:6]}@example.com"
    res = await client.post("/api/auth/signup", json={
        "business_name": "Signup Garage",
        "phone_number": phone,
        "business_type": "mechanic",
        "email": email,
        "password": "hunter22",
    })
    assert res.status_code == 201, res.text
    assert res.json()["access_token"].startswith("mock-jwt-for-")

    db = service_client()
    business = await repos.get_business_by_phone(db, phone)
    assert business is not None and business["business_type"] == "mechanic"
    assert await repos.count_users_for_business(db, business["id"]) == 1
    # Mirror row shares the auth user's id and carries the tenant
    user = await repos.get_user_by_id(db, mock_gotrue[email]["id"])
    assert user["business_id"] == business["id"] and user["role"] == "admin"


@pytest.mark.anyio
async def test_signup_rejects_duplicate_phone(client, mock_gotrue):
    phone = unique_phone()
    body = {
        "business_name": "Dup", "phone_number": phone, "business_type": "salon",
        "email": f"a-{uuid.uuid4().hex[:6]}@example.com", "password": "x-longer-pw",
    }
    assert (await client.post("/api/auth/signup", json=body)).status_code == 201
    body["email"] = f"b-{uuid.uuid4().hex[:6]}@example.com"
    assert (await client.post("/api/auth/signup", json=body)).status_code == 400


@pytest.mark.anyio
async def test_register_first_user_only(client, mock_gotrue):
    db = service_client()
    business = await repos.create_business(db, {
        "name": "Preexisting Clinic", "phone_number": unique_phone(),
        "business_type": "clinic",
    })
    first = {"business_id": business["id"],
             "email": f"first-{uuid.uuid4().hex[:6]}@example.com", "password": "pw123456"}
    res = await client.post("/api/auth/register", json=first)
    assert res.status_code == 201, res.text

    second = {**first, "email": f"second-{uuid.uuid4().hex[:6]}@example.com"}
    res2 = await client.post("/api/auth/register", json=second)
    assert res2.status_code == 403  # bootstrap rule: only the first user self-registers


@pytest.mark.anyio
async def test_register_unknown_business_404(client, mock_gotrue):
    res = await client.post("/api/auth/register", json={
        "business_id": str(uuid.uuid4()),
        "email": "x@example.com", "password": "pw123456",
    })
    assert res.status_code == 404


@pytest.mark.anyio
async def test_login_wrong_password_401(client, mock_gotrue):
    phone = unique_phone()
    email = f"login-{uuid.uuid4().hex[:6]}@example.com"
    await client.post("/api/auth/signup", json={
        "business_name": "Login Salon", "phone_number": phone,
        "business_type": "salon", "email": email, "password": "correct-pw",
    })
    ok = await client.post("/api/auth/login", json={"email": email, "password": "correct-pw"})
    assert ok.status_code == 200
    bad = await client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    assert bad.status_code == 401
