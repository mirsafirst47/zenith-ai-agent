"""Shared API dependencies: Supabase Auth verification and tenant scoping"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from postgrest import AsyncPostgrestClient

from app.config import settings
from app.db.client import user_client, service_client

# auto_error=False so we can produce our own 401 (and support AUTH_ENABLED=false)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """Verified identity of the dashboard caller."""
    user_id: str
    business_id: str
    email: Optional[str]
    token: str  # raw JWT — forwarded to PostgREST so RLS applies


def _decode_supabase_jwt(token: str) -> Optional[dict]:
    if not settings.SUPABASE_JWT_SECRET:
        return None
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        return None


def get_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[AuthContext]:
    """Resolve the authenticated user from a Supabase Auth Bearer token.

    The tenant comes from the app_metadata.business_id claim — the same
    claim the database RLS policies key off, so the API and the database
    always agree on who the caller is.

    With AUTH_ENABLED=false (local dev) returns None and endpoints fall
    back to unscoped behavior.
    """
    if not settings.AUTH_ENABLED:
        return None

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = _decode_supabase_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    business_id = (payload.get("app_metadata") or {}).get("business_id")
    if not business_id:
        # A Supabase user that was never onboarded to a tenant
        raise HTTPException(status_code=403, detail="Account is not linked to a business")

    return AuthContext(
        user_id=payload.get("sub"),
        business_id=business_id,
        email=payload.get("email"),
        token=credentials.credentials,
    )


def get_db(auth: Optional[AuthContext] = Depends(get_auth)) -> AsyncPostgrestClient:
    """Tenant-scoped database access for dashboard routes.

    Auth on: the caller's own JWT is forwarded, so Postgres RLS enforces
    isolation even if a route handler forgets an app-level check.
    Auth off (dev): service client, unscoped.
    """
    if auth is None:
        return service_client()
    return user_client(auth.token)


def scoped_business_id(business_id: Optional[str], auth: Optional[AuthContext]) -> Optional[str]:
    """Resolve which business a request may operate on.

    - Auth enforced: always the caller's own business. A mismatched
      explicit business_id is a 403 (one tenant cannot read another).
    - Auth disabled (dev): pass the query param through unchanged.
    """
    if auth is None:
        return business_id
    if business_id and business_id != auth.business_id:
        raise HTTPException(status_code=403, detail="Not authorized for this business")
    return auth.business_id


def assert_tenant(obj_business_id: Optional[str], auth: Optional[AuthContext]) -> None:
    """Guard a fetched row: 404 if it belongs to another tenant.

    404 rather than 403 so we don't confirm the resource exists in a
    different tenant. No-op when auth is disabled. (Defense in depth —
    RLS already prevents the row from being returned at all.)
    """
    if auth is not None and obj_business_id != auth.business_id:
        raise HTTPException(status_code=404, detail="Not found")
