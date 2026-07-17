"""Call history routes"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from postgrest import AsyncPostgrestClient
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import AuthContext, get_auth, get_db, scoped_business_id
from app.db import repos

router = APIRouter()


class CallResponse(BaseModel):
    id: str
    call_sid: str
    caller_number: str
    status: str
    detected_language: Optional[str] = None
    intent: Optional[str] = None
    emotion: Optional[str] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


@router.get("/", response_model=List[CallResponse])
async def list_calls(
    limit: int = 50,
    business_id: Optional[str] = None,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    """List recent calls (tenant-scoped by RLS + app check)"""
    business_id = scoped_business_id(business_id, auth)
    return await repos.list_calls(db, business_id=business_id, limit=limit)


async def _get_scoped_call(call_id: str, db: AsyncPostgrestClient, auth: Optional[AuthContext]) -> dict:
    res = await db.from_("calls").select("*").eq("id", call_id).execute()
    call = res.data[0] if res.data else None
    if not call or (auth is not None and call["business_id"] != auth.business_id):
        # 404, not 403 — don't confirm the call exists in another tenant
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    return await _get_scoped_call(call_id, db, auth)


@router.get("/{call_id}/transcript")
async def get_transcript(
    call_id: str,
    db: AsyncPostgrestClient = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_auth),
):
    call = await _get_scoped_call(call_id, db, auth)
    return {"call_id": call_id, "transcript": call.get("transcript") or []}
