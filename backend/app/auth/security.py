"""
Security utilities for password hashing, password validation, and JWT token management.
Uses native bcrypt library with fallback for maximum forward-compatibility and work factor 12.
"""
import os
import re
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Set
from jose import JWTError, jwt

# In-memory revocation set for blacklisted tokens
_REVOKED_TOKENS: Set[str] = set()

# JWT configuration from environment
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-secure-random-secret-key-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ALLOWED_ALGORITHMS = [ALGORITHM] if ALGORITHM else ["HS256"]

# Strict token expiration limits:
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


def validate_password_complexity(password: str) -> None:
    """
    Enforces production password policy:
    - Minimum 8 characters
    - At least one uppercase letter [A-Z]
    - At least one lowercase letter [a-z]
    - At least one digit [0-9]
    - At least one special character [!@#$%^&*(),.?":{}|<>\-_]
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_]', password):
        raise ValueError("Password must contain at least one special character")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using native bcrypt with configured work factor (default 12)."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    Claims encoded: sub, role, org_id, type="access", exp, iat
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed long-lived refresh token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def revoke_token(token: str) -> None:
    """Revoke a token immediately."""
    _REVOKED_TOKENS.add(token)


def is_token_revoked(token: str) -> bool:
    """Check if token has been revoked."""
    return token in _REVOKED_TOKENS


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Enforces algorithm pinning, expiration validation, and revocation check.
    """
    if is_token_revoked(token):
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=ALLOWED_ALGORITHMS,
            options={"verify_exp": True, "verify_iat": True}
        )
        return payload
    except JWTError:
        return None
