"""Queue-hold domain logic shared by the REST API and the voice
orchestrator: join, notify ("it's your turn"), resolve + position
shuffling with SMS updates. Persistence via app.db.repos."""
from datetime import datetime, timezone
from typing import Dict, Tuple

from postgrest import AsyncPostgrestClient

from app.db import repos
from app.db.repos import QUEUE_ACTIVE_STATUS
from app.services.twilio_service import twilio_service

ACTIVE_STATUS = QUEUE_ACTIVE_STATUS  # re-export, existing imports use this name


async def join_queue(db: AsyncPostgrestClient, business_id: str, caller_number: str) -> Tuple[Dict, bool]:
    return await repos.join_queue(db, business_id, caller_number)


def _send_sms_safe(to: str, body: str) -> None:
    """Notification failure must never corrupt queue state — log and continue."""
    try:
        twilio_service.send_sms(to, body)
    except Exception as e:
        print(f"⚠️ Queue SMS to {to} failed: {e}")


async def notify_hold(db: AsyncPostgrestClient, hold: Dict) -> Dict:
    """It's this caller's turn: SMS them and mark the hold notified."""
    business = await repos.get_business_by_id(db, hold["business_id"])
    name = business["name"] if business else "the business"
    _send_sms_safe(
        hold["caller_number"],
        f"It's your turn at {name}! Please call back or head over now.",
    )
    return await repos.update_hold(
        db,
        hold["id"],
        {"status": "notified", "notified_at": datetime.now(timezone.utc).isoformat()},
    )


async def resolve_hold(db: AsyncPostgrestClient, hold: Dict, terminal_status: str) -> Dict:
    """Close a hold and move everyone behind them up one place, texting
    each waiting caller their new position."""
    updated = await repos.update_hold(db, hold["id"], {"status": terminal_status})

    if hold["status"] == QUEUE_ACTIVE_STATUS:  # position only frees if they were still waiting
        behind = await repos.waiting_holds_after(db, hold["business_id"], hold["position"])
        business = await repos.get_business_by_id(db, hold["business_id"])
        name = business["name"] if business else "the business"
        for waiting in behind:
            new_pos = waiting["position"] - 1
            await repos.update_hold(db, waiting["id"], {"position": new_pos})
            if new_pos == 1:
                body = f"You're next in line at {name}! We'll text you the moment it's your turn."
            else:
                body = f"Update from {name}: you're now number {new_pos} in line."
            _send_sms_safe(waiting["caller_number"], body)

    return updated
