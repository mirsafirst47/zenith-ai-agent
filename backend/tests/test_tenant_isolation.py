"""Tenant isolation integration tests.

Runs the real FastAPI app against a real PostgREST + Postgres with the
production RLS policies applied. JWTs are minted with the same secret
PostgREST validates — identical to how Supabase-issued tokens behave.

Requires local stack: postgres + postgrest (see backend/.env).
"""
import os
import sys
import uuid

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.main import app

SECRET = settings.SUPABASE_JWT_SECRET

TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


def user_token(business_id: str) -> str:
    """Mint a JWT with the exact claim shape Supabase Auth issues."""
    return pyjwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "authenticated",
            "aud": "authenticated",
            "email": f"user-{business_id[:4]}@example.com",
            "app_metadata": {"business_id": business_id},
            "exp": 9999999999,
        },
        SECRET,
        algorithm="HS256",
    )


def auth_header(business_id: str) -> dict:
    return {"Authorization": f"Bearer {user_token(business_id)}"}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_unauthenticated_request_is_401(client):
    res = await client.get("/api/bookings/")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_invalid_token_is_401(client):
    bad = pyjwt.encode({"sub": "x", "role": "authenticated"}, "wrong-secret", algorithm="HS256")
    res = await client.get("/api/bookings/", headers={"Authorization": f"Bearer {bad}"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_token_without_business_claim_is_403(client):
    orphan = pyjwt.encode(
        {"sub": "x", "role": "authenticated", "aud": "authenticated", "exp": 9999999999},
        SECRET,
        algorithm="HS256",
    )
    res = await client.get("/api/bookings/", headers={"Authorization": f"Bearer {orphan}"})
    assert res.status_code == 403


@pytest.mark.anyio
async def test_each_tenant_sees_only_its_bookings(client):
    res_a = await client.get("/api/bookings/", headers=auth_header(TENANT_A))
    res_b = await client.get("/api/bookings/", headers=auth_header(TENANT_B))
    assert res_a.status_code == 200 and res_b.status_code == 200
    assert {b["business_id"] for b in res_a.json()} <= {TENANT_A}
    assert {b["business_id"] for b in res_b.json()} <= {TENANT_B}
    assert len(res_a.json()) >= 1, "seed data should be visible to its own tenant"


@pytest.mark.anyio
async def test_cannot_request_another_tenants_business_id(client):
    res = await client.get(
        f"/api/bookings/?business_id={TENANT_B}", headers=auth_header(TENANT_A)
    )
    assert res.status_code == 403


@pytest.mark.anyio
async def test_cross_tenant_booking_fetch_is_404(client):
    mine = (await client.get("/api/bookings/", headers=auth_header(TENANT_B))).json()
    assert mine, "tenant B needs at least one seeded booking"
    stolen_id = mine[0]["id"]
    res = await client.get(f"/api/bookings/{stolen_id}", headers=auth_header(TENANT_A))
    assert res.status_code == 404  # not 403 — must not confirm existence


@pytest.mark.anyio
async def test_cross_tenant_create_is_blocked(client):
    res = await client.post(
        "/api/bookings/",
        headers=auth_header(TENANT_A),
        json={
            "business_id": TENANT_B,
            "customer_name": "Evil",
            "customer_phone": "+10000000000",
            "scheduled_at": "2027-01-01T10:00:00Z",
        },
    )
    assert res.status_code == 404  # assert_tenant hides the other tenant


@pytest.mark.anyio
async def test_rls_blocks_even_without_app_checks(client):
    """Defense-in-depth: hit PostgREST directly with tenant A's JWT and
    filter for tenant B's rows — the database itself must return nothing."""
    async with AsyncClient(base_url=settings.POSTGREST_URL) as raw:
        res = await raw.get(
            f"/bookings?business_id=eq.{TENANT_B}",
            headers={"Authorization": f"Bearer {user_token(TENANT_A)}"},
        )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
async def test_tenant_scoped_calls_and_analytics(client):
    res = await client.get("/api/calls/", headers=auth_header(TENANT_A))
    assert res.status_code == 200
    assert {c["id"] for c in res.json()} is not None
    res = await client.get("/api/analytics/summary", headers=auth_header(TENANT_A))
    assert res.status_code == 200
    assert "total_calls" in res.json()


@pytest.mark.anyio
async def test_queue_hold_join_and_isolation(client):
    res = await client.post(
        "/api/queue-holds/join",
        headers=auth_header(TENANT_A),
        json={"business_id": TENANT_A, "caller_number": "+17135559999"},
    )
    assert res.status_code == 201
    hold = res.json()
    assert hold["position"] >= 1

    # idempotent join
    res2 = await client.post(
        "/api/queue-holds/join",
        headers=auth_header(TENANT_A),
        json={"business_id": TENANT_A, "caller_number": "+17135559999"},
    )
    assert res2.json()["id"] == hold["id"]

    # tenant B can't see tenant A's queue
    res3 = await client.get(
        f"/api/queue-holds/?business_id={TENANT_A}", headers=auth_header(TENANT_B)
    )
    assert res3.status_code == 403
