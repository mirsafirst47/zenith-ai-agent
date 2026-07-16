"""Shared API dependencies: authentication and tenant scoping"""
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.models.database import get_db
from app.models.user import User

# auto_error=False so we can produce our own 401 (and support AUTH_ENABLED=false)
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Resolve the authenticated user from a Bearer token.

    With AUTH_ENABLED=false (local dev), returns None and endpoints fall
    back to their unscoped behavior. With auth on, a missing/invalid
    token is a 401.
    """
    if not settings.AUTH_ENABLED:
        return None

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def scoped_business_id(
    business_id: Optional[str],
    user: Optional[User],
) -> Optional[str]:
    """Resolve which business a request may operate on.

    - Auth enforced: always the user's own business. A mismatched
      explicit business_id is a 403 (one tenant cannot read another).
    - Auth disabled (dev): pass the query param through unchanged.
    """
    if user is None:  # AUTH_ENABLED=false
        return business_id
    if business_id and business_id != user.business_id:
        raise HTTPException(status_code=403, detail="Not authorized for this business")
    return user.business_id


def assert_tenant(obj_business_id: Optional[str], user: Optional[User]) -> None:
    """Guard a fetched row: 404 if it belongs to another tenant.

    404 rather than 403 so we don't confirm the resource exists in a
    different tenant. No-op when auth is disabled.
    """
    if user is not None and obj_business_id != user.business_id:
        raise HTTPException(status_code=404, detail="Not found")
