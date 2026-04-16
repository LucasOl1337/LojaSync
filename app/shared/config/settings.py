from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    app_name: str = os.getenv("LOJASYNC_APP_NAME", "LojaSync")
    api_host: str = os.getenv("LOJASYNC_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("LOJASYNC_BACKEND_PORT", "8800"))
    auth_enabled: bool = os.getenv("LOJASYNC_AUTH_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    auth_host: str = os.getenv("LOJASYNC_AUTH_HOST", "127.0.0.1")
    auth_port: int = int(os.getenv("LOJASYNC_AUTH_PORT", "8810"))
    default_margin: float = 1.0
    default_brands: tuple[str, ...] = ("OGOCHI", "MALWEE", "REVANCHE", "COQ")
    auth_cookie_name: str = os.getenv("LOJASYNC_AUTH_COOKIE_NAME", "lojasync_session")
    auth_session_ttl_minutes: int = int(os.getenv("LOJASYNC_AUTH_SESSION_TTL_MINUTES", str(12 * 60)))
    auth_password_min_length: int = int(os.getenv("LOJASYNC_AUTH_PASSWORD_MIN_LENGTH", "8"))
