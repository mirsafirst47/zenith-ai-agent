"""Voice pipeline end-to-end (mock LLM mode, real database).

Drives the same code path a Twilio webhook hits: business lookup by
dialed number -> orchestrator -> intent/entities -> persistence.
"""
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


@pytest.fixture
async def mechanic():
    db = service_client()
    phone = "+1832555" + str(uuid.uuid4().int)[:4]
    return await repos.create_business(db, {
        "name": "E2E Test Garage",
        "phone_number": phone,
        "business_type": "mechanic",
        "config": {
            "service_catalog": ["oil change", "brake inspection", "tire rotation"],
            "faq": {"do you take walk-ins": "Yes, before 3pm on weekdays."},
        },
    })


@pytest.mark.anyio
async def test_simulated_call_persists_with_tenant(client, mechanic):
    res = await client.post("/api/voice/test/simulate", data={
        "business_phone": mechanic["phone_number"],
        "caller_number": "+17135550123",
        "message": "I'd like to book a brake inspection tomorrow at 2 PM, my name is Sam Rivera",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["business_id"] == mechanic["id"]
    assert body["intent"] == "booking"

    db = service_client()
    call = await repos.get_call_by_sid(db, body["call_sid"])
    assert call is not None
    assert call["business_id"] == mechanic["id"]
    assert len(call["transcript"]) == 3


@pytest.mark.anyio
async def test_queue_hold_intent_creates_hold(client, mechanic):
    caller = "+17135550777"
    res = await client.post("/api/voice/test/simulate", data={
        "business_phone": mechanic["phone_number"],
        "caller_number": caller,
        "message": "Can you hold my place in line and text me when it's my turn?",
    })
    assert res.status_code == 200, res.text
    assert res.json()["action"] == "queue_hold_created"

    hold = await repos.get_active_hold(service_client(), mechanic["id"], caller)
    assert hold is not None and hold["position"] >= 1


@pytest.mark.anyio
async def test_twilio_webhook_flow(client, mechanic):
    """The /incoming -> /process -> /status sequence Twilio drives."""
    call_sid = f"CA{uuid.uuid4().hex}"
    res = await client.post("/api/voice/incoming", data={
        "CallSid": call_sid, "From": "+17135550456", "To": mechanic["phone_number"],
    })
    assert res.status_code == 200
    assert "<Gather" in res.text

    res = await client.post("/api/voice/process", data={
        "CallSid": call_sid, "SpeechResult": "What are your hours?",
    })
    assert res.status_code == 200

    res = await client.post("/api/voice/status", data={
        "CallSid": call_sid, "CallStatus": "completed", "CallDuration": "42",
    })
    assert res.status_code == 200

    call = await repos.get_call_by_sid(service_client(), call_sid)
    assert call["status"] == "completed"
    assert call["duration_seconds"] == 42
    assert call["transcript"] and call["transcript"][0]["role"] == "user"
