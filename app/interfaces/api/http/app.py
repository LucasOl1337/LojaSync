from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bootstrap.wiring.container import build_container
from app.interfaces.api.http.routes import router
from app.shared.logging.setup import configure_logging
from app.shared.ui_events import UiEventBroker, configure_ui_event_broker


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
    app.state.container = container
    app.state.ui_event_broker = configure_ui_event_broker(UiEventBroker())
    app.include_router(router)
    if container.paths.web_ts_dist_dir.exists():
        app.mount("/ts", StaticFiles(directory=str(container.paths.web_ts_dist_dir), html=True), name="static-ts")
    app.mount("/", StaticFiles(directory=str(container.paths.web_static_dir), html=True), name="static")
    return app
