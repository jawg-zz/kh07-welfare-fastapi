"""Session-based auth using signed cookies (no server-side storage)."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import Request, HTTPException, status

# Change this in production!
SECRET_KEY = "kh07-welfare-secret-key-change-me"

SESSION_COOKIE = "kh07_session"
SESSION_MAX_AGE = timedelta(hours=24)


def _sign(data: str) -> str:
    """Create an HMAC-SHA256 signature for the data."""
    return hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()


def _encode_session(username: str) -> str:
    """Create a signed cookie value: <random>.<username>.<signature>"""
    nonce = secrets.token_hex(16)
    payload = f"{nonce}.{username}"
    sig = _sign(payload)
    return f"{payload}.{sig}"


def _decode_session(token: str) -> str | None:
    """Verify and decode a signed cookie. Returns username or None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = f"{parts[0]}.{parts[1]}"
    expected_sig = _sign(payload)
    if not hmac.compare_digest(parts[2], expected_sig):
        return None
    return parts[1]


def verify_password(password: str) -> bool:
    """Verify admin password against stored hash."""
    expected = hashlib.sha256(b"admin123").hexdigest()
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), expected)


def create_session(username: str) -> str:
    """Create a signed session token."""
    return _encode_session(username)


def get_session_user(request: Request) -> str | None:
    """Get the authenticated username from the signed cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return _decode_session(token)


async def require_auth(request: Request):
    """Dependency: redirect to login if not authenticated."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


async def maybe_user(request: Request) -> str | None:
    """Optional auth check - returns user or None."""
    return get_session_user(request)


def logout_session(request: Request):
    """No server-side session to clear — cookie deletion is handled by the response."""
    pass
