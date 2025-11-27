from fastapi import APIRouter, Form, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.call import Call
from app.models.business import Business
from app.core.agent_orchestrator import agent_orchestrator
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/incoming")
async def handle_incoming(CallSid: str = Form(...), From: str = Form(...), To: str = Form(...), db: Session = Depends(get_db)):
    # Find business by phone number
    business = db.query(Business).filter(Business.phone_number == To).first()
    
    call = Call(
        call_sid=CallSid, 
        caller_number=From, 
        status="in-progress", 
        started_at=datetime.utcnow(),
        business_id=str(business.id) if business else None  # ← FIX: Add business_id
    )
    db.add(call)
    db.commit()
    
    greeting, lang = await agent_orchestrator.handle_incoming_call(CallSid, From, To, db)
    twiml = f'<?xml version="1.0"?><Response><Say>{greeting}</Say></Response>'
    return Response(content=twiml, media_type="application/xml")

@router.post("/test/simulate")
async def simulate(business_phone: str = Form(...), message: str = Form("Hello"), db: Session = Depends(get_db)):
    call_sid = f"TEST_{uuid.uuid4().hex[:8]}"
    
    # Find business FIRST
    business = db.query(Business).filter(Business.phone_number == business_phone).first()
    if not business:
        return {"error": "Business not found", "phone": business_phone}
    
    # Create call with business_id
    call = Call(
        call_sid=call_sid,
        caller_number="+14155551234",
        status="completed",
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow(),
        business_id=str(business.id),  # ← FIX: Link to business
        duration_seconds=30
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    
    # Run conversation
    greeting, lang = await agent_orchestrator.handle_incoming_call(call_sid, "+14155551234", business_phone, db)
    response, action = await agent_orchestrator.process_user_speech(call_sid, message, db)
    
    # Update call with results
    call.detected_language = lang
    call.status = "completed"
    db.commit()
    
    return {
        "call_sid": call_sid,
        "call_id": str(call.id),  # ← Return the actual call ID
        "business_id": str(business.id),
        "conversation": [
            {"role": "assistant", "content": greeting},
            {"role": "user", "content": message},
            {"role": "assistant", "content": response}
        ]
    }
