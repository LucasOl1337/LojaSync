from __future__ import annotations

from fastapi import FastAPI

from app.bootstrap.wiring.auth_container import build_auth_container
from app.interfaces.auth_api.http.routes import router
from app.shared.logging.setup import configure_logging


def create_auth_app() -> FastAPI:
    configure_logging()
    container = build_auth_container()
    app = FastAPI(title="LojaSync Auth", version="1.0.0")
    app.state.container = container
    app.include_router(router)
    return app
