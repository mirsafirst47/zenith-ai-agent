"""Call history routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.database import get_db
from app.models.call import Call

router = APIRouter()


class CallResponse(BaseModel):
    id: str
    call_sid: str
    caller_number: str
    status: str
    detected_language: Optional[str]
    duration_seconds: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CallResponse])
def list_calls(
    limit: int = 50,
    business_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List recent calls"""
    query = db.query(Call).order_by(Call.started_at.desc())
    if business_id:
        query = query.filter(Call.business_id == business_id)
    return query.limit(limit).all()


@router.get("/{call_id}", response_model=CallResponse)
def get_call(call_id: str, db: Session = Depends(get_db)):
    """Get a specific call"""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/{call_id}/transcript")
def get_transcript(call_id: str, db: Session = Depends(get_db)):
    """Get call transcript"""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "call_id": call_id,
        "transcript": call.transcript or []
    }
