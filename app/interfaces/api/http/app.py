from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap.wiring.container import build_container
from app.interfaces.api.http.routes import router
from app.shared.logging.setup import configure_logging
from app.shared.ui_events import UiEventBroker, configure_ui_event_broker

API_CACHELESS_PREFIXES = (
    "/health",
    "/auth",
    "/products",
    "/totals",
    "/brands",
    "/settings",
    "/automation",
    "/actions",
    "/catalog",
)

PROTECTED_API_PREFIXES = (
    "/products",
    "/totals",
    "/brands",
    "/settings",
    "/automation",
    "/actions",
    "/catalog",
)


def create_app() -> FastAPI:
    configure_logging()
    container = build_container()
    app = FastAPI(title="LojaSync", version="1.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def disable_api_cache(request: Request, call_next):
        if request.url.path.startswith(PROTECTED_API_PREFIXES):
            auth_connector = request.app.state.container.auth_connector
            auth_status = await auth_connector.get_status()
            if not auth_status.enabled:
                response = await call_next(request)
                if request.url.path.startswith(API_CACHELESS_PREFIXES):
                    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                    response.headers["Pragma"] = "no-cache"
                    response.headers["Expires"] = "0"
                return response
            token = request.cookies.get(auth_connector.cookie_name)
            identity = await auth_connector.validate_session_token(token)
            if auth_status.bootstrap_required:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Configure a senha inicial antes de usar o sistema.", "code": "setup_required"},
                )
            if not identity.authenticated:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Sessao invalida ou expirada.", "code": "auth_required"},
                )
            request.state.auth_identity = identity
        response = await call_next(request)
        if request.url.path.startswith(API_CACHELESS_PREFIXES):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.state.container = container
    app.state.ui_event_broker = configure_ui_event_broker(UiEventBroker())
    app.include_router(router)

    @app.get("/ts", include_in_schema=False)
    @app.get("/ts/{path:path}", include_in_schema=False)
    def redirect_ts_to_root(path: str = "") -> RedirectResponse:
        return RedirectResponse(url="/", status_code=307)

    primary_static_dir = (
        container.paths.web_ts_dist_dir if container.paths.web_ts_dist_dir.exists() else container.paths.web_static_dir
    )
    if primary_static_dir != container.paths.web_static_dir and container.paths.web_static_dir.exists():
        app.mount("/legacy", StaticFiles(directory=str(container.paths.web_static_dir), html=True), name="static-legacy")
    app.mount("/", StaticFiles(directory=str(primary_static_dir), html=True), name="static")
    return app
