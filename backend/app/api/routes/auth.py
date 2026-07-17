"""Auth routes backed by Supabase Auth.

- /signup creates the whole tenant in one call: business + Supabase Auth
  user (with app_metadata.business_id stamped so RLS works) + mirror row
  in public.users.
- /register adds the first user to an EXISTING business (bootstrap rule
  preserved from the previous auth system).
- /login proxies Supabase Auth's password grant and returns its JWT —
  the frontend keeps sending the same Bearer header as before.
"""
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.deps import AuthContext, get_auth
from app.config import settings
from app.db import repos
from app.db.client import service_client

router = APIRouter()


class SignupRequest(BaseModel):
    business_name: str
    phone_number: str
    business_type: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class RegisterRequest(BaseModel):
    business_id: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    business_id: str
    email: str
    full_name: Optional[str] = None
    role: str


def _auth_base() -> str:
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase auth is not configured")
    return settings.SUPABASE_URL.rstrip("/") + "/auth/v1"


async def _admin_create_auth_user(email: str, password: str, business_id: str) -> dict:
    """Create a Supabase Auth user with the tenant claim RLS keys off."""
    async with httpx.AsyncClient(timeout=10) as http:
        res = await http.post(
            f"{_auth_base()}/admin/users",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            },
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "app_metadata": {"business_id": business_id},
            },
        )
    if res.status_code == 422 and "already" in res.text.lower():
        raise HTTPException(status_code=400, detail="Email already registered")
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail="Auth provider rejected the signup")
    return res.json()


async def _password_grant(email: str, password: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        res = await http.post(
            f"{_auth_base()}/token?grant_type=password",
            headers={"apikey": settings.SUPABASE_ANON_KEY or ""},
            json={"email": email, "password": password},
        )
    if res.status_code >= 400:
        # Same error for unknown email and wrong password — don't leak which
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return res.json()


async def _create_user_for_business(
    business_id: str, email: str, password: str, full_name: Optional[str], role: str
) -> str:
    auth_user = await _admin_create_auth_user(email, password, business_id)
    db = service_client()
    await repos.create_user_mirror(
        db,
        {
            "id": auth_user["id"],  # same id as auth.users
            "business_id": business_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            # Passwords live in Supabase Auth now; column kept non-null
            # in the schema, so store an explicit marker.
            "hashed_password": "supabase-auth",
        },
    )
    return auth_user["id"]


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(req: SignupRequest):
    """Create a new tenant: business + its first (admin) user."""
    db = service_client()
    if await repos.get_business_by_phone(db, req.phone_number):
        raise HTTPException(status_code=400, detail="A business with this phone number already exists")

    business = await repos.create_business(
        db,
        {
            "name": req.business_name,
            "phone_number": req.phone_number,
            "business_type": req.business_type,
        },
    )
    await _create_user_for_business(business["id"], req.email, req.password, req.full_name, "admin")
    session = await _password_grant(req.email, req.password)
    return TokenResponse(access_token=session["access_token"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest):
    """Register a user for an existing business.

    Bootstrap rule: only the FIRST user of a business can self-register
    (that's how a tenant created out-of-band gets its admin). Adding
    further users is a follow-up admin feature.
    """
    db = service_client()
    business = await repos.get_business_by_id(db, req.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if await repos.count_users_for_business(db, req.business_id) > 0:
        raise HTTPException(
            status_code=403,
            detail="This business already has users. An existing user must add you.",
        )

    await _create_user_for_business(req.business_id, req.email, req.password, req.full_name, "admin")
    session = await _password_grant(req.email, req.password)
    return TokenResponse(access_token=session["access_token"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    session = await _password_grant(req.email, req.password)
    return TokenResponse(access_token=session["access_token"])


@router.get("/me", response_model=UserResponse)
async def me(auth: Optional[AuthContext] = Depends(get_auth)):
    if auth is None:
        raise HTTPException(status_code=401, detail="Auth is disabled (AUTH_ENABLED=false)")
    user = await repos.get_user_by_id(service_client(), auth.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User record not found")
    return UserResponse(**{k: user[k] for k in ("id", "business_id", "email", "full_name", "role")})
