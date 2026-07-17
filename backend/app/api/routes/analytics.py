"""Analytics routes — computed in Python over the tenant's calls.
Fine at pilot scale; move to SQL views/RPC if call volume grows."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from postgrest import AsyncPostgrestClient

from app.api.deps import AuthContext, get_auth, get_db, scoped_business_id

router = APIRouter()

_FIELDS = "id,business_id,status,detected_language,intent,duration_seconds,started_at"


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _fetch_calls(db: AsyncPostgrestClient, business_id: Optional[str], limit: int = 5000):
    q = db.from_("calls").select(_FIELDS).order("started_at", desc=True).limit(limit)
    if business_id:
        q = q.eq("business_id", business_id)
    res = await q.execute()
    return res.data


@router.get("/summary")
async def get_summary(
    business_id: Optional[str] = None,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Analytics summary, scoped to the caller's business when auth is on"""
    business_id = scoped_business_id(business_id, auth)
    calls = await _fetch_calls(db, business_id)

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    durations = [c["duration_seconds"] for c in calls if c.get("duration_seconds")]
    recent = [c for c in calls if (_parse_ts(c.get("started_at")) or yesterday) >= yesterday]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    by_language = Counter(c["detected_language"] for c in calls if c.get("detected_language"))
    by_intent = Counter(c["intent"] for c in calls if c.get("intent"))

    return {
        "total_calls": len(calls),
        "completed_calls": sum(1 for c in calls if c["status"] == "completed"),
        "escalated_calls": sum(1 for c in calls if c["status"] == "escalated"),
        "today_calls": len(recent),
        "calls_last_24h": len(recent),
        "today_bookings": 0,
        "active_calls": sum(1 for c in calls if c["status"] == "in-progress"),
        "satisfaction_score": 4.5,  # placeholder until post-call surveys exist
        "average_duration": avg_duration,
        "avg_duration_seconds": avg_duration,
        "by_language": dict(by_language),
        "by_intent": dict(by_intent),
        "languages": dict(by_language),
    }


@router.get("/calls-by-day")
async def calls_by_day(
    days: int = 7,
    business_id: Optional[str] = None,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Call volume by day"""
    business_id = scoped_business_id(business_id, auth)
    start = datetime.now(timezone.utc) - timedelta(days=days)
    calls = await _fetch_calls(db, business_id)
    counts = Counter()
    for c in calls:
        ts = _parse_ts(c.get("started_at"))
        if ts and ts >= start:
            counts[ts.date().isoformat()] += 1
    return [{"date": d, "calls": n} for d, n in sorted(counts.items())]


@router.get("/business/{business_id}")
async def business_analytics(
    business_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Analytics for a specific business"""
    business_id = scoped_business_id(business_id, auth)
    calls = await _fetch_calls(db, business_id)
    durations = [c["duration_seconds"] for c in calls if c.get("duration_seconds")]
    return {
        "business_id": business_id,
        "total_calls": len(calls),
        "avg_duration_seconds": round(sum(durations) / len(durations), 1) if durations else 0,
    }
