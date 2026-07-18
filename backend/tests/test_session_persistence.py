"""Session state survives restarts and works across instances.

"Restart" is simulated the honest way: wipe every in-memory store
(orchestrator sessions, agent contexts, knowledge bases) mid-call, then
continue the conversation. The next turn must hydrate from the
agent_sessions table and pick up exactly where it left off — collected
entities, language, business knowledge and all.
"""
import os
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core import session_store
from app.core.intelligent_agent import intelligent_agent
from app.core.knowledge_base import knowledge_manager
from app.core.unified_orchestrator import unified_orchestrator
from app.db import repos
from app.db.client import service_client
from app.main import app


def wipe_memory():
    """Simulate a process restart / a webhook landing on another instance."""
    unified_orchestrator._sessions.clear()
    intelligent_agent.contexts.clear()
    knowledge_manager._knowledge_bases.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def salon():
    return await repos.create_business(service_client(), {
        "name": "Persistence Salon",
        "phone_number": "+1713444" + str(uuid.uuid4().int)[:4],
        "business_type": "salon",
        "config": {
            "service_catalog": [{"name": "Haircut", "duration_minutes": 45}],
            "faq": {"do you take card": "Yes, all major cards accepted."},
        },
    })


async def start_call(client, salon, call_sid):
    res = await client.post("/api/voice/incoming", data={
        "CallSid": call_sid, "From": "+17135551234", "To": salon["phone_number"],
    })
    assert res.status_code == 200


async def speak(client, call_sid, text):
    res = await client.post("/api/voice/process", data={
        "CallSid": call_sid, "SpeechResult": text,
    })
    assert res.status_code == 200
    return res.text


@pytest.mark.anyio
async def test_call_survives_process_restart(client, salon):
    call_sid = f"CA{uuid.uuid4().hex}"
    await start_call(client, salon, call_sid)
    await speak(client, call_sid, "I'd like to book a haircut tomorrow")

    # ---- the server "dies" here ----
    wipe_memory()
    assert unified_orchestrator.get_session(call_sid) is None

    # Next webhook turn must NOT be the lost-call apology
    reply = await speak(client, call_sid, "2 PM works, my name is Maria Lopez")
    assert "connection issue" not in reply.lower()

    # Entities gathered before the restart are still there
    context = intelligent_agent.contexts[call_sid]
    assert context.entities.get("date"), "pre-restart entity lost"
    session = unified_orchestrator.get_session(call_sid)
    assert session.business_id == salon["id"]


@pytest.mark.anyio
async def test_business_knowledge_rehydrates(client, salon):
    call_sid = f"CA{uuid.uuid4().hex}"
    await start_call(client, salon, call_sid)
    wipe_memory()

    reply = await speak(client, call_sid, "Do you take card?")
    assert "all major cards accepted" in reply.lower() or "cards accepted" in reply


@pytest.mark.anyio
async def test_session_row_deleted_on_call_end(client, salon):
    call_sid = f"CA{uuid.uuid4().hex}"
    await start_call(client, salon, call_sid)
    assert await session_store.load(call_sid) is not None

    res = await client.post("/api/voice/status", data={
        "CallSid": call_sid, "CallStatus": "completed", "CallDuration": "30",
    })
    assert res.status_code == 200
    assert await session_store.load(call_sid) is None


@pytest.mark.anyio
async def test_unknown_call_sid_still_fails_gracefully(client):
    res = await client.post("/api/voice/process", data={
        "CallSid": "CA_never_existed", "SpeechResult": "hello?",
    })
    assert res.status_code == 200
    assert "connection issue" in res.text.lower()
