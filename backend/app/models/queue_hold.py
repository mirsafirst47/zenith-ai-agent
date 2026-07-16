"""QueueHold model — holds a caller's place in line so they can be
texted their status instead of staying on hold."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from datetime import datetime
import uuid
from .database import Base

QUEUE_HOLD_STATUSES = ("waiting", "notified", "expired", "cancelled", "served")


class QueueHold(Base):
    __tablename__ = "queue_holds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String(36), ForeignKey("businesses.id"), nullable=False)
    caller_number = Column(String(20), nullable=False)
    # Place in line for this business; lowest = next. Only meaningful
    # while status = waiting.
    position = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="waiting")
    # When the "it's your turn" SMS went out. Null until then.
    notified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
