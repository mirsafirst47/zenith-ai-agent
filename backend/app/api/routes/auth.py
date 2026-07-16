"""Auth routes: register, login, me"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.database import get_db
from app.models.business import Business
from app.models.user import User

router = APIRouter()


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

    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a user for a business.

    Bootstrap rule: only the FIRST user of a business can self-register
    (that's how a new tenant gets its admin). Adding further users to a
    business is a follow-up admin feature.
    """
    business = db.query(Business).filter(Business.id == req.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_users = db.query(User).filter(User.business_id == req.business_id).count()
    if existing_users > 0:
        raise HTTPException(
            status_code=403,
            detail="This business already has users. An existing user must add you.",
        )

    user = User(
        business_id=req.business_id,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="admin",  # first user is the tenant admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id, user.business_id))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    # Same error for unknown email and wrong password — don't leak which
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    return TokenResponse(access_token=create_access_token(user.id, user.business_id))


@router.get("/me", response_model=UserResponse)
def me(current_user: Optional[User] = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Auth is disabled (AUTH_ENABLED=false)")
    return current_user
