from __future__ import annotations

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.shared.ui_events import get_ui_event_broker

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.websocket("/ws/ui")
async def ui_ws(websocket: WebSocket) -> None:
    auth_connector = websocket.app.state.container.auth_connector
    auth_status = await auth_connector.get_status()
    if auth_status.password_configured:
        identity = await auth_connector.validate_session_token(websocket.cookies.get(auth_connector.cookie_name))
        if not identity.authenticated:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="authentication required")
            return
    broker = get_ui_event_broker()
    if broker is None:
        await websocket.accept()
    else:
        await broker.connect(websocket)
    await websocket.send_json({"type": "ui.connected", "ts": time.time()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if broker is not None:
            await broker.disconnect(websocket)
        return
