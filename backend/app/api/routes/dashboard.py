"""Dashboard API routes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta
from app.models.database import get_db
from app.models.business import Business
from app.models.call import Call
from app.models.booking import Booking
from pydantic import BaseModel

router = APIRouter()

class DashboardStats(BaseModel):
    today_calls: int
    today_bookings: int
    active_calls: int
    satisfaction_score: float

@router.get("/stats")
async def get_dashboard_stats(
    business_id: str,
    db: Session = Depends(get_db)
):
    """Get main dashboard statistics"""
    today = datetime.utcnow().date()
    
    # Today's calls
    today_calls = db.query(func.count(Call.id)).filter(
        and_(
            Call.business_id == business_id,
            func.date(Call.started_at) == today
        )
    ).scalar() or 0
    
    # Today's bookings
    today_bookings = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.business_id == business_id,
            func.date(Booking.created_at) == today
        )
    ).scalar() or 0
    
    # Active calls
    active_calls = db.query(func.count(Call.id)).filter(
        and_(
            Call.business_id == business_id,
            Call.status == "in-progress"
        )
    ).scalar() or 0
    
    # Average satisfaction
    avg_satisfaction = db.query(func.avg(Call.customer_satisfaction)).filter(
        and_(
            Call.business_id == business_id,
            Call.customer_satisfaction.isnot(None)
        )
    ).scalar() or 0.0
    
    return {
        "today_calls": today_calls,
        "today_bookings": today_bookings,
        "active_calls": active_calls,
        "satisfaction_score": round(float(avg_satisfaction), 2)
    }

@router.get("/calls/recent")
async def get_recent_calls(
    business_id: str,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get recent calls"""
    calls = db.query(Call).filter(
        Call.business_id == business_id
    ).order_by(Call.started_at.desc()).limit(limit).all()
    
    return [
        {
            "id": call.id,
            "call_sid": call.call_sid,
            "caller_number": call.caller_number,
            "detected_language": call.detected_language,
            "intent": call.intent,
            "status": call.status,
            "duration_seconds": call.duration_seconds,
            "escalated": call.escalated_to_human,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None
        }
        for call in calls
    ]

@router.get("/calls/{call_id}/transcript")
async def get_call_transcript(
    call_id: str,
    db: Session = Depends(get_db)
):
    """Get full call transcript"""
    call = db.query(Call).filter(Call.id == call_id).first()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call_id": call.id,
        "transcript": call.transcript or [],
        "summary": call.summary,
        "recording_url": call.recording_url
    }

@router.get("/analytics/calls")
async def get_call_analytics(
    business_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get call analytics"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    base_query = db.query(Call).filter(
        and_(
            Call.business_id == business_id,
            Call.started_at >= start_date,
            Call.started_at <= end_date
        )
    )
    
    total_calls = base_query.count()
    completed_calls = base_query.filter(Call.status == "completed").count()
    escalated_calls = base_query.filter(Call.escalated_to_human == True).count()
    
    avg_duration = db.query(func.avg(Call.duration_seconds)).filter(
        and_(
            Call.business_id == business_id,
            Call.started_at >= start_date,
            Call.started_at <= end_date,
            Call.duration_seconds.isnot(None)
        )
    ).scalar() or 0
    
    # By language
    language_stats = db.query(
        Call.detected_language,
        func.count(Call.id)
    ).filter(
        and_(
            Call.business_id == business_id,
            Call.started_at >= start_date,
            Call.started_at <= end_date
        )
    ).group_by(Call.detected_language).all()
    
    by_language = {lang or "unknown": count for lang, count in language_stats}
    
    # By intent
    intent_stats = db.query(
        Call.intent,
        func.count(Call.id)
    ).filter(
        and_(
            Call.business_id == business_id,
            Call.started_at >= start_date,
            Call.started_at <= end_date
        )
    ).group_by(Call.intent).all()
    
    by_intent = {intent or "unknown": count for intent, count in intent_stats}
    
    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "escalated_calls": escalated_calls,
        "average_duration": round(float(avg_duration), 2),
        "by_language": by_language,
        "by_intent": by_intent
    }

@router.get("/bookings/recent")
async def get_recent_bookings(
    business_id: str,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get recent bookings"""
    bookings = db.query(Booking).filter(
        Booking.business_id == business_id
    ).order_by(Booking.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": booking.id,
            "customer_name": booking.customer_name,
            "customer_phone": booking.customer_phone,
            "service_name": booking.service_name,
            "scheduled_at": booking.scheduled_at.isoformat(),
            "status": booking.status,
            "confirmation_code": booking.confirmation_code,
            "created_at": booking.created_at.isoformat()
        }
        for booking in bookings
    ]
