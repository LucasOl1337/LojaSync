from __future__ import annotations

import httpx

from fastapi import HTTPException, status

from app.domain.auth import AuthCommandResult, AuthStatus, SessionValidation


class HttpAuthConnector:
    def __init__(self, base_url: str, cookie_name: str, timeout_seconds: float = 5.0, enabled: bool = False) -> None:
        self._base_url = base_url.rstrip("/")
        self.cookie_name = cookie_name
        self._timeout_seconds = timeout_seconds
        self._enabled = enabled

    async def get_status(self) -> AuthStatus:
        if not self._enabled:
            return AuthStatus(enabled=False, password_configured=False, bootstrap_required=False, session_ttl_minutes=0)
        payload = await self._request("GET", "/internal/auth/status")
        return AuthStatus(
            enabled=bool(payload.get("enabled", True)),
            password_configured=bool(payload.get("password_configured")),
            bootstrap_required=bool(payload.get("bootstrap_required")),
            session_ttl_minutes=int(payload.get("session_ttl_minutes", 0) or 0),
        )

    async def validate_session_token(self, token: str | None) -> SessionValidation:
        if not self._enabled:
            return SessionValidation(authenticated=False, user=None, expires_at=None)
        payload = await self._request(
            "POST",
            "/internal/auth/validate",
            json={"token": token},
        )
        return SessionValidation(
            authenticated=bool(payload.get("authenticated")),
            user=str(payload.get("user")).strip() if payload.get("user") else None,
            expires_at=int(payload.get("expires_at")) if payload.get("expires_at") else None,
        )

    async def bootstrap_password(self, password: str) -> AuthCommandResult:
        self._require_enabled()
        payload = await self._request("POST", "/internal/auth/bootstrap", json={"password": password})
        return self._command_result(payload)

    async def authenticate(self, password: str) -> AuthCommandResult:
        self._require_enabled()
        payload = await self._request("POST", "/internal/auth/login", json={"password": password})
        return self._command_result(payload)

    async def logout(self) -> dict[str, str]:
        if not self._enabled:
            return {"status": "auth_disabled"}
        payload = await self._request("POST", "/internal/auth/logout")
        return {"status": str(payload.get("status") or "logged_out")}

    async def change_password(self, token: str | None, current_password: str, new_password: str) -> dict[str, str]:
        self._require_enabled()
        payload = await self._request(
            "POST",
            "/internal/auth/change-password",
            json={
                "token": token,
                "current_password": current_password,
                "new_password": new_password,
            },
        )
        return {"status": str(payload.get("status") or "password_changed")}

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Autenticacao remota nao foi habilitada.")

    async def _request(self, method: str, path: str, json: dict[str, object] | None = None) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds) as client:
                response = await client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servico de autenticacao indisponivel.",
            ) from exc

        if response.is_success:
            payload = response.json()
            return payload if isinstance(payload, dict) else {}

        detail = response.text
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or detail)
        except ValueError:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail or "Falha no servico de autenticacao.")

    @staticmethod
    def _command_result(payload: dict[str, object]) -> AuthCommandResult:
        return AuthCommandResult(
            status=str(payload.get("status") or ""),
            authenticated=bool(payload.get("authenticated")),
            user=str(payload.get("user")).strip() if payload.get("user") else None,
            token=str(payload.get("token")).strip() if payload.get("token") else None,
        )
