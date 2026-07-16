"""Call history routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.database import get_db
from app.models.call import Call
from app.models.user import User
from app.api.deps import get_current_user, scoped_business_id

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
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """List recent calls (scoped to the caller's business when auth is on)"""
    business_id = scoped_business_id(business_id, user)
    query = db.query(Call).order_by(Call.started_at.desc())
    if business_id:
        query = query.filter(Call.business_id == business_id)
    return query.limit(limit).all()


def _get_scoped_call(call_id: str, db: Session, user: Optional[User]) -> Call:
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if user is not None and call.business_id != user.business_id:
        # 404, not 403 — don't confirm the call exists in another tenant
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/{call_id}", response_model=CallResponse)
def get_call(
    call_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific call"""
    return _get_scoped_call(call_id, db, user)


@router.get("/{call_id}/transcript")
def get_transcript(
    call_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Get call transcript"""
    call = _get_scoped_call(call_id, db, user)
    return {
        "call_id": call_id,
        "transcript": call.transcript or []
    }
