"""Voice routes using the unified orchestrator"""
from fastapi import APIRouter, Form, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.call import Call
from app.models.business import Business
from app.core.unified_orchestrator import handle_incoming_call, process_speech, end_call
from datetime import datetime
import uuid

router = APIRouter()


def build_business_data(business: Business) -> dict:
    """Shape a Business row for the orchestrator.

    The in-memory contract keeps a flat "services" key (what the agent
    speaks about); it is sourced from config.service_catalog in the new
    generalized schema.
    """
    config = business.config or {}
    return {
        "id": str(business.id),
        "name": business.name,
        "phone_number": business.phone_number,
        "description": business.description,
        "business_type": business.business_type,
        "hours_of_operation": business.hours_of_operation or {},
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
    else:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{message}</Say>
</Response>'''


@router.post("/incoming")
async def handle_incoming(
    CallSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle incoming Twilio call"""
    
    # Find business
    business = db.query(Business).filter(Business.phone_number == To).first()
    business_data = build_business_data(business) if business else None
    
    # Create call record
    call = Call(
        call_sid=CallSid,
        caller_number=From,
        status="in-progress",
        started_at=datetime.utcnow(),
        business_id=str(business.id) if business else None
    )
    db.add(call)
    db.commit()
    
    # Handle with orchestrator
    greeting, language = await handle_incoming_call(CallSid, From, To, business_data)
    
    # Update call with language
    call.detected_language = language
    db.commit()
    
    # Map language to TwiML language code
    lang_map = {"en": "en-US", "es": "es-MX", "fr": "fr-FR", "zh": "zh-CN", "ru": "ru-RU"}
    twiml_lang = lang_map.get(language, "en-US")
    
    return Response(content=create_twiml(greeting, language=twiml_lang), media_type="application/xml")


@router.post("/process")
async def process_input(
    CallSid: str = Form(...),
    SpeechResult: str = Form(default=""),
    db: Session = Depends(get_db)
):
    """Process speech input"""
    
    if not SpeechResult:
        return Response(
            content=create_twiml("I didn't catch that. Could you please repeat?"),
            media_type="application/xml"
        )
    
    # Process with orchestrator
    result = await process_speech(CallSid, SpeechResult)
    
    response_text = result.get("response", "How can I help you?")
    action = result.get("action", "continue")
    
    # Update call record
    call = db.query(Call).filter(Call.call_sid == CallSid).first()
    if call:
        call.detected_language = result.get("language", call.detected_language)
        
        # Append to transcript
        transcript = call.transcript or []
        transcript.append({"role": "user", "content": SpeechResult})
        transcript.append({"role": "assistant", "content": response_text})
        call.transcript = transcript
        db.commit()
    
    # Handle escalation
    if action == "escalate":
        # In production, would transfer to human
        return Response(
            content=create_twiml(response_text + " Transferring now.", gather=False),
            media_type="application/xml"
        )
    
    return Response(content=create_twiml(response_text), media_type="application/xml")


@router.post("/status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    CallDuration: int = Form(default=0),
    db: Session = Depends(get_db)
):
    """Handle call status webhook"""
    
    call = db.query(Call).filter(Call.call_sid == CallSid).first()
    if call:
        call.status = CallStatus
        call.duration_seconds = CallDuration
        if CallStatus in ["completed", "failed", "busy", "no-answer"]:
            call.ended_at = datetime.utcnow()
        db.commit()
    
    # Clean up orchestrator
    if CallStatus in ["completed", "failed"]:
        await end_call(CallSid, CallStatus)
    
    return {"status": "ok"}


@router.post("/test/simulate")
async def simulate_call(
    business_phone: str = Form(...),
    caller_number: str = Form(default="+14155551234"),
    message: str = Form(default="Hello"),
    db: Session = Depends(get_db)
):
    """Simulate a call for testing (no Twilio needed)"""
    
    call_sid = f"TEST_{uuid.uuid4().hex[:8]}"
    
    # Find business
    business = db.query(Business).filter(Business.phone_number == business_phone).first()
    if not business:
        return {"error": "Business not found", "phone": business_phone}
    
    business_data = build_business_data(business)
    
    # Create call record
    call = Call(
        call_sid=call_sid,
        caller_number=caller_number,
        status="completed",
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        business_id=str(business.id),
        duration_seconds=30
    )
    db.add(call)
    db.commit()
    
    # Run through orchestrator
    greeting, language = await handle_incoming_call(call_sid, caller_number, business_phone, business_data)
    result = await process_speech(call_sid, message)

    # Get the final detected language from the session (may have changed during speech processing)
    from app.core.unified_orchestrator import unified_orchestrator
    session = unified_orchestrator._sessions.get(call_sid)
    final_language = session.language if session else language

    # Update call with detected language and other data
    call.detected_language = final_language
    call.emotion = result.get("emotion")
    call.intent = result.get("intent")
    call.transcript = [
        {"role": "assistant", "content": greeting},
        {"role": "user", "content": message},
        {"role": "assistant", "content": result.get("response", "")}
    ]
    db.commit()

    # Log for debugging
    print(f"✅ Test call saved:")
    print(f"   Call ID: {call.id}")
    print(f"   Business ID: {call.business_id}")
    print(f"   Language: {call.detected_language}")
    print(f"   Emotion: {call.emotion}")
    print(f"   Intent: {call.intent}")
    
    # Clean up
    await end_call(call_sid, "completed")
    
    return {
        "call_sid": call_sid,
        "call_id": str(call.id),
        "business_id": str(business.id),
        "language": language,
        "emotion": result.get("emotion"),
        "intent": result.get("intent"),
        "entities": result.get("data", {}).get("entities", result.get("entities", {})),
        "action": result.get("action"),
        "conversation": [
            {"role": "assistant", "content": greeting},
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.get("response", "")}
        ]
    }
