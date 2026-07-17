"""Data-access functions over PostgREST.

Every function takes a client explicitly — the caller decides whether
this runs as the service role (voice pipeline) or as the signed-in user
(dashboard routes, where RLS applies). Functions return plain dicts in
the same shape the REST API responses use.
"""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from postgrest import AsyncPostgrestClient

BOOKING_STATUSES = ("pending", "confirmed", "modified", "completed", "cancelled", "no_show")
QUEUE_HOLD_STATUSES = ("waiting", "notified", "expired", "cancelled", "served")
QUEUE_ACTIVE_STATUS = "waiting"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_confirmation_code(length: int = 6) -> str:
    # Unambiguous charset — read aloud over the phone
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(alphabet, k=length))


# ---------------------------------------------------------------- businesses

async def get_business_by_id(db: AsyncPostgrestClient, business_id: str) -> Optional[Dict]:
    res = await db.from_("businesses").select("*").eq("id", business_id).execute()
    return res.data[0] if res.data else None


async def get_business_by_phone(db: AsyncPostgrestClient, phone_number: str) -> Optional[Dict]:
    res = await db.from_("businesses").select("*").eq("phone_number", phone_number).execute()
    return res.data[0] if res.data else None


async def list_businesses(db: AsyncPostgrestClient) -> List[Dict]:
    res = await db.from_("businesses").select("*").execute()
    return res.data


async def create_business(db: AsyncPostgrestClient, data: Dict) -> Dict:
    res = await db.from_("businesses").insert(data).execute()
    return res.data[0]


async def update_business(db: AsyncPostgrestClient, business_id: str, changes: Dict) -> Optional[Dict]:
    res = await db.from_("businesses").update(changes).eq("id", business_id).execute()
    return res.data[0] if res.data else None


# --------------------------------------------------------------------- users
# Mirror rows of auth.users: same id, plus business_id / role for RLS
# and the dashboard. Maintained by the auth routes with the service client.

async def get_user_by_id(db: AsyncPostgrestClient, user_id: str) -> Optional[Dict]:
    res = await db.from_("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None


async def count_users_for_business(db: AsyncPostgrestClient, business_id: str) -> int:
    res = await db.from_("users").select("id").eq("business_id", business_id).execute()
    return len(res.data)


async def create_user_mirror(db: AsyncPostgrestClient, data: Dict) -> Dict:
    res = await db.from_("users").insert(data).execute()
    return res.data[0]


# --------------------------------------------------------------------- calls

async def create_call(db: AsyncPostgrestClient, data: Dict) -> Dict:
    res = await db.from_("calls").insert(data).execute()
    return res.data[0]


async def get_call_by_sid(db: AsyncPostgrestClient, call_sid: str) -> Optional[Dict]:
    res = await db.from_("calls").select("*").eq("call_sid", call_sid).execute()
    return res.data[0] if res.data else None


async def update_call_by_sid(db: AsyncPostgrestClient, call_sid: str, changes: Dict) -> Optional[Dict]:
    res = await db.from_("calls").update(changes).eq("call_sid", call_sid).execute()
    return res.data[0] if res.data else None


async def list_calls(
    db: AsyncPostgrestClient,
    business_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    q = db.from_("calls").select("*").order("started_at", desc=True).limit(limit)
    if business_id:
        q = q.eq("business_id", business_id)
    res = await q.execute()
    return res.data


# ------------------------------------------------------------------ bookings

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
    row = {
        "business_id": business_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "scheduled_at": scheduled_at,
        "service_type": service_type,
        "resource": resource,
        "duration_minutes": duration_minutes,
        "status": status,
        "call_id": call_id,
        "confirmation_code": generate_confirmation_code(),
        "booking_metadata": booking_metadata or {},
    }
    res = await db.from_("bookings").insert(row).execute()
    return res.data[0]


async def get_booking(db: AsyncPostgrestClient, booking_id: str) -> Optional[Dict]:
    res = await db.from_("bookings").select("*").eq("id", booking_id).execute()
    return res.data[0] if res.data else None


async def update_booking(db: AsyncPostgrestClient, booking_id: str, changes: Dict) -> Optional[Dict]:
    res = await db.from_("bookings").update(changes).eq("id", booking_id).execute()
    return res.data[0] if res.data else None


async def list_bookings(
    db: AsyncPostgrestClient,
    business_id: Optional[str] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    limit: int = 100,
) -> List[Dict]:
    q = db.from_("bookings").select("*").order("scheduled_at").limit(limit)
    if business_id:
        q = q.eq("business_id", business_id)
    if status:
        q = q.eq("status", status)
    if upcoming_only:
        q = q.gte("scheduled_at", _now_iso())
    res = await q.execute()
    return res.data


async def find_active_booking(
    db: AsyncPostgrestClient,
    *,
    business_id: str,
    confirmation_code: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Optional[Dict]:
    """Locate a booking to modify/cancel: by confirmation code if the
    caller has it, else the next upcoming active booking on their number."""
    q = (
        db.from_("bookings")
        .select("*")
        .eq("business_id", business_id)
        .in_("status", ["pending", "confirmed", "modified"])
    )
    if confirmation_code:
        q = q.eq("confirmation_code", confirmation_code.upper())
    elif customer_phone:
        q = q.eq("customer_phone", customer_phone).gte("scheduled_at", _now_iso())
    else:
        return None
    res = await q.order("scheduled_at").limit(1).execute()
    return res.data[0] if res.data else None


# --------------------------------------------------------------- queue holds

async def get_active_hold(
    db: AsyncPostgrestClient, business_id: str, caller_number: str
) -> Optional[Dict]:
    res = (
        await db.from_("queue_holds")
        .select("*")
        .eq("business_id", business_id)
        .eq("caller_number", caller_number)
        .eq("status", QUEUE_ACTIVE_STATUS)
        .execute()
    )
    return res.data[0] if res.data else None


async def join_queue(
    db: AsyncPostgrestClient, business_id: str, caller_number: str
) -> Tuple[Dict, bool]:
    """Add a caller to the back of the line. Idempotent. Returns (hold, created)."""
    existing = await get_active_hold(db, business_id, caller_number)
    if existing:
        return existing, False

    max_res = (
        await db.from_("queue_holds")
        .select("position")
        .eq("business_id", business_id)
        .eq("status", QUEUE_ACTIVE_STATUS)
        .order("position", desc=True)
        .limit(1)
        .execute()
    )
    next_pos = (max_res.data[0]["position"] if max_res.data else 0) + 1
    res = (
        await db.from_("queue_holds")
        .insert(
            {
                "business_id": business_id,
                "caller_number": caller_number,
                "position": next_pos,
                "status": QUEUE_ACTIVE_STATUS,
            }
        )
        .execute()
    )
    return res.data[0], True


async def list_queue(
    db: AsyncPostgrestClient, business_id: str, status: Optional[str] = QUEUE_ACTIVE_STATUS
) -> List[Dict]:
    q = db.from_("queue_holds").select("*").eq("business_id", business_id).order("position")
    if status:
        q = q.eq("status", status)
    res = await q.execute()
    return res.data


async def update_hold(db: AsyncPostgrestClient, hold_id: str, changes: Dict) -> Optional[Dict]:
    res = await db.from_("queue_holds").update(changes).eq("id", hold_id).execute()
    return res.data[0] if res.data else None


async def waiting_holds_after(
    db: AsyncPostgrestClient, business_id: str, position: int
) -> List[Dict]:
    """Everyone behind a given position — the people whose place moves up."""
    res = (
        await db.from_("queue_holds")
        .select("*")
        .eq("business_id", business_id)
        .eq("status", QUEUE_ACTIVE_STATUS)
        .gt("position", position)
        .order("position")
        .execute()
    )
    return res.data


async def count_overlapping_bookings(
    db: AsyncPostgrestClient,
    business_id: str,
    start_iso: str,
    end_iso: str,
) -> int:
    """Active bookings whose [scheduled_at, +duration) window overlaps
    [start, end). Overlap test: existing.start < new.end AND
    existing.end > new.start — duration isn't queryable arithmetic via
    PostgREST, so fetch the narrow candidate window and finish in Python."""
    res = (
        await db.from_("bookings")
        .select("scheduled_at,duration_minutes")
        .eq("business_id", business_id)
        .in_("status", ["pending", "confirmed", "modified"])
        .lt("scheduled_at", end_iso)
        .gte("scheduled_at", _shift_iso(start_iso, minutes=-24 * 60))
        .execute()
    )
    start = _aware(datetime.fromisoformat(start_iso.replace("Z", "+00:00")))
    end = _aware(datetime.fromisoformat(end_iso.replace("Z", "+00:00")))
    count = 0
    for row in res.data:
        b_start = _aware(datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00")))
        b_end = b_start + timedelta(minutes=row.get("duration_minutes") or 60)
        if b_start < end and b_end > start:
            count += 1
    return count


def _aware(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never mix tz-ness."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _shift_iso(iso: str, minutes: int) -> str:
    dt = _aware(datetime.fromisoformat(iso.replace("Z", "+00:00")))
    return (dt + timedelta(minutes=minutes)).isoformat()
