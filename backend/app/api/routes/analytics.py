"""Analytics routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.models.database import get_db
from app.models.call import Call
from app.models.business import Business

router = APIRouter()


@router.get("/summary")
def get_summary(db: Session = Depends(get_db), business_id: str = None):
    """Get overall analytics summary"""
    query = db.query(Call)
    if business_id:
        query = query.filter(Call.business_id == business_id)
        print(f"📊 Analytics requested for business: {business_id}")

    total_calls = query.count()
    print(f"📊 Total calls for query: {total_calls}")

    # Calls in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_calls = query.filter(Call.started_at >= yesterday).count()

    # Average call duration
    avg_duration = query.with_entities(func.avg(Call.duration_seconds)).scalar() or 0

    # Completed calls
    completed_calls = query.filter(Call.status == "completed").count()

    # Escalated calls (calls that were transferred to human)
    escalated_calls = query.filter(Call.status == "escalated").count()

    # Language breakdown - filter out NULL values
    languages = query.filter(Call.detected_language.isnot(None)).with_entities(
        Call.detected_language,
        func.count(Call.id)
    ).group_by(Call.detected_language).all()

    print(f"📊 Languages found: {languages}")
    language_dict = {lang or 'unknown': count for lang, count in languages}
    print(f"📊 Language dict: {language_dict}")

    # Intent breakdown - filter out NULL values
    intents = query.filter(Call.intent.isnot(None)).with_entities(
        Call.intent,
        func.count(Call.id)
    ).group_by(Call.intent).all()

    print(f"📊 Intents found: {intents}")

    # Active calls (in-progress)
    active_calls = query.filter(Call.status == "in-progress").count()

    # Calculate satisfaction score (placeholder)
    satisfaction_score = 4.5

    intent_dict = {intent or "unknown": count for intent, count in intents}

    response = {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "escalated_calls": escalated_calls,
        "today_calls": recent_calls,
        "calls_last_24h": recent_calls,
        "today_bookings": 0,
        "active_calls": active_calls,
        "satisfaction_score": satisfaction_score,
        "average_duration": round(avg_duration, 1),
        "avg_duration_seconds": round(avg_duration, 1),
        "by_language": language_dict,
        "by_intent": intent_dict,
        "languages": language_dict
    }

    print(f"📊 Analytics response: {response}")
    return response


@router.get("/calls-by-day")
def calls_by_day(days: int = 7, db: Session = Depends(get_db)):
    """Get call volume by day"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    calls = db.query(
        func.date(Call.started_at).label('date'),
        func.count(Call.id).label('count')
    ).filter(
        Call.started_at >= start_date
    ).group_by(
        func.date(Call.started_at)
    ).all()
    
    return [{"date": str(c.date), "calls": c.count} for c in calls]


@router.get("/business/{business_id}")
def business_analytics(business_id: str, db: Session = Depends(get_db)):
    """Get analytics for a specific business"""
    total = db.query(Call).filter(Call.business_id == business_id).count()
    
    avg_duration = db.query(func.avg(Call.duration_seconds)).filter(
        Call.business_id == business_id
    ).scalar() or 0
    
    return {
        "business_id": business_id,
        "total_calls": total,
        "avg_duration_seconds": round(avg_duration, 1)
    }
