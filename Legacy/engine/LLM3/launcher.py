from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .backend import router as backend_router
from .frontend import router as frontend_router


def create_app() -> FastAPI:
    app = FastAPI(title="LLM3 Chat", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(frontend_router)
    app.include_router(backend_router)
    return app


app = create_app()


def run(host: str = "127.0.0.1", port: int = 8002, *, log_level: str = "info", reload: bool = False) -> None:
    uvicorn.run(app=app, host=host, port=port, log_level=log_level, reload=reload)


def main() -> None:
    run(host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main()
