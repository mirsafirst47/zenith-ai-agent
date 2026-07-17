"""Supabase data layer — PostgREST client factories.

Two access paths, mirroring Supabase's own model:

- service_client(): authenticated with the service-role key. Bypasses RLS.
  Used by the voice pipeline (callers on the phone aren't authenticated
  Supabase users) and by trusted admin operations like tenant signup.

- user_client(jwt): authenticated with the *end user's* Supabase Auth JWT.
  RLS enforces tenant isolation at the database — the API code no longer
  has to be the only line of defense.

POSTGREST_URL lets local tests point at a plain PostgREST instance; in
production it's derived from SUPABASE_URL (Supabase serves PostgREST at
/rest/v1).
"""
from postgrest import AsyncPostgrestClient

from app.config import settings


def rest_base_url() -> str:
    if settings.POSTGREST_URL:
        return settings.POSTGREST_URL.rstrip("/")
    if settings.SUPABASE_URL:
        return settings.SUPABASE_URL.rstrip("/") + "/rest/v1"
    raise RuntimeError(
        "No database configured: set SUPABASE_URL (and keys) in backend/.env, "
        "or POSTGREST_URL for a local PostgREST instance."
    )


def _client(bearer: str, apikey: str) -> AsyncPostgrestClient:
    return AsyncPostgrestClient(
        rest_base_url(),
        headers={
            "apikey": apikey,
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )


def service_client() -> AsyncPostgrestClient:
    """RLS-bypassing client for the voice pipeline / admin operations."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set")
    return _client(bearer=key, apikey=key)


def user_client(user_jwt: str) -> AsyncPostgrestClient:
    """Per-request client carrying the caller's own JWT — RLS applies."""
    apikey = settings.SUPABASE_ANON_KEY or user_jwt
    return _client(bearer=user_jwt, apikey=apikey)
