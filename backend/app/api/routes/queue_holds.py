"""Queue-hold routes — "hold your place in line, get texted instead of
staying on hold". Backs the queue_holds table."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from postgrest import AsyncPostgrestClient
from pydantic import BaseModel

from app.api.deps import AuthContext, assert_tenant, get_auth, get_db, scoped_business_id
from app.db import repos
from app.db.repos import QUEUE_ACTIVE_STATUS
from app.services.queue_service import notify_hold, resolve_hold as resolve_hold_svc

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


@router.post("/join", response_model=QueueHoldResponse, status_code=201)
async def join_queue(
    hold: QueueHoldJoin,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Add a caller to the back of a business's queue (idempotent)"""
    assert_tenant(hold.business_id, auth)
    business = await repos.get_business_by_id(db, hold.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    db_hold, _created = await repos.join_queue(db, hold.business_id, hold.caller_number)
    return db_hold


@router.get("/", response_model=List[QueueHoldResponse])
async def list_queue(
    business_id: str,
    status: Optional[str] = None,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """List a business's queue, in line order"""
    business_id = scoped_business_id(business_id, auth)
    if status:
        return await repos.list_queue(db, business_id, status=status)
    active = await repos.list_queue(db, business_id, status=QUEUE_ACTIVE_STATUS)
    notified = await repos.list_queue(db, business_id, status="notified")
    return sorted(active + notified, key=lambda h: h["position"])


async def _get_scoped_hold(hold_id: str, db: AsyncPostgrestClient, auth: Optional[AuthContext]) -> dict:
    res = await db.from_("queue_holds").select("*").eq("id", hold_id).execute()
    hold = res.data[0] if res.data else None
    if not hold:
        raise HTTPException(status_code=404, detail="Queue hold not found")
    assert_tenant(hold["business_id"], auth)
    return hold


@router.post("/{hold_id}/notify", response_model=QueueHoldResponse)
async def notify_caller(
    hold_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """It's the caller's turn: send the SMS and mark the hold notified."""
    hold = await _get_scoped_hold(hold_id, db, auth)
    if hold["status"] != QUEUE_ACTIVE_STATUS:
        raise HTTPException(status_code=409, detail=f"Cannot notify a hold in status '{hold['status']}'")
    return await notify_hold(db, hold)


@router.post("/{hold_id}/resolve", response_model=QueueHoldResponse)
async def resolve_hold(
    hold_id: str,
    status: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """Close out a hold as served / cancelled / expired.

    Frees the position — everyone behind moves up and gets a
    position-update SMS (that's the queue-hold promise)."""
    if status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid terminal status '{status}'. Must be one of: {', '.join(TERMINAL_STATUSES)}",
        )
    hold = await _get_scoped_hold(hold_id, db, auth)
    if hold["status"] in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail=f"Hold already resolved as '{hold['status']}'")
    return await resolve_hold_svc(db, hold, status)
