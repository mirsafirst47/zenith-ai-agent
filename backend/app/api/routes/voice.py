"""Voice webhook routes.

Twilio TwiML endpoints (current pipeline) backed by the unified
orchestrator. Persistence goes through the service-role Supabase client
— phone callers aren't authenticated users, so the voice pipeline is
trusted code operating across the tenant it resolved from the dialed
number.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Form
from fastapi.responses import Response

from app.core.unified_orchestrator import handle_incoming_call, process_speech, end_call
from app.db import repos
from app.db.client import service_client

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_business_data(business: dict) -> dict:
    """Shape a business row for the orchestrator.

    The in-memory contract keeps a flat "services" key (what the agent
    speaks about); it is sourced from config.service_catalog in the
    generalized schema.
    """
    config = business.get("config") or {}
    return {
        "id": str(business["id"]),
        "name": business["name"],
        "phone_number": business["phone_number"],
        "description": business.get("description"),
        "business_type": business["business_type"],
        "hours_of_operation": business.get("hours_of_operation") or {},
        "services": config.get("service_catalog", []),
        "config": config,
    }


def create_twiml(message: str, gather: bool = True, language: str = "en-US") -> str:
    """Create TwiML response"""
    if gather:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" timeout="3" language="{language}" action="/api/voice/process" method="POST">
        <Say>{message}</Say>
    </Gather>
    <Say>I didn't catch that. Please try again.</Say>
</Response>'''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{message}</Say>
</Response>'''


@router.post("/incoming")
async def handle_incoming(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
):
    """Handle incoming Twilio call"""
    db = service_client()
    business = await repos.get_business_by_phone(db, To)
    business_data = build_business_data(business) if business else None

    greeting, language = await handle_incoming_call(CallSid, From, To, business_data)

    await repos.create_call(
        db,
        {
            "call_sid": CallSid,
            "caller_number": From,
            "status": "in-progress",
            "started_at": _now(),
            "business_id": business["id"] if business else None,
            "detected_language": language,
        },
    )

    lang_map = {"en": "en-US", "es": "es-MX", "fr": "fr-FR", "zh": "zh-CN", "ru": "ru-RU"}
    return Response(
        content=create_twiml(greeting, language=lang_map.get(language, "en-US")),
        media_type="application/xml",
    )


@router.post("/process")
async def process_input(
    CallSid: str = Form(...),
    SpeechResult: str = Form(default=""),
):
    """Process speech input"""
    if not SpeechResult:
        return Response(
            content=create_twiml("I didn't catch that. Could you please repeat?"),
            media_type="application/xml",
        )

    result = await process_speech(CallSid, SpeechResult)
    response_text = result.get("response", "How can I help you?")
    action = result.get("action", "continue")

    db = service_client()
    call = await repos.get_call_by_sid(db, CallSid)
    if call:
        changes = {"detected_language": result.get("language", call.get("detected_language"))}

        if action == "booking_confirmed" and result.get("data", {}).get("id"):
            changes["booking_id"] = result["data"]["id"]
            changes["action_taken"] = "booking_created"
            await repos.update_booking(db, result["data"]["id"], {"call_id": call["id"]})
        elif action == "queue_hold_created":
            changes["action_taken"] = "queue_hold_created"

        transcript = call.get("transcript") or []
        transcript.append({"role": "user", "content": SpeechResult})
        transcript.append({"role": "assistant", "content": response_text})
        changes["transcript"] = transcript
        await repos.update_call_by_sid(db, CallSid, changes)

    if action == "escalate":
        # In production, would transfer to human
        return Response(
            content=create_twiml(response_text + " Transferring now.", gather=False),
            media_type="application/xml",
        )

    return Response(content=create_twiml(response_text), media_type="application/xml")


@router.post("/status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: int = Form(default=0),
):
    """Handle call status webhook"""
    db = service_client()
    changes = {"status": CallStatus, "duration_seconds": CallDuration}
    if CallStatus in ["completed", "failed", "busy", "no-answer"]:
        changes["ended_at"] = _now()
    await repos.update_call_by_sid(db, CallSid, changes)

    if CallStatus in ["completed", "failed"]:
        await end_call(CallSid, CallStatus)

    return {"status": "ok"}


@router.post("/test/simulate")
async def simulate_call(
    business_phone: str = Form(...),
    caller_number: str = Form(default="+14155551234"),
    message: str = Form(default="Hello"),
):
    """Simulate a call for testing (no Twilio needed)"""
    call_sid = f"TEST_{uuid.uuid4().hex[:8]}"
    db = service_client()

    business = await repos.get_business_by_phone(db, business_phone)
    if not business:
        return {"error": "Business not found", "phone": business_phone}

    business_data = build_business_data(business)

    greeting, language = await handle_incoming_call(call_sid, caller_number, business_phone, business_data)
    result = await process_speech(call_sid, message)

    # Final detected language from the session (may change during speech)
    from app.core.unified_orchestrator import unified_orchestrator
    session = unified_orchestrator.get_session(call_sid)
    final_language = session.language if session else language

    transcript = [
        {"role": "assistant", "content": greeting},
        {"role": "user", "content": message},
        {"role": "assistant", "content": result.get("response", "")},
    ]
    call = await repos.create_call(
        db,
        {
            "call_sid": call_sid,
            "caller_number": caller_number,
            "status": "completed",
            "started_at": _now(),
            "ended_at": _now(),
            "business_id": business["id"],
            "duration_seconds": 30,
            "detected_language": final_language,
            "emotion": result.get("emotion"),
            "intent": result.get("intent"),
            "transcript": transcript,
        },
    )

    await end_call(call_sid, "completed")

    return {
        "call_sid": call_sid,
        "call_id": call["id"],
        "business_id": business["id"],
        "language": final_language,
        "emotion": result.get("emotion"),
        "intent": result.get("intent"),
        "entities": result.get("data", {}).get("entities", result.get("entities", {})),
        "action": result.get("action"),
        "conversation": transcript,
    }
