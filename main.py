#!/usr/bin/env python3
"""
AI Radar — Main Application Entry Point
"""

import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse

from admin.router import router as admin_router
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT: Mount static files FIRST (without html=True)
# Then mount html pages. Order matters!
app.mount("/app/static", StaticFiles(directory="static/app/static"), name="app_static")
app.mount("/admin/static", StaticFiles(directory="static/admin/static"), name="admin_static")

# HTML pages served via FileResponse (not mount with html=True)
@app.get("/app", response_class=FileResponse)
async def app_page():
    return FileResponse("static/app/index.html")

@app.get("/admin", response_class=FileResponse)
async def admin_page():
    return FileResponse("static/admin/index.html")

# Also serve index.html for subpaths (SPA routing)
@app.get("/app/{path:path}")
async def app_spa(path: str):
    return FileResponse("static/app/index.html")

@app.get("/admin/{path:path}")
async def admin_spa(path: str):
    return FileResponse("static/admin/index.html")

# API routes
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
