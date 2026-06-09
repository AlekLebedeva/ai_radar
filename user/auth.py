"""
AI Radar — User session (signed cookie with user_id) and Authentik integration.
"""

import hmac
import hashlib
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import httpx
from fastapi import Request, HTTPException, status

from config import get_settings, SERVICES

settings = get_settings()

USER_COOKIE = "ai_radar_user_session"
USER_SESSION_TTL = 86400 * 30  # 30 days

logger = logging.getLogger(__name__)


def _secret() -> str:
    return f"{settings.admin_username}:{settings.admin_password}:user"


def _sign(data: str) -> str:
    return hmac.new(
        _secret().encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_user_session(user_id: uuid.UUID) -> str:
    expires = int(datetime.utcnow().timestamp()) + USER_SESSION_TTL
    payload = f"{user_id}:{expires}"
    signature = _sign(payload)
    return f"{payload}.{signature}"


def verify_user_session(request: Request) -> uuid.UUID:
    token = request.cookies.get(USER_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload, signature = token.rsplit(".", 1)
        user_id_str, expires_str = payload.split(":", 1)
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

    if datetime.utcnow().timestamp() > int(expires_str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id",
        )


async def get_current_user(request: Request, http_client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    Получение текущего пользователя из Authentik header.
    Обернуто в try-catch для обработки ошибок, так как сервис может быть недоступен.
    """
    authentik_user = request.headers.get("X-Authentik-Username")
    if not authentik_user:
        return None

    logger.info(f"Authentik user: {authentik_user}")
    auth_url = SERVICES["auth"]["url"]

    try:
        response = await http_client.post(
            f"{auth_url}/authentik",
            json={"username": authentik_user},
            timeout=5.0,
        )
        if response.status_code == 200:
            data = response.json()
            user_id = data.get("user_id")
            if user_id:
                return {
                    "username": authentik_user,
                    "user_id": uuid.UUID(user_id),
                    "authenticated": True,
                }
        logger.warning(f"Auth service returned status {response.status_code}: {response.text}")
    except httpx.TimeoutException:
        logger.error("Auth service timeout")
    except httpx.RequestError as e:
        logger.error(f"Auth service unreachable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")

    return None
