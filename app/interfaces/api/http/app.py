from __future__ import annotations

import logging
import os
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap.wiring.container import build_container
from app.interfaces.api.http.routes import router
from app.shared.logging.setup import configure_logging, log_event
from app.shared.ui_events import UiEventBroker, configure_ui_event_broker

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "x-request-id"

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


def _request_id(request: Request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER)
    return supplied.strip() if supplied and supplied.strip() else uuid.uuid4().hex


def _should_log_request(path: str) -> bool:
    return path.startswith(API_CACHELESS_PREFIXES)


def _http_log_level(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


def _coerce_int(value: object, fallback: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _format_origin_host(host: str) -> str:
    normalized = str(host or "").strip()
    if ":" in normalized and not normalized.startswith("["):
        return f"[{normalized}]"
    return normalized


def _cors_origins(container: object) -> list[str]:
    configured = [
        origin.strip()
        for origin in os.getenv("LOJASYNC_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if configured:
        return configured

    settings = getattr(container, "settings", None)
    api_host = str(getattr(settings, "api_host", os.getenv("LOJASYNC_HOST", "127.0.0.1")) or "127.0.0.1")
    auth_host = str(getattr(settings, "auth_host", os.getenv("LOJASYNC_AUTH_HOST", "127.0.0.1")) or "127.0.0.1")
    api_port = _coerce_int(getattr(settings, "api_port", os.getenv("LOJASYNC_BACKEND_PORT", "8800")), 8800)
    auth_port = _coerce_int(getattr(settings, "auth_port", os.getenv("LOJASYNC_AUTH_PORT", "8810")), 8810)
    frontend_port = _coerce_int(os.getenv("LOJASYNC_FRONTEND_PORT", "5173"), 5173)

    hosts = {"127.0.0.1", "localhost"}
    for host in (api_host, auth_host):
        if host and host not in {"0.0.0.0", "::"}:
            hosts.add(host)

    ports = {api_port, auth_port, frontend_port}
    return sorted({f"http://{_format_origin_host(host)}:{port}" for host in hosts for port in ports})


def create_app() -> FastAPI:
    configure_logging()
    container = build_container()
    app = FastAPI(title="LojaSync", version="1.2.8")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(container),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_cache_and_auth(request: Request, call_next):
        path = request.url.path
        method = request.method
        request_id = _request_id(request)
        request.state.request_id = request_id
        started_at = time.perf_counter()
        auth_reason: str | None = None

        def finalize_response(response):
            response.headers[REQUEST_ID_HEADER] = request_id
            if path.startswith(API_CACHELESS_PREFIXES):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            if _should_log_request(path):
                status_code = int(getattr(response, "status_code", 0) or 0)
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                fields = {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
                if auth_reason:
                    fields["auth_reason"] = auth_reason
                log_event(
                    logger,
                    _http_log_level(status_code),
                    "http_request_completed",
                    "http request completed",
                    **fields,
                )
            return response

        try:
            if path.startswith(PROTECTED_API_PREFIXES):
                auth_connector = request.app.state.container.auth_connector
                auth_status = await auth_connector.get_status()
                if not auth_status.enabled:
                    return finalize_response(await call_next(request))
                token = request.cookies.get(auth_connector.cookie_name)
                identity = await auth_connector.validate_session_token(token)
                if auth_status.bootstrap_required:
                    auth_reason = "setup_required"
                    response = JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Configure a senha inicial antes de usar o sistema.",
                            "code": auth_reason,
                        },
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "auth_request_blocked",
                        "auth request blocked",
                        request_id=request_id,
                        method=method,
                        path=path,
                        status_code=403,
                        auth_reason=auth_reason,
                    )
                    return finalize_response(response)
                if not identity.authenticated:
                    auth_reason = "auth_required"
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "Sessao invalida ou expirada.", "code": auth_reason},
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "auth_request_blocked",
                        "auth request blocked",
                        request_id=request_id,
                        method=method,
                        path=path,
                        status_code=401,
                        auth_reason=auth_reason,
                    )
                    return finalize_response(response)
                request.state.auth_identity = identity
            return finalize_response(await call_next(request))
        except Exception as exc:
            if _should_log_request(path):
                log_event(
                    logger,
                    logging.ERROR,
                    "http_request_failed",
                    "http request failed",
                    request_id=request_id,
                    method=method,
                    path=path,
                    duration_ms=int((time.perf_counter() - started_at) * 1000),
                    exception_type=type(exc).__name__,
                )
            raise

    app.state.container = container
    app.state.ui_event_broker = configure_ui_event_broker(UiEventBroker())

    # ------------------------------------------------------------------
    # Health check endpoint
    # ------------------------------------------------------------------
    import time as _time

    @app.get("/health", tags=["ops"])
    async def health_check():
        return {
            "status": "ok",
            "version": "1.2.8",
            "timestamp": _time.time(),
        }

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
