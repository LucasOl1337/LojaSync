from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class PasswordPayload(BaseModel):
    password: str


class TokenPayload(BaseModel):
    token: str | None = None


class ChangePasswordPayload(BaseModel):
    token: str | None = None
    current_password: str
    new_password: str


def _auth_service(request: Request):
    return request.app.state.container.auth_service


@router.get("/internal/auth/status")
async def auth_status(request: Request) -> dict[str, object]:
    return {"enabled": True, **_auth_service(request).get_status()}


@router.post("/internal/auth/validate")
async def auth_validate(payload: TokenPayload, request: Request) -> dict[str, object]:
    identity = _auth_service(request).validate_session_token(payload.token)
    return {
        "authenticated": identity is not None,
        "user": identity.username if identity else None,
        "expires_at": identity.expires_at if identity else None,
    }


@router.post("/internal/auth/bootstrap")
async def auth_bootstrap(payload: PasswordPayload, request: Request) -> dict[str, object]:
    token = _auth_service(request).bootstrap_password(payload.password)
    return {"status": "configured", "authenticated": True, "user": "admin", "token": token}


@router.post("/internal/auth/login")
async def auth_login(payload: PasswordPayload, request: Request) -> dict[str, object]:
    token = _auth_service(request).authenticate(payload.password)
    return {"status": "authenticated", "authenticated": True, "user": "admin", "token": token}


@router.post("/internal/auth/logout")
async def auth_logout() -> dict[str, str]:
    return {"status": "logged_out"}


@router.post("/internal/auth/change-password")
async def auth_change_password(payload: ChangePasswordPayload, request: Request) -> dict[str, str]:
    _auth_service(request).require_authenticated_session(payload.token)
    _auth_service(request).change_password(payload.current_password, payload.new_password)
    return {"status": "password_changed"}
