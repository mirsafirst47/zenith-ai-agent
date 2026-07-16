"""Queue-hold routes — "hold your place in line, get texted instead of
staying on hold". Backs the queue_holds table."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.database import get_db
from app.models.queue_hold import QueueHold, QUEUE_HOLD_STATUSES
from app.models.business import Business
from app.models.user import User
from app.api.deps import get_current_user, scoped_business_id, assert_tenant
from app.services.queue_service import join_queue as join_queue_row, ACTIVE_STATUS

router = APIRouter()
# Terminal statuses release the position
TERMINAL_STATUSES = ("expired", "cancelled", "served")


class QueueHoldJoin(BaseModel):
    business_id: str
    caller_number: str


class QueueHoldResponse(BaseModel):
    id: str
    business_id: str
    caller_number: str
    position: int
    status: str
    notified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("/join", response_model=QueueHoldResponse, status_code=201)
def join_queue(
    hold: QueueHoldJoin,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Add a caller to the back of a business's queue (idempotent)"""
    assert_tenant(hold.business_id, user)
    business = db.query(Business).filter(Business.id == hold.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db_hold, _created = join_queue_row(db, hold.business_id, hold.caller_number)
    return db_hold


@router.get("/", response_model=List[QueueHoldResponse])
def list_queue(
    business_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """List a business's queue, in line order"""
    business_id = scoped_business_id(business_id, user)
    query = db.query(QueueHold).filter(QueueHold.business_id == business_id)
    if status:
        query = query.filter(QueueHold.status == status)
    else:
        query = query.filter(QueueHold.status.in_((ACTIVE_STATUS, "notified")))
    return query.order_by(QueueHold.position.asc()).all()


@router.post("/{hold_id}/notify", response_model=QueueHoldResponse)
def notify_caller(
    hold_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Mark a hold notified (it's the caller's turn) and stamp notified_at.

    SMS sending goes through the notification service; this endpoint
    records the state transition either way so the queue stays correct
    even when Twilio isn't configured (dev/mock mode).
    """
    hold = db.query(QueueHold).filter(QueueHold.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Queue hold not found")
    assert_tenant(hold.business_id, user)
    if hold.status != ACTIVE_STATUS:
        raise HTTPException(status_code=409, detail=f"Cannot notify a hold in status '{hold.status}'")

    business = db.query(Business).filter(Business.id == hold.business_id).first()
    try:
        from app.services.twilio_service import twilio_service
        twilio_service.send_sms(
            hold.caller_number,
            f"It's your turn at {business.name if business else 'the business'}! "
            "Please call back or head over now.",
        )
    except Exception as e:
        # Notification failure shouldn't corrupt queue state — log and continue
        print(f"⚠️ Queue-hold SMS failed for {hold.id}: {e}")

    hold.status = "notified"
    hold.notified_at = datetime.utcnow()
    db.commit()
    db.refresh(hold)
    return hold


@router.post("/{hold_id}/resolve", response_model=QueueHoldResponse)
def resolve_hold(
    hold_id: str,
    status: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """Close out a hold as served / cancelled / expired"""
    if status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid terminal status '{status}'. Must be one of: {', '.join(TERMINAL_STATUSES)}",
        )
    hold = db.query(QueueHold).filter(QueueHold.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Queue hold not found")
    assert_tenant(hold.business_id, user)
    if hold.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Hold already resolved as '{hold.status}'")

    hold.status = status
    db.commit()
    db.refresh(hold)
    return hold
