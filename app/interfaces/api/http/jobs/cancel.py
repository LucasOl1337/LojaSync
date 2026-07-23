"""Cooperative cancellation for long-running import jobs (LLM HTTP included)."""

from __future__ import annotations

from threading import Event, RLock
from typing import Any

import httpx

_lock = RLock()
_cancel_events: dict[str, Event] = {}
_http_clients: dict[str, httpx.Client] = {}


class ImportJobCancelled(Exception):
    """Raised when an import job is aborted by the operator."""

    def __init__(self, job_id: str, message: str = "Importação cancelada pelo operador.") -> None:
        self.job_id = job_id
        super().__init__(message)


def _event_for(job_id: str) -> Event:
    key = str(job_id or "").strip()
    with _lock:
        event = _cancel_events.get(key)
        if event is None:
            event = Event()
            _cancel_events[key] = event
        return event


def begin_import_job(job_id: str) -> Event:
    """Reset and return the cancel event for a new/running job."""
    key = str(job_id or "").strip()
    with _lock:
        event = Event()
        _cancel_events[key] = event
        return event


def request_import_cancel(job_id: str) -> bool:
    """Mark job cancelled and close any active HTTP client to abort LLM calls."""
    key = str(job_id or "").strip()
    if not key:
        return False
    with _lock:
        event = _cancel_events.get(key)
        if event is None:
            event = Event()
            _cancel_events[key] = event
        already = event.is_set()
        event.set()
        client = _http_clients.pop(key, None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    return not already or True


def is_import_cancelled(job_id: str) -> bool:
    key = str(job_id or "").strip()
    with _lock:
        event = _cancel_events.get(key)
        return bool(event and event.is_set())


def raise_if_import_cancelled(job_id: str) -> None:
    if is_import_cancelled(job_id):
        raise ImportJobCancelled(job_id)


def register_import_http_client(job_id: str, client: httpx.Client) -> None:
    key = str(job_id or "").strip()
    with _lock:
        _http_clients[key] = client


def unregister_import_http_client(job_id: str, client: httpx.Client | None = None) -> None:
    key = str(job_id or "").strip()
    with _lock:
        current = _http_clients.get(key)
        if client is None or current is client:
            _http_clients.pop(key, None)


def clear_import_cancel_state(job_id: str) -> None:
    key = str(job_id or "").strip()
    with _lock:
        _cancel_events.pop(key, None)
        client = _http_clients.pop(key, None)
    if client is not None:
        try:
            client.close()
        except Exception:
            pass


def cancel_snapshot(job_id: str) -> dict[str, Any]:
    return {
        "job_id": str(job_id or "").strip(),
        "cancelled": is_import_cancelled(job_id),
        "has_active_http_client": str(job_id or "").strip() in _http_clients,
    }
