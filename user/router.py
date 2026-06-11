from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

import httpx

from database.session import get_db
from user.auth import (
    USER_COOKIE,
    USER_SESSION_TTL,
    create_user_session,
    verify_user_session,
    get_current_user as get_authentik_user,
)
from user.schemas import CategoryOut, InterestsUpdate, ProfileUpdate, UserOut
from user.service import CategoryService, UserService

router = APIRouter(prefix="/api/v1", tags=["user"])


def _session_response(user_out: UserOut, token: str) -> JSONResponse:
    response = JSONResponse(user_out.model_dump(mode="json"))
    response.set_cookie(
        key=USER_COOKIE,
        value=token,
        httponly=True,
        max_age=USER_SESSION_TTL,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


def _get_http_client(request: Request) -> Optional[httpx.AsyncClient]:
    return getattr(request.app.state, "http_client", None)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).list_from_data()


@router.post("/user/session", response_model=UserOut)
async def create_or_resume_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    http_client: Optional[httpx.AsyncClient] = Depends(_get_http_client),
):
    svc = UserService(db)

    if http_client:
        authentik_user = await get_authentik_user(request, http_client)
        if authentik_user and authentik_user.get("user_id"):
            user = await svc.get_or_create(authentik_user["user_id"])
            token = create_user_session(user.id)
            return _session_response(svc.to_out(user), token)

    try:
        user_id = verify_user_session(request)
        user = await svc.get_or_create(user_id)
    except Exception:
        user = await svc.get_or_create()
        token = create_user_session(user.id)
        return _session_response(svc.to_out(user), token)

    token = create_user_session(user.id)
    return _session_response(svc.to_out(user), token)


@router.get("/user/me", response_model=UserOut)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_user_session(request)
    user = await UserService(db).get_by_id(user_id)
    if user is None:
        return JSONResponse({"detail": "User not found"}, status_code=404)
    return UserService(db).to_out(user)


@router.put("/user/interests", response_model=UserOut)
async def update_user_interests(
    payload: InterestsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_user_session(request)
    user_out = await UserService(db).save_interests(user_id, payload.categories)
    return user_out


@router.put("/user/profile", response_model=UserOut)
async def update_user_profile(
    payload: ProfileUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_user_session(request)
    user_out = await UserService(db).update_profile(
        user_id,
        display_name=payload.display_name,
        email_notifications=payload.email_notifications,
        digest_frequency=payload.digest_frequency,
    )
    return user_out
