from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import WebSocket


class UiEventBroker:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
            self._loop = asyncio.get_running_loop()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    def publish(self, payload: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), loop)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        stale: list[WebSocket] = []
        for websocket in clients:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        if stale:
            async with self._lock:
                for websocket in stale:
                    self._clients.discard(websocket)


_broker: UiEventBroker | None = None


def configure_ui_event_broker(broker: UiEventBroker) -> UiEventBroker:
    global _broker
    _broker = broker
    return broker


def get_ui_event_broker() -> UiEventBroker | None:
    return _broker


def publish_ui_event(payload: dict[str, Any]) -> None:
    broker = _broker
    if broker is None:
        return
    payload.setdefault("ts", time.time())
    broker.publish(payload)


def publish_state_changed(scopes: list[str]) -> None:
    normalized = sorted({str(scope).strip() for scope in scopes if str(scope).strip()})
    if not normalized:
        return
    publish_ui_event({"type": "state.changed", "scopes": normalized})


def publish_job_updated(
    *,
    job: str,
    job_id: str,
    stage: str,
    message: str,
    error: str | None = None,
) -> None:
    publish_ui_event(
        {
            "type": "job.updated",
            "job": job,
            "job_id": job_id,
            "stage": stage,
            "message": message,
            "error": error,
        }
    )
