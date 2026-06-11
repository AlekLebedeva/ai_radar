from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, FileResponse, PlainTextResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from admin.auth import verify_session
from database.session import is_postgres

STATIC_ROOT = Path(__file__).resolve().parent / "static"
FAVICON_PATH = STATIC_ROOT / "favicon.ico"


def register_routes(app: FastAPI) -> None:
    @app.get("/favicon.ico")
    async def favicon():
        if FAVICON_PATH.exists():
            return FileResponse(FAVICON_PATH)
        return PlainTextResponse("", status_code=204)

    @app.get("/app", response_class=FileResponse)
    async def app_page():
        return FileResponse("static/app/index.html")

    @app.get("/app/{path:path}")
    async def app_spa(path: str):
        return FileResponse("static/app/index.html")

    @app.get("/admin/login")
    async def admin_login_page():
        return FileResponse("static/admin/login.html")

    @app.get("/admin")
    @app.get("/admin/{path:path}")
    async def admin_spa(request: Request, path: str = ""):
        try:
            verify_session(request)
        except Exception:
            return RedirectResponse(url="/admin/login", status_code=303)
        return FileResponse("static/admin/index.html")

    @app.get("/")
    async def root():
        return RedirectResponse(url="/app", status_code=302)

    @app.get("/docs", include_in_schema=False)
    async def get_documentation(request: Request, _=Depends(verify_session)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title="AI Radar API")

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi(request: Request, _=Depends(verify_session)):
        return get_openapi(title=app.title, version=app.version, routes=app.routes)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "ai-radar",
            "version": "1.0.0",
            "database": "postgresql" if is_postgres() else "sqlite (demo)",
        }
