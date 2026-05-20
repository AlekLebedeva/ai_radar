#!/usr/bin/env python3
"""
AI Radar — Main Application Entry Point
"""

import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from admin.router import router as admin_router
from admin.auth import verify_session, ADMIN_COOKIE
from database.base import Base
from database.session import get_engine_for_lifespan, is_postgres


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create engine inside lifespan (not at import)."""
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
#  Admin Auth Middleware
# ═══════════════════════════════════════════════════════
class AdminAuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = ["/admin/login", "/admin/login.html", "/admin/static/"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/admin"):
            return await call_next(request)

        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        is_api = (
            request.headers.get("accept", "").startswith("application/json")
            or request.headers.get("x-requested-with") == "XMLHttpRequest"
        )

        try:
            verify_session(request)
        except Exception:
            if is_api:
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return RedirectResponse(url="/admin/login", status_code=303)

        return await call_next(request)


app.add_middleware(AdminAuthMiddleware)


app.mount("/app/static", StaticFiles(directory="static/app/static"), name="app_static")
app.mount("/admin/static", StaticFiles(directory="static/admin/static"), name="admin_static")

@app.get("/app", response_class=FileResponse)
async def app_page():
    return FileResponse("static/app/index.html")

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    return FileResponse("static/admin/login.html")

@app.get("/admin", response_class=FileResponse)
async def admin_page(request: Request):
    try:
        verify_session(request)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=303)
    return FileResponse("static/admin/index.html")

@app.get("/app/{path:path}")
async def app_spa(path: str):
    return FileResponse("static/app/index.html")

@app.get("/admin/{path:path}")
async def admin_spa(path: str, request: Request):
    # Пропускаем login и static — они отдаются отдельно
    if path in ("login", "login.html") or path.startswith("static/"):
        return FileResponse(f"static/admin/{path}")
    try:
        verify_session(request)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=303)
    return FileResponse("static/admin/index.html")





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