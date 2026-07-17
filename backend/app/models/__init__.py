"""Shared domain constants.

The SQLAlchemy ORM is gone — the schema now lives in
supabase/migrations/*.sql and data access in app.db.repos. This package
keeps the status vocabularies that used to live on the models.
"""
from app.db.repos import BOOKING_STATUSES, QUEUE_HOLD_STATUSES  # noqa: F401
