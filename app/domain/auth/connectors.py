from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthStatus:
    enabled: bool
    password_configured: bool
    bootstrap_required: bool
    session_ttl_minutes: int


@dataclass(frozen=True)
class SessionValidation:
    authenticated: bool
    user: str | None
    expires_at: int | None


@dataclass(frozen=True)
class AuthCommandResult:
    status: str
    authenticated: bool
    user: str | None
    token: str | None = None


class AuthConnector(Protocol):
    cookie_name: str

    async def get_status(self) -> AuthStatus:
        ...

    async def validate_session_token(self, token: str | None) -> SessionValidation:
        ...

    async def bootstrap_password(self, password: str) -> AuthCommandResult:
        ...

    async def authenticate(self, password: str) -> AuthCommandResult:
        ...

    async def logout(self) -> dict[str, str]:
        ...

    async def change_password(self, token: str | None, current_password: str, new_password: str) -> dict[str, str]:
        ...
