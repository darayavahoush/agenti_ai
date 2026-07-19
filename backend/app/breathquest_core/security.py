from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.breathquest_core.config import get_breathquest_settings

settings = get_breathquest_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------ #
#  Password helpers (therapists)                                       #
# ------------------------------------------------------------------ #

def hash_password(password: str) -> str:
    # Use SHA-256 for password hashing to avoid bcrypt limitations
    # Add salt for security
    salt = secrets.token_hex(16)
    salted_password = password + salt
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(plain: str, hashed: str) -> bool:
    # Verify SHA-256 hashed password with salt
    try:
        salt, stored_hash = hashed.split('$')
        salted_password = plain + salt
        computed_hash = hashlib.sha256(salted_password.encode()).hexdigest()
        return computed_hash == stored_hash
    except:
        # Fallback to bcrypt for existing passwords
        try:
            return pwd_context.verify(plain, hashed)
        except:
            return False


# ------------------------------------------------------------------ #
#  JWT (therapists)                                                    #
# ------------------------------------------------------------------ #

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "therapist"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ------------------------------------------------------------------ #
#  PIN tokens (kids)                                                   #
# ------------------------------------------------------------------ #

def hash_pin(pin: str) -> str:
    """Store PINs as SHA-256 (not bcrypt — PINs are short and already validated)."""
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(plain: str, hashed: str) -> bool:
    return hash_pin(plain) == hashed


def create_kid_token(patient_id: str) -> str:
    """Long-lived simple token for kid sessions."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.KID_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(patient_id), "exp": expire, "type": "patient"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_kid_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "patient":
            return None
        return payload
    except JWTError:
        return None
