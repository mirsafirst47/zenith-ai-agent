"""Model registry.

Importing every model here ensures Base.metadata knows about all tables
before main.py calls Base.metadata.create_all() — previously Booking and
User were never imported anywhere at startup, so their tables were
silently never created.
"""
from .database import Base, engine, SessionLocal, get_db
from .business import Business
from .call import Call
from .booking import Booking, BOOKING_STATUSES
from .queue_hold import QueueHold, QUEUE_HOLD_STATUSES
from .user import User

__all__ = [
    "Base", "engine", "SessionLocal", "get_db",
    "Business", "Call", "Booking", "BOOKING_STATUSES",
    "QueueHold", "QUEUE_HOLD_STATUSES", "User",
]
