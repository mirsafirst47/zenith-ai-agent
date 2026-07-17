"""FAQ answering is wired into the live conversation flow.

Two layers verified:
1. Mock-LLM path: an FAQ question asked mid-call gets the business's
   configured answer back (previously: generic deflection, KB orphaned).
2. LLM path: the system prompt handed to Claude contains the FAQ Q&As
   and the priced catalog, so live calls can answer them.
"""
import os
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.knowledge_base import knowledge_manager
from app.db import repos
from app.db.client import service_client
from app.main import app
from app.services.claude_service import claude_service

FAQ = {
    "do you take walk-ins": "Yes, walk-ins are welcome before 3pm on weekdays.",
    "do you offer loaner cars": "No loaners, but we're right next to the light rail.",
}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def garage():
    return await repos.create_business(service_client(), {
        "name": "FAQ Garage",
        "phone_number": "+1346555" + str(uuid.uuid4().int)[:4],
        "business_type": "mechanic",
        "config": {
            "service_catalog": [{"name": "Oil Change", "price": 49.99, "duration_minutes": 30}],
            "faq": FAQ,
        },
    })


@pytest.mark.anyio
async def test_faq_answered_mid_call(client, garage):
    res = await client.post("/api/voice/test/simulate", data={
        "business_phone": garage["phone_number"],
        "caller_number": "+17135550808",
        "message": "Quick question, do you guys take walk-ins?",
    })
    assert res.status_code == 200, res.text
    reply = res.json()["conversation"][-1]["content"]
    assert "before 3pm" in reply, f"FAQ answer not used; got: {reply}"


@pytest.mark.anyio
async def test_catalog_inquiry_lists_priced_services(client, garage):
    res = await client.post("/api/voice/test/simulate", data={
        "business_phone": garage["phone_number"],
        "caller_number": "+17135550809",
        "message": "How much do your services cost?",
    })
    reply = res.json()["conversation"][-1]["content"]
    assert "Oil Change" in reply and "49.99" in reply


@pytest.mark.anyio
async def test_llm_system_prompt_carries_faq_and_catalog(client, garage):
    # Simulate a call so the KB is loaded for this business
    await client.post("/api/voice/test/simulate", data={
        "business_phone": garage["phone_number"],
        "caller_number": "+17135550810",
        "message": "hello",
    })
    kb = knowledge_manager.get_knowledge_base(garage["id"])
    assert kb is not None

    prompt = claude_service.build_phone_agent_prompt(
        business_name=garage["name"],
        business_info=kb.to_context_dict(),
        customer_emotion="neutral",
        preferred_tone="professional",
        detected_intent="inquiry",
        collected_entities={},
        language="en",
    )
    assert "walk-ins are welcome before 3pm" in prompt
    assert "Oil Change" in prompt and "49.99" in prompt
    assert "use these answers verbatim" in prompt
