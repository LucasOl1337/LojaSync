from __future__ import annotations

from dataclasses import dataclass

from app.application.auth.service import AuthService
from app.infrastructure.persistence.files.auth_store import JsonAuthStore
from app.shared.config.settings import AppSettings
from app.shared.paths.runtime_paths import build_runtime_paths


@dataclass(frozen=True)
class AuthRuntimeContainer:
    settings: AppSettings
    paths: object
    auth_service: AuthService


def build_auth_container() -> AuthRuntimeContainer:
    settings = AppSettings()
    paths = build_runtime_paths()
    auth_store = JsonAuthStore(paths.auth_file, settings.auth_session_ttl_minutes)
    auth_service = AuthService(auth_store, settings.auth_password_min_length, settings.auth_cookie_name)
    return AuthRuntimeContainer(settings=settings, paths=paths, auth_service=auth_service)
