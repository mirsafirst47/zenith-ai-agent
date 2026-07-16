"""Password hashing and JWT creation/validation.

Uses bcrypt directly rather than passlib — passlib 1.7.4 is unmaintained
and crashes against bcrypt >= 4.1 during its backend detection.
"""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import jwt, JWTError

from app.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt only reads the first 72 bytes; truncate explicitly so long
    # passphrases hash deterministically instead of raising.
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str, business_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "business_id": business_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Returns the payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
