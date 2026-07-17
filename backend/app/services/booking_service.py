"""Booking persistence helpers shared by the REST API and the voice
orchestrator. Thin wrappers over app.db.repos so both entry points
create identical rows."""
from typing import Dict, Optional

from postgrest import AsyncPostgrestClient

from app.db import repos


async def create_booking(
    db: AsyncPostgrestClient,
    *,
    business_id: str,
    customer_name: str,
    customer_phone: str,
    scheduled_at: str,
    service_type: Optional[str] = None,
    resource: Optional[str] = None,
    duration_minutes: int = 60,
    status: str = "pending",
    call_id: Optional[str] = None,
    booking_metadata: Optional[Dict] = None,
) -> Dict:
    return await repos.create_booking(
        db,
        business_id=business_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        scheduled_at=scheduled_at,
        service_type=service_type,
        resource=resource,
        duration_minutes=duration_minutes,
        status=status,
        call_id=call_id,
        booking_metadata=booking_metadata,
    )


async def find_active_booking(
    db: AsyncPostgrestClient,
    *,
    business_id: str,
    confirmation_code: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Optional[Dict]:
    return await repos.find_active_booking(
        db,
        business_id=business_id,
        confirmation_code=confirmation_code,
        customer_phone=customer_phone,
    )
