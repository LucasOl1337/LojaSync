from __future__ import annotations

from app.application.auth.service import AuthService
from app.domain.auth import AuthCommandResult, AuthStatus, SessionValidation


class AuthServiceConnectorStub:
    def __init__(self, auth_service: AuthService, enabled: bool = True) -> None:
        self._auth_service = auth_service
        self._enabled = enabled
        self.cookie_name = auth_service.cookie_name

    async def get_status(self) -> AuthStatus:
        if not self._enabled:
            return AuthStatus(enabled=False, password_configured=False, bootstrap_required=False, session_ttl_minutes=0)
        payload = self._auth_service.get_status()
        return AuthStatus(
            enabled=True,
            password_configured=bool(payload.get("password_configured")),
            bootstrap_required=bool(payload.get("bootstrap_required")),
            session_ttl_minutes=int(payload.get("session_ttl_minutes", 0) or 0),
        )

    async def validate_session_token(self, token: str | None) -> SessionValidation:
        if not self._enabled:
            return SessionValidation(authenticated=False, user=None, expires_at=None)
        identity = self._auth_service.validate_session_token(token)
        return SessionValidation(
            authenticated=identity is not None,
            user=identity.username if identity else None,
            expires_at=identity.expires_at if identity else None,
        )

    async def bootstrap_password(self, password: str) -> AuthCommandResult:
        if not self._enabled:
            raise RuntimeError("auth disabled in stub")
        token = self._auth_service.bootstrap_password(password)
        return AuthCommandResult(status="configured", authenticated=True, user="admin", token=token)

    async def authenticate(self, password: str) -> AuthCommandResult:
        if not self._enabled:
            raise RuntimeError("auth disabled in stub")
        token = self._auth_service.authenticate(password)
        return AuthCommandResult(status="authenticated", authenticated=True, user="admin", token=token)

    async def logout(self) -> dict[str, str]:
        return {"status": "logged_out"}

    async def change_password(self, token: str | None, current_password: str, new_password: str) -> dict[str, str]:
        if not self._enabled:
            raise RuntimeError("auth disabled in stub")
        self._auth_service.require_authenticated_session(token)
        self._auth_service.change_password(current_password, new_password)
        return {"status": "password_changed"}
