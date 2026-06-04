from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from admin.auth import verify_session


class AdminAuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {"/admin/login", "/admin/login.html", "/admin/static/"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/admin"):
            return await call_next(request)

        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        try:
            verify_session(request)
        except Exception:
            is_api = (
                request.headers.get("accept", "").startswith("application/json")
                or request.headers.get("x-requested-with") == "XMLHttpRequest"
            )
            if is_api:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return RedirectResponse(url="/admin/login", status_code=303)

        return await call_next(request)


class ProtectedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        request = Request(scope)
        if not path.startswith("login") and not path.startswith("js/login"):
            try:
                verify_session(request)
            except Exception:
                return RedirectResponse(url="/admin/login", status_code=303)
        return await super().get_response(path, scope)
