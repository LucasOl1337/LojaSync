from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bootstrap.wiring.container import build_container
from app.interfaces.api.http.routes import router
from app.shared.logging.setup import configure_logging


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
    app.include_router(router)
    app.mount("/", StaticFiles(directory=str(container["paths"].web_static_dir), html=True), name="static")
    return app
