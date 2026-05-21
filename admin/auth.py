"""
AI Radar — Admin Authentication
Cookie-session для UI + API. Без Basic Auth.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status

from config import get_settings

settings = get_settings()

_sessions: dict[str, datetime] = {}

SESSION_TTL = 86400  # 24 часа

def _hash(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def _verify(plain: str, hashed: str) -> bool:
    return secrets.compare_digest(_hash(plain), hashed)


def _token() -> str:
    return secrets.token_urlsafe(32)


ADMIN_COOKIE = "ai_radar_admin_session"


def create_session() -> str:
    token = _token()
    _sessions[token] = datetime.utcnow() + timedelta(seconds=SESSION_TTL)
    return token


def verify_session(request: Request) -> str:
    token = request.cookies.get(ADMIN_COOKIE)
    if not token or token not in _sessions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    expiry = _sessions[token]
    if datetime.utcnow() > expiry:
        del _sessions[token]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    _sessions[token] = datetime.utcnow() + timedelta(seconds=SESSION_TTL)
    return token


def destroy_session(request: Request):
    token = request.cookies.get(ADMIN_COOKIE)
    if token and token in _sessions:
        del _sessions[token]


async def get_current_admin(request: Request) -> str:
    verify_session(request)
    return settings.admin_username