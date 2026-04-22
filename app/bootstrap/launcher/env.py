"""LojaSync Launcher — Environment and configuration constants.

Extracted from launcher.py to isolate configuration logic.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]  # LojaSync/
PROJECT_ROOT = ROOT_DIR
ENGINE_DIR = PROJECT_ROOT / "Legacy" / "engine"
FRONTEND_TS_DIR = ROOT_DIR / "frontend-ts"
FRONTEND_TS_DIST_DIR = FRONTEND_TS_DIR / "dist"
NODEJS_DIR = Path(r"C:\Program Files\nodejs")

# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------

def _coerce_int(value: Any, fallback: int) -> int:
    try:
        if value in (None, ""):
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if value in (None, ""):
        return fallback
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return fallback


# ---------------------------------------------------------------------------
# User params (webapp.parametros)
# ---------------------------------------------------------------------------

def _load_user_params():
    import sys
    for candidate_str in (str(ROOT_DIR), str(ENGINE_DIR)):
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    try:
        import webapp.parametros as _mod  # type: ignore
        return _mod
    except Exception:
        return None


_user_params = _load_user_params()


def _param_value(name: str, fallback: Any) -> Any:
    if _user_params and hasattr(_user_params, name):
        value = getattr(_user_params, name)
        if value not in (None, ""):
            return value
    return fallback


# ---------------------------------------------------------------------------
# Default configuration values (from env / user params)
# ---------------------------------------------------------------------------

DEFAULT_HOST: str = os.getenv("LOJASYNC_HOST") or str(_param_value("HOST", "127.0.0.1"))
DEFAULT_FRONTEND_PORT: int = _coerce_int(
    os.getenv("LOJASYNC_FRONTEND_PORT"),
    _coerce_int(_param_value("FRONTEND_PORT", 5173), 5173),
)
DEFAULT_BACKEND_PORT: int = _coerce_int(
    os.getenv("LOJASYNC_BACKEND_PORT"),
    _coerce_int(_param_value("BACKEND_PORT", 8800), 8800),
)
DEFAULT_AUTH_PORT: int = _coerce_int(
    os.getenv("LOJASYNC_AUTH_PORT"),
    _coerce_int(_param_value("AUTH_PORT", 8810), 8810),
)
DEFAULT_AUTH_ENABLED: bool = _coerce_bool(
    os.getenv("LOJASYNC_AUTH_ENABLED"),
    False,
)
DEFAULT_LLM_PORT: int = _coerce_int(
    os.getenv("LOJASYNC_LLM_PORT"),
    _coerce_int(_param_value("LLM_PORT", 8002), 8002),
)
DEFAULT_LLM_MONITOR_PORT: int = _coerce_int(
    os.getenv("LOJASYNC_LLM_MONITOR_PORT"),
    _coerce_int(_param_value("LLM_MONITOR_PORT", 5174), 5174),
)
DEFAULT_LLM_MONITOR_ENABLED: bool = _coerce_bool(
    os.getenv("LOJASYNC_LLM_MONITOR_ENABLED"),
    True,
)
DEFAULT_LLM_HOST: str = os.getenv("LOJASYNC_LLM_HOST") or str(_param_value("LLM_HOST", DEFAULT_HOST))
DEFAULT_LLM_BIND: str = os.getenv("LOJASYNC_LLM_BIND", "0.0.0.0")
DEFAULT_BROWSER_HOST: str = os.getenv("LOJASYNC_BROWSER_HOST") or str(_param_value("BROWSER_OVERRIDE_HOST", "127.0.0.1"))

PERFORMANCE_DEFAULTS: dict[str, str] = {
    "LLM_DOC_CHUNK_CHARS": "16000",
    "LLM_INCLUDE_IMAGES_WITH_TEXT": "0",
    "PDF_RENDER_MAX_PAGES": "12",
    "PDF_RENDER_ZOOM": "1.5",
    "LLM_ROMANEIO_RETRY_VISION_MAX_PAGES": "4",
    "LLM_ROMANEIO_RETRY_VISION_ZOOM": "1.5",
}

TS_BUILD_INPUTS = (
    FRONTEND_TS_DIR / "index.html",
    FRONTEND_TS_DIR / "package.json",
    FRONTEND_TS_DIR / "package-lock.json",
    FRONTEND_TS_DIR / "tsconfig.json",
    FRONTEND_TS_DIR / "tsconfig.app.json",
    FRONTEND_TS_DIR / "vite.config.ts",
    FRONTEND_TS_DIR / "src",
)
