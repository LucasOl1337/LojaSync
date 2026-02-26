"""Servidor frontend simplificado para o protótipo LojaSync.

Quando o ``launcher.py`` localizar este módulo, chamará ``run(host, port)`` para
inicializar a camada de frontend. Aqui usamos ``uvicorn`` servindo um FastAPI
com rota raiz devolvendo o ``index.html`` estático (e arquivos estáticos
associados).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR

app = FastAPI(title="LojaSync Frontend Prototype", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_files = StaticFiles(directory=STATIC_DIR, html=True)
app.mount("/", static_files, name="static")


@app.get("/assets/{path:path}")
async def serve_assets(path: str) -> FileResponse:
    file_path = STATIC_DIR / path
    if not file_path.exists():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Asset não encontrado")
    return FileResponse(file_path)


def ensure_dependencies() -> None:
    try:
        import importlib.metadata as importlib_metadata
    except Exception:
        import importlib_metadata  # type: ignore

    try:
        importlib_metadata.version("fastapi")
        importlib_metadata.version("uvicorn")
    except importlib_metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "Dependências FastAPI/uvicorn não instaladas. Execute: pip install fastapi uvicorn"
        ) from exc


def run(host: str = "127.0.0.1", port: int = 5173) -> None:
    ensure_dependencies()
    import uvicorn

    uvicorn.run(
        "webapp.frontend:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
