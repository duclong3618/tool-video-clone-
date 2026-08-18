# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
JWT Authentication & Authorization for multi-user support.

Provides:
- User registration & login
- JWT token generation & validation
- Role-based access control (admin, user)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class AuthError(Exception):
    pass


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password with salt using SHA-256."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    )
    return hashed.hex(), salt


def _verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against hash."""
    computed, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed, hashed)


def create_token(user_id: str, role: str, expires_hours: int = 24) -> str:
    """Create a simple JWT-like token."""
    settings = get_settings()
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int(time.time()) + (expires_hours * 3600),
        "iat": int(time.time()),
    }
    # Simple encoding (for production, use PyJWT)
    data = json.dumps(payload)
    signature = hmac.new(
        settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256
    ).hexdigest()
    encoded = __import__("base64").b64encode(data.encode()).decode()
    return f"{encoded}.{signature}"


def verify_token(token: str) -> dict | None:
    """Verify and decode a token."""
    settings = get_settings()
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        encoded_data, signature = parts
        data = __import__("base64").b64decode(encoded_data.encode()).decode()
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        payload = json.loads(data)
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


# ── Dependency for FastAPI ───────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict | None:
    """Extract and validate user from JWT token. Returns None for unauthenticated."""
    if credentials is None:
        return None

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


async def require_auth(
    user: dict | None = Depends(get_current_user),
) -> dict:
    """Require authentication."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


async def require_admin(
    user: dict = Depends(require_auth),
) -> dict:
    """Require admin role."""
    if user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ── Simple in-memory user store (for MVP) ────────────────
# In production, use database

_users: dict[str, dict] = {}


def register_user(username: str, password: str, role: str = "user") -> dict:
    """Register a new user."""
    if username in _users:
        raise AuthError("Username already exists")

    hashed, salt = _hash_password(password)
    user = {
        "user_id": username,
        "username": username,
        "password_hash": hashed,
        "salt": salt,
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
    }
    _users[username] = user
    return {"user_id": username, "username": username, "role": role}


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user credentials."""
    user = _users.get(username)
    if not user:
        return None
    if not _verify_password(password, user["password_hash"], user["salt"]):
        return None
    return {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}
