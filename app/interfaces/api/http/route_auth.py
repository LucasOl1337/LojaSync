from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.interfaces.api.http.route_shared import get_auth_connector
from app.shared.logging.setup import log_event

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


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


def _request_id(request: Request) -> str | None:
    state_id = getattr(request.state, "request_id", None)
    header_id = request.headers.get("x-request-id")
    value = state_id or header_id
    return str(value).strip() if value else None


def _http_status(exc: Exception) -> int:
    return exc.status_code if isinstance(exc, HTTPException) else 500


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
    try:
        result = await get_auth_connector(request).bootstrap_password(payload.password)
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth_bootstrap_failed",
            "auth bootstrap failed",
            request_id=_request_id(request),
            status_code=_http_status(exc),
        )
        raise
    if result.token:
        _apply_session_cookie(request, response, result.token)
    log_event(
        logger,
        logging.INFO,
        "auth_bootstrap_succeeded",
        "auth bootstrap succeeded",
        request_id=_request_id(request),
        user=result.user or "admin",
    )
    return {"status": result.status, "authenticated": result.authenticated, "user": result.user}


@router.post("/login")
async def auth_login(payload: PasswordPayload, request: Request, response: Response) -> dict[str, object]:
    try:
        result = await get_auth_connector(request).authenticate(payload.password)
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth_login_failed",
            "auth login failed",
            request_id=_request_id(request),
            status_code=_http_status(exc),
        )
        raise
    if result.token:
        _apply_session_cookie(request, response, result.token)
    log_event(
        logger,
        logging.INFO,
        "auth_login_succeeded",
        "auth login succeeded",
        request_id=_request_id(request),
        user=result.user or "admin",
    )
    return {"status": result.status, "authenticated": result.authenticated, "user": result.user}


@router.post("/logout")
async def auth_logout(request: Request, response: Response) -> dict[str, str]:
    try:
        await get_auth_connector(request).logout()
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth_logout_failed",
            "auth logout failed",
            request_id=_request_id(request),
            status_code=_http_status(exc),
        )
        raise
    clear_auth_cookie(request, response)
    log_event(
        logger,
        logging.INFO,
        "auth_logout_succeeded",
        "auth logout succeeded",
        request_id=_request_id(request),
    )
    return {"status": "logged_out"}


@router.post("/change-password")
async def auth_change_password(payload: ChangePasswordPayload, request: Request, response: Response) -> dict[str, str]:
    auth_connector = get_auth_connector(request)
    try:
        await auth_connector.change_password(
            request.cookies.get(auth_connector.cookie_name),
            payload.current_password,
            payload.new_password,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth_password_change_failed",
            "auth password change failed",
            request_id=_request_id(request),
            status_code=_http_status(exc),
        )
        raise
    clear_auth_cookie(request, response)
    log_event(
        logger,
        logging.INFO,
        "auth_password_changed",
        "auth password changed",
        request_id=_request_id(request),
        user="admin",
    )
    return {"status": "password_changed"}
