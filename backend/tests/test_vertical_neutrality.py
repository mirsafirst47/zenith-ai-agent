"""Vertical neutrality: the SAME booking code must serve a mechanic, a
salon, and a restaurant, differing only by each business's config."""
import os
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import repos
from app.db.client import service_client
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_business(business_type: str, config: dict) -> dict:
    return await repos.create_business(service_client(), {
        "name": f"Vertical {business_type} {uuid.uuid4().hex[:4]}",
        "phone_number": "+1281555" + str(uuid.uuid4().int)[:4],
        "business_type": business_type,
        "config": config,
    })


async def simulate(client, business, message, caller="+17135551212"):
    res = await client.post("/api/voice/test/simulate", data={
        "business_phone": business["phone_number"],
        "caller_number": caller,
        "message": message,
    })
    assert res.status_code == 200, res.text
    return res.json()


@pytest.mark.anyio
async def test_salon_books_catalog_service_with_duration(client):
    salon = await make_business("salon", {
        "service_catalog": [
            {"name": "Gel Manicure", "price": 45, "duration_minutes": 45},
            {"name": "Balayage", "price": 180, "duration_minutes": 150},
        ],
        "appointment_capacity": {"max_concurrent": 4},
    })
    body = await simulate(
        client, salon,
        "Hi, I'd like to book a Balayage tomorrow at 10 AM, my name is Dana Kim",
    )
    assert body["action"] == "booking_confirmed"
    bookings = await repos.list_bookings(service_client(), business_id=salon["id"])
    assert len(bookings) == 1
    booking = bookings[0]
    assert booking["service_type"] == "Balayage"
    assert booking["duration_minutes"] == 150
    assert "party_size" not in (booking["booking_metadata"] or {})


@pytest.mark.anyio
async def test_mechanic_same_code_no_party_size_prompt(client):
    mech = await make_business("mechanic", {
        "service_catalog": ["oil change", "brake inspection"],
        "appointment_capacity": {"max_concurrent": 2},
    })
    body = await simulate(client, mech, "I need an appointment")
    # First gather prompt must NOT be the restaurant party-size question
    last = body["conversation"][-1]["content"].lower()
    assert "party" not in last
    assert "day" in last or "service" in last


@pytest.mark.anyio
async def test_restaurant_still_collects_party_size(client):
    resto = await make_business("restaurant", {
        "service_catalog": ["dinner"],
        "appointment_capacity": {"max_concurrent": 20, "max_party_size": 8},
    })
    body = await simulate(client, resto, "I'd like to book a table")
    assert "how many people" in body["conversation"][-1]["content"].lower()


@pytest.mark.anyio
async def test_custom_booking_fields_from_config(client):
    mech = await make_business("mechanic", {
        "service_catalog": ["oil change"],
        "booking_fields": ["service_type", "date", "time", "name"],
    })
    body = await simulate(client, mech, "Can I make an appointment?")
    assert "which service" in body["conversation"][-1]["content"].lower()


@pytest.mark.anyio
async def test_capacity_full_offers_alternative(client):
    mech = await make_business("mechanic", {
        "service_catalog": [{"name": "oil change", "duration_minutes": 60}],
        "appointment_capacity": {"max_concurrent": 1},
    })
    first = await simulate(
        client, mech,
        "Book me an oil change tomorrow at 2 PM, my name is Alex Chen",
        caller="+17135553001",
    )
    assert first["action"] == "booking_confirmed"

    second = await simulate(
        client, mech,
        "Book me an oil change tomorrow at 2 PM, my name is Blake Ortiz",
        caller="+17135553002",
    )
    assert second["action"] != "booking_confirmed"
    assert "fully booked" in second["conversation"][-1]["content"].lower()
    bookings = await repos.list_bookings(service_client(), business_id=mech["id"])
    assert len(bookings) == 1  # the second one must NOT have been created
