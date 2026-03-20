from __future__ import annotations

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.websocket("/ws/ui")
async def ui_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "ui.connected", "ts": time.time()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
