from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.interfaces.api.http.route_shared import get_auth_connector

router = APIRouter(prefix="/auth", tags=["auth"])


class PasswordPayload(BaseModel):
    password: str


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


def _apply_session_cookie(request: Request, response: Response, token: str) -> None:
    auth_connector = get_auth_connector(request)
    secure = request.url.scheme == "https"
    response.set_cookie(
        key=auth_connector.cookie_name,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=request.app.state.container.settings.auth_session_ttl_minutes * 60,
        path="/",
    )


def clear_auth_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(key=get_auth_connector(request).cookie_name, path="/", samesite="lax")


@router.get("/session")
async def auth_session(request: Request) -> dict[str, object]:
    auth_connector = get_auth_connector(request)
    status_payload = await auth_connector.get_status()
    identity = await auth_connector.validate_session_token(request.cookies.get(auth_connector.cookie_name))
    return {
        "auth_enabled": status_payload.enabled,
        "password_configured": status_payload.password_configured,
        "bootstrap_required": status_payload.bootstrap_required,
        "session_ttl_minutes": status_payload.session_ttl_minutes,
        "authenticated": identity.authenticated,
        "user": identity.user,
        "expires_at": identity.expires_at,
    }


@router.post("/bootstrap")
async def auth_bootstrap(payload: PasswordPayload, request: Request, response: Response) -> dict[str, object]:
    result = await get_auth_connector(request).bootstrap_password(payload.password)
    if result.token:
        _apply_session_cookie(request, response, result.token)
    return {"status": result.status, "authenticated": result.authenticated, "user": result.user}


@router.post("/login")
async def auth_login(payload: PasswordPayload, request: Request, response: Response) -> dict[str, object]:
    result = await get_auth_connector(request).authenticate(payload.password)
    if result.token:
        _apply_session_cookie(request, response, result.token)
    return {"status": result.status, "authenticated": result.authenticated, "user": result.user}


@router.post("/logout")
async def auth_logout(request: Request, response: Response) -> dict[str, str]:
    await get_auth_connector(request).logout()
    clear_auth_cookie(request, response)
    return {"status": "logged_out"}


@router.post("/change-password")
async def auth_change_password(payload: ChangePasswordPayload, request: Request, response: Response) -> dict[str, str]:
    auth_connector = get_auth_connector(request)
    await auth_connector.change_password(
        request.cookies.get(auth_connector.cookie_name),
        payload.current_password,
        payload.new_password,
    )
    clear_auth_cookie(request, response)
    return {"status": "password_changed"}
