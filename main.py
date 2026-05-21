#!/usr/bin/env python3
"""
AI Radar — Main Application Entry Point
"""

import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

from admin.router import router as admin_router
from admin.auth import verify_session
from database.base import Base
from database.session import get_engine_for_lifespan, is_postgres


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine_for_lifespan()
    if is_postgres():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Radar",
    description="Automated AI innovation monitoring system",
    version="1.0.0",
    #lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════
#  Admin Auth Middleware — перехватывает ВСЕ /admin запросы
#  до попадания в роуты. Работает для static тоже.
# ═══════════════════════════════════════════════════════
class AdminAuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {"/admin/login", "/admin/login.html", "/admin/static/"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Не /admin — пропускаем
        if not path.startswith("/admin"):
            return await call_next(request)

        # Публичные пути — пропускаем
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        # Проверяем сессию
        try:
            verify_session(request)
        except Exception:
            # API запросы — 401, HTML — редирект
            is_api = (
                request.headers.get("accept", "").startswith("application/json")
                or request.headers.get("x-requested-with") == "XMLHttpRequest"
            )
            if is_api:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return RedirectResponse(url="/admin/login", status_code=303)

        return await call_next(request)


# Middleware ДО static mounts и роутов
app.add_middleware(AdminAuthMiddleware)


# ═══════════════════════════════════════════════════════
#  Static files — после middleware!
# ═══════════════════════════════════════════════════════
app.mount("/app/static", StaticFiles(directory="static/app/static"), name="app_static")

# Admin static — через кастомный handler с проверкой
class ProtectedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        request = Request(scope)
        # Проверяем сессию для всего кроме login страницы
        if not path.startswith("login") and not path.startswith("js/login"):
            try:
                verify_session(request)
            except Exception:
                return RedirectResponse(url="/admin/login", status_code=303)
        return await super().get_response(path, scope)

app.mount("/admin/static", ProtectedStaticFiles(directory="static/admin/static"), name="admin_static")


# ═══════════════════════════════════════════════════════
#  Favicon
# ═══════════════════════════════════════════════════════
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")


# ═══════════════════════════════════════════════════════
#  App pages (public)
# ═══════════════════════════════════════════════════════
@app.get("/app", response_class=FileResponse)
async def app_page():
    return FileResponse("static/app/index.html")

@app.get("/app/{path:path}")
async def app_spa(path: str):
    return FileResponse("static/app/index.html")


# ═══════════════════════════════════════════════════════
#  Admin login page (public)
# ═══════════════════════════════════════════════════════
@app.get("/admin/login")
async def admin_login_page():
    return FileResponse("static/admin/login.html")


# ═══════════════════════════════════════════════════════
#  Admin SPA — middleware уже проверил сессию,
#  здесь просто отдаём HTML
# ═══════════════════════════════════════════════════════
@app.get("/admin")
@app.get("/admin/{path:path}")
async def admin_spa(request: Request, path: str = ""):
    # Middleware уже проверил сессию, но на всякий случай
    try:
        verify_session(request)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=303)
    return FileResponse("static/admin/index.html")


# ═══════════════════════════════════════════════════════
#  API routes
# ═══════════════════════════════════════════════════════
app.include_router(admin_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/app", status_code=302)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-radar",
        "version": "1.0.0",
        "database": "postgresql" if is_postgres() else "sqlite (demo)",
    }


if __name__ == "__main__":
    print("=" * 55)
    print("  AI RADAR — Starting Server")
    print("=" * 55)
    print("URLs:")
    print("Main app:   http://localhost:8000/app")
    print("Admin:      http://localhost:8000/admin")
    print("API Docs:   http://localhost:8000/docs")
    print("Health:     http://localhost:8000/health")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )