"""Session-based auth using signed cookies + DB-backed users with role-based permissions."""

import hashlib
import hmac
import secrets
import os
from datetime import timedelta
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User

# Config — override via env vars
SECRET_KEY = os.environ.get("SECRET_KEY", "kh07-welfare-secret-key-change-me")
SESSION_COOKIE = "kh07_session"
SESSION_MAX_AGE = timedelta(hours=int(os.environ.get("SESSION_HOURS", "24")))

# ── Role definitions ──
# Permission format: "resource" = full access, "resource:read" = read-only
ROLES = {
    "admin": {
        "members", "causes", "contributions", "disbursements",
        "mpesa", "users", "reports", "activity_log", "backup",
    },
    "treasurer": {
        "contributions", "disbursements", "mpesa",
        "members:read", "causes:read", "users:read",
        "reports",
    },
    "secretary": {
        "members", "causes",
        "contributions:read", "disbursements:read",
        "users:read", "reports",
    },
    "viewer": {
        "members:read", "causes:read", "contributions:read", "disbursements:read",
        "mpesa:read", "reports",
    },
}

ROLE_LABELS = {
    "admin": "Administrator",
    "treasurer": "Treasurer",
    "secretary": "Secretary",
    "viewer": "Viewer",
}

VALID_ROLES = set(ROLES.keys())


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    if role not in ROLES:
        return False
    perms = ROLES[role]
    if permission in perms:
        return True
    # Full access (e.g. "members") implies sub-permissions (e.g. "members:read")
    resource = permission.split(":")[0]
    return resource in perms


def require_permission(*permissions: str):
    """FastAPI dependency: require ALL specified permissions.

    Usage:
        @app.post("/alumni/register")
        async def create_member(..., user: User = Depends(require_permission("members"))):
            ...
    """
    async def _check(request: Request, db: AsyncSession = Depends(get_db)) -> User:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        for perm in permissions:
            if not has_permission(user.role, perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{ROLE_LABELS.get(user.role, user.role)}' does not have permission: {perm}",
                )
        return user
    return _check


def _sign(data: str) -> str:
    return hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()


def _encode_session(username: str, role: str = "admin") -> str:
    nonce = secrets.token_hex(16)
    payload = f"{nonce}.{username}.{role}"
    sig = _sign(payload)
    return f"{payload}.{sig}"


def _decode_session(token: str) -> tuple | None:
    """Returns (username, role) or None."""
    parts = token.split(".")
    if len(parts) != 4:
        return None
    payload = f"{parts[0]}.{parts[1]}.{parts[2]}"
    expected_sig = _sign(payload)
    if not hmac.compare_digest(parts[3], expected_sig):
        return None
    return parts[1], parts[2]


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000)
    return f"pbkdf2:sha256:600000:{salt}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash. Supports legacy SHA-256 for migration."""
    if stored_hash.startswith("pbkdf2:"):
        parts = stored_hash.split(":")
        if len(parts) == 5 and parts[1] == "sha256":
            salt = parts[3]
            iterations = int(parts[2])
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
            return hmac.compare_digest(dk.hex(), parts[4])
        return False
    # Legacy SHA-256 fallback for existing users
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored_hash)


def create_session(username: str, role: str = "admin") -> str:
    return _encode_session(username, role)


def get_session_user(request: Request) -> str | None:
    """Get the authenticated username from the signed cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    result = _decode_session(token)
    if result:
        return result[0]
    return None


def get_session_role(request: Request) -> str | None:
    """Get the user's role from the signed cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    result = _decode_session(token)
    if result:
        return result[1]
    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get the authenticated User object from the session cookie."""
    username = get_session_user(request)
    if not username:
        return None
    result = await db.execute(select(User).where(User.username == username, User.is_active == True))
    return result.scalar_one_or_none()


async def require_auth(request: Request):
    """Dependency: redirect to login if not authenticated."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency: require admin role (legacy — use require_permission instead)."""
    user = await get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def require_viewer(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency: require any authenticated user."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def maybe_user(request: Request) -> str | None:
    return get_session_user(request)
