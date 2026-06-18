from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.shared.logging.setup import log_event

router = APIRouter()
logger = logging.getLogger(__name__)


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


def _request_id(request: Request) -> str | None:
    state_id = getattr(request.state, "request_id", None)
    header_id = request.headers.get("x-request-id")
    value = state_id or header_id
    return str(value).strip() if value else None


def _http_status(exc: Exception) -> int:
    return exc.status_code if isinstance(exc, HTTPException) else 500


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
    try:
        token = _auth_service(request).bootstrap_password(payload.password)
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
    log_event(
        logger,
        logging.INFO,
        "auth_bootstrap_succeeded",
        "auth bootstrap succeeded",
        request_id=_request_id(request),
        user="admin",
    )
    return {"status": "configured", "authenticated": True, "user": "admin", "token": token}


@router.post("/internal/auth/login")
async def auth_login(payload: PasswordPayload, request: Request) -> dict[str, object]:
    try:
        token = _auth_service(request).authenticate(payload.password)
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
    log_event(
        logger,
        logging.INFO,
        "auth_login_succeeded",
        "auth login succeeded",
        request_id=_request_id(request),
        user="admin",
    )
    return {"status": "authenticated", "authenticated": True, "user": "admin", "token": token}


@router.post("/internal/auth/logout")
async def auth_logout() -> dict[str, str]:
    return {"status": "logged_out"}


@router.post("/internal/auth/change-password")
async def auth_change_password(payload: ChangePasswordPayload, request: Request) -> dict[str, str]:
    try:
        _auth_service(request).require_authenticated_session(payload.token)
        _auth_service(request).change_password(payload.current_password, payload.new_password)
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
    log_event(
        logger,
        logging.INFO,
        "auth_password_changed",
        "auth password changed",
        request_id=_request_id(request),
        user="admin",
    )
    return {"status": "password_changed"}
