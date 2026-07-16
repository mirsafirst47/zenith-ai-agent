"""Shared queue-hold persistence — used by both the REST API and the
voice orchestrator."""
from typing import Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.queue_hold import QueueHold

ACTIVE_STATUS = "waiting"


def next_position(db: Session, business_id: str) -> int:
    current_max = (
        db.query(func.max(QueueHold.position))
        .filter(QueueHold.business_id == business_id, QueueHold.status == ACTIVE_STATUS)
        .scalar()
    )
    return (current_max or 0) + 1


def join_queue(db: Session, business_id: str, caller_number: str) -> Tuple[QueueHold, bool]:
    """Add a caller to the back of the line. Idempotent — a caller already
    waiting gets their existing hold back. Returns (hold, created)."""
    existing = (
        db.query(QueueHold)
        .filter(
            QueueHold.business_id == business_id,
            QueueHold.caller_number == caller_number,
            QueueHold.status == ACTIVE_STATUS,
        )
        .first()
    )
    if existing:
        return existing, False

    hold = QueueHold(
        business_id=business_id,
        caller_number=caller_number,
        position=next_position(db, business_id),
        status=ACTIVE_STATUS,
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold, True
