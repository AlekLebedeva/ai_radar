"""
AI Radar — Admin Authentication
Stateless signed cookie auth.
"""

import hmac
import hashlib
import secrets
from datetime import datetime

from fastapi import Request, HTTPException, status

from config import get_settings

settings = get_settings()

ADMIN_COOKIE = "ai_radar_admin_session"
SESSION_TTL = 86400  # 24 часа


def _hash(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def _verify(plain: str, hashed: str) -> bool:
    return secrets.compare_digest(_hash(plain), hashed)


def _secret() -> str:
    return f"{settings.admin_username}:{settings.admin_password}"


def _sign(data: str) -> str:
    return hmac.new(
        _secret().encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()


def create_session() -> str:
    expires = int(datetime.utcnow().timestamp()) + SESSION_TTL

    payload = str(expires)

    signature = _sign(payload)

    return f"{payload}.{signature}"


def verify_session(request: Request) -> str:
    token = request.cookies.get(ADMIN_COOKIE)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload, signature = token.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    expected = _sign(payload)

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session signature",
        )

    expires = int(payload)

    if datetime.utcnow().timestamp() > expires:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    return token


def destroy_session(request: Request):
    """
    Stateless auth.
    Ничего удалять на сервере не нужно.
    """
    return


async def get_current_admin(request: Request) -> str:
    verify_session(request)
    return settings.admin_username