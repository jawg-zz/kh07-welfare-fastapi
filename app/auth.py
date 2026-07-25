"""Session-based auth using signed cookies + DB-backed users with roles."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User

# Change this in production!
SECRET_KEY = "kh07-welfare-secret-key-change-me"

SESSION_COOKIE = "kh07_session"
SESSION_MAX_AGE = timedelta(hours=24)


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
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, expected_hash: str) -> bool:
    """Verify password against stored hash."""
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), expected_hash)

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


async def get_current_user_sync(request: Request) -> User | None:
    """Non-DB version — just returns the username string for backward compat."""
    username = get_session_user(request)
    if not username:
        return None
    # Return a lightweight object
    return type("User", (), {"username": username, "role": "admin"})()


async def require_auth(request: Request):
    """Dependency: redirect to login if not authenticated."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency: require admin role."""
    user = await get_current_user(request, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def require_viewer(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency: require any authenticated user (viewer or admin)."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def maybe_user(request: Request) -> str | None:
    return get_session_user(request)
