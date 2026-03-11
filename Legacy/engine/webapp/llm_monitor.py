from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

import httpx
from fastapi import FastAPI, File, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LLM_MONITOR_HOST = os.getenv("LLM_MONITOR_HOST", "127.0.0.1")
LLM_MONITOR_PORT = int(os.getenv("LLM_MONITOR_PORT", "5174"))

_UPSTREAM_BASE_URL_ENV = os.getenv("LLM_MONITOR_UPSTREAM_BASE_URL")

_UPSTREAM_HOST_ENV = os.getenv("LLM_HOST")
_UPSTREAM_PORT_ENV = os.getenv("LLM_PORT")

_UPSTREAM_HOST = _UPSTREAM_HOST_ENV or "127.0.0.1"
_UPSTREAM_PORT = _UPSTREAM_PORT_ENV or "8002"
DEFAULT_UPSTREAM_BASE_URL = f"http://{_UPSTREAM_HOST}:{_UPSTREAM_PORT}"
LLM_MONITOR_UPSTREAM_BASE_URL = _UPSTREAM_BASE_URL_ENV or DEFAULT_UPSTREAM_BASE_URL

LLM_MONITOR_HISTORY_FILE = Path(
    os.getenv(
        "LLM_MONITOR_HISTORY_FILE",
        str(DATA_DIR / "llm_monitor_history.jsonl"),
    )
)

LLM_MONITOR_MEMORY_LIMIT = int(os.getenv("LLM_MONITOR_MEMORY_LIMIT", "500"))
LLM_MONITOR_MAX_TEXT_CHARS = int(os.getenv("LLM_MONITOR_MAX_TEXT_CHARS", "20000"))
LLM_MONITOR_TIMEOUT_SECONDS = float(os.getenv("LLM_MONITOR_TIMEOUT_SECONDS", "900"))


app = FastAPI(title="LojaSync LLM Monitor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_history_lock = threading.RLock()
_history: Deque[Dict[str, Any]] = deque(maxlen=LLM_MONITOR_MEMORY_LIMIT)


class _RealtimeHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                await self.disconnect(client)


_realtime_hub = _RealtimeHub()


def _truncate_text(value: str, *, limit: int) -> Dict[str, Any]:
    if value is None:
        return {"value": "", "truncated": False, "len": 0}
    text = str(value)
    if limit <= 0:
        return {"value": "", "truncated": True, "len": len(text)}
    if len(text) <= limit:
        return {"value": text, "truncated": False, "len": len(text)}
    return {"value": text[:limit], "truncated": True, "len": len(text)}


def _sanitize_images(images: Any) -> Any:
    if not images:
        return []
    if not isinstance(images, list):
        return images
    out: List[Any] = []
    for img in images:
        if isinstance(img, dict):
            data = img.get("data")
            data_prefix = data[:120] if isinstance(data, str) else None
            out.append(
                {
                    "name": img.get("name"),
                    "mime": img.get("mime"),
                    "data_len": len(data) if isinstance(data, str) else None,
                    "data_prefix": data_prefix,
                }
            )
        else:
            out.append(str(img))
    return out


def _sanitize_documents(documents: Any) -> Any:
    if not documents:
        return []
    if not isinstance(documents, list):
        return documents
    out: List[Any] = []
    for doc in documents:
        if isinstance(doc, dict):
            content = doc.get("content")
            if isinstance(content, str):
                content_info = _truncate_text(content, limit=LLM_MONITOR_MAX_TEXT_CHARS)
                out.append(
                    {
                        "name": doc.get("name"),
                        "content": content_info["value"],
                        "content_len": content_info["len"],
                        "content_truncated": content_info["truncated"],
                    }
                )
            else:
                out.append({"name": doc.get("name"), "content": content})
        else:
            out.append(str(doc))
    return out


def _sanitize_chat_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    sanitized = dict(payload)
    if "images" in sanitized:
        sanitized["images"] = _sanitize_images(sanitized.get("images"))
    if "documents" in sanitized:
        sanitized["documents"] = _sanitize_documents(sanitized.get("documents"))
    if "message" in sanitized and isinstance(sanitized.get("message"), str):
        msg_info = _truncate_text(sanitized["message"], limit=LLM_MONITOR_MAX_TEXT_CHARS)
        sanitized["message"] = msg_info["value"]
        sanitized["message_len"] = msg_info["len"]
        sanitized["message_truncated"] = msg_info["truncated"]
    return sanitized


def _sanitize_upload_request(files_meta: List[Dict[str, Any]]) -> Any:
    return {"files": files_meta}


def _sanitize_upload_response(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {
        "images": _sanitize_images(payload.get("images")),
        "documents": _sanitize_documents(payload.get("documents")),
        "errors": payload.get("errors"),
    }


def _sanitize_chat_response(payload: Any) -> Any:
    if not isinstance(payload, dict):
        if isinstance(payload, str):
            return _truncate_text(payload, limit=LLM_MONITOR_MAX_TEXT_CHARS)
        return payload
    sanitized = dict(payload)
    content = sanitized.get("content")
    if isinstance(content, str):
        info = _truncate_text(content, limit=LLM_MONITOR_MAX_TEXT_CHARS)
        sanitized["content"] = info["value"]
        sanitized["content_len"] = info["len"]
        sanitized["content_truncated"] = info["truncated"]
    return sanitized


def _extract_job_id(request: Request) -> Optional[str]:
    return request.headers.get("x-job-id")


def _forward_headers(request: Request) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for key, value in request.headers.items():
        k = key.lower()
        if k in {"host", "content-length", "content-type", "connection"}:
            continue
        if k.startswith("x-") or k in {"authorization", "user-agent", "accept"}:
            headers[key] = value
    return headers


def _append_history(entry: Dict[str, Any]) -> None:
    line = json.dumps(entry, ensure_ascii=False)
    with _history_lock:
        LLM_MONITOR_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LLM_MONITOR_HISTORY_FILE.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
        _history.append(entry)


async def _append_and_broadcast(entry: Dict[str, Any]) -> None:
    _append_history(entry)
    await _realtime_hub.broadcast({"type": "llm.event", "ts": time.time(), "event": entry})


def _load_history_on_startup() -> None:
    if not LLM_MONITOR_HISTORY_FILE.exists():
        return
    recent_lines: Deque[str] = deque(maxlen=LLM_MONITOR_MEMORY_LIMIT)
    try:
        with LLM_MONITOR_HISTORY_FILE.open("r", encoding="utf-8") as fp:
            for line in fp:
                ln = line.strip()
                if ln:
                    recent_lines.append(ln)
    except Exception:
        return

    with _history_lock:
        _history.clear()
        for line in recent_lines:
            try:
                _history.append(json.loads(line))
            except Exception:
                continue


@app.on_event("startup")
async def _startup() -> None:
    _load_history_on_startup()


INDEX_HTML = """<!doctype html>
<html lang=\"pt-br\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>LLM Monitor</title>
  <style>
    :root { color-scheme: dark; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b0f17; color: #e8eefc; }
    header { padding: 14px 16px; border-bottom: 1px solid #1b2640; display: flex; gap: 12px; align-items: baseline; }
    header h1 { font-size: 16px; margin: 0; }
    header .meta { opacity: .8; font-size: 12px; }
    .wrap { display: grid; grid-template-columns: 420px 1fr; gap: 0; height: calc(100vh - 52px); }
    .panel { border-right: 1px solid #1b2640; overflow: auto; }
    .detail { overflow: auto; }
    .toolbar { padding: 10px 12px; border-bottom: 1px solid #1b2640; display: flex; gap: 8px; }
    input { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid #223055; background: #0f1626; color: #e8eefc; }
    .list { padding: 6px; }
    .item { padding: 10px; border: 1px solid #1b2640; background: #0f1626; border-radius: 10px; margin: 6px; cursor: pointer; }
    .item:hover { border-color: #2b3b67; }
    .item .top { display: flex; justify-content: space-between; gap: 12px; }
    .item .path { font-weight: 600; }
    .item .sub { opacity: .75; font-size: 12px; margin-top: 6px; display: flex; gap: 10px; flex-wrap: wrap; }
    .pill { border: 1px solid #223055; padding: 2px 8px; border-radius: 999px; }
    pre { margin: 0; padding: 14px; white-space: pre-wrap; word-break: break-word; }
    .empty { padding: 14px; opacity: .8; }
  </style>
</head>
<body>
  <header>
    <h1>LLM Monitor</h1>
    <div class=\"meta\" id=\"meta\"></div>
  </header>
  <div class=\"wrap\">
    <div class=\"panel\">
      <div class=\"toolbar\">
        <input id=\"filter\" placeholder=\"Filtrar por endpoint, job_id, status...\" />
      </div>
      <div class=\"list\" id=\"list\"></div>
    </div>
    <div class=\"detail\" id=\"detail\"><div class=\"empty\">Selecione um evento à esquerda.</div></div>
  </div>

<script>
  const state = { events: [], selectedId: null, filter: "" };

  const metaEl = document.getElementById('meta');
  const listEl = document.getElementById('list');
  const detailEl = document.getElementById('detail');
  const filterEl = document.getElementById('filter');

  function fmtTs(ts) {
    try { return new Date(ts * 1000).toLocaleString(); } catch { return String(ts); }
  }

  function matchesFilter(ev) {
    const q = (state.filter || "").trim().toLowerCase();
    if (!q) return true;
    const hay = JSON.stringify({ endpoint: ev.endpoint, job_id: ev.job_id, status_code: ev.status_code, request: ev.request, response: ev.response }).toLowerCase();
    return hay.includes(q);
  }

  function renderList() {
    const rows = state.events.filter(matchesFilter);
    listEl.innerHTML = rows.map(ev => {
      const job = ev.job_id ? `<span class=\"pill\">job ${ev.job_id}</span>` : '';
      return `
        <div class=\"item\" data-id=\"${ev.id}\">
          <div class=\"top\">
            <div class=\"path\">${ev.endpoint}</div>
            <div class=\"pill\">${ev.status_code}</div>
          </div>
          <div class=\"sub\">
            <span class=\"pill\">${fmtTs(ev.ts)}</span>
            ${job}
            <span class=\"pill\">${ev.duration_ms}ms</span>
          </div>
        </div>
      `;
    }).join('');

    Array.from(listEl.querySelectorAll('.item')).forEach(el => {
      el.addEventListener('click', () => {
        const id = el.getAttribute('data-id');
        state.selectedId = id;
        const ev = state.events.find(e => e.id === id);
        if (ev) renderDetail(ev);
      });
    });
  }

  function renderDetail(ev) {
    detailEl.innerHTML = `<pre>${escapeHtml(JSON.stringify(ev, null, 2))}</pre>`;
  }

  function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function loadHistory() {
    const resp = await fetch('/api/history?limit=200');
    const data = await resp.json();
    state.events = (data && data.events) ? data.events : [];
    renderList();
    metaEl.textContent = `upstream: ${data.upstream_base_url} | history: ${data.history_file}`;
  }

  function connectWs() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        if (payload && payload.type === 'llm.event' && payload.event) {
          state.events.unshift(payload.event);
          if (state.events.length > 500) state.events.pop();
          renderList();
          if (state.selectedId === payload.event.id) renderDetail(payload.event);
        }
      } catch {}
    };
    ws.onclose = () => setTimeout(connectWs, 1500);
  }

  filterEl.addEventListener('input', () => {
    state.filter = filterEl.value;
    renderList();
  });

  loadHistory();
  connectWs();
</script>
</body>
</html>"""


@app.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/api/history")
async def get_history(limit: int = 200) -> Dict[str, Any]:
    lim = max(1, min(limit, LLM_MONITOR_MEMORY_LIMIT))
    with _history_lock:
        events = list(_history)[-lim:]
    return {
        "events": events[::-1],
        "upstream_base_url": LLM_MONITOR_UPSTREAM_BASE_URL,
        "history_file": str(LLM_MONITOR_HISTORY_FILE),
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await _realtime_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await _realtime_hub.disconnect(websocket)


@app.post("/api/upload")
async def proxy_upload(request: Request, files: List[UploadFile] = File(...)) -> Response:
    started_at = time.time()
    job_id = _extract_job_id(request)

    files_meta: List[Dict[str, Any]] = []
    multipart: List[Any] = []

    for uploaded in files:
        data = await uploaded.read()
        filename = uploaded.filename or "file"
        content_type = uploaded.content_type or "application/octet-stream"
        files_meta.append(
            {
                "name": filename,
                "content_type": content_type,
                "size": len(data),
            }
        )
        multipart.append(("files", (filename, data, content_type)))

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(LLM_MONITOR_TIMEOUT_SECONDS, connect=10.0)
        ) as client:
            upstream_resp = await client.post(
                f"{LLM_MONITOR_UPSTREAM_BASE_URL.rstrip('/')}/api/upload",
                files=multipart,
                headers=_forward_headers(request),
            )
    except httpx.RequestError as exc:
        entry = {
            "id": uuid.uuid4().hex,
            "ts": time.time(),
            "endpoint": "/api/upload",
            "method": "POST",
            "job_id": job_id,
            "duration_ms": int((time.time() - started_at) * 1000),
            "status_code": 502,
            "request": _sanitize_upload_request(files_meta),
            "response": {"error": str(exc)},
        }
        await _append_and_broadcast(entry)
        return Response(content=str(exc), status_code=502, media_type="text/plain")

    duration_ms = int((time.time() - started_at) * 1000)

    resp_content_type = upstream_resp.headers.get("content-type") or "application/octet-stream"
    sanitized_response: Any
    if "application/json" in resp_content_type.lower():
        try:
            sanitized_response = _sanitize_upload_response(upstream_resp.json())
        except Exception:
            sanitized_response = {"non_json": True}
    else:
        sanitized_response = {
            "content_type": resp_content_type,
            "text": upstream_resp.text[:LLM_MONITOR_MAX_TEXT_CHARS],
        }

    entry = {
        "id": uuid.uuid4().hex,
        "ts": time.time(),
        "endpoint": "/api/upload",
        "method": "POST",
        "job_id": job_id,
        "duration_ms": duration_ms,
        "status_code": upstream_resp.status_code,
        "request": _sanitize_upload_request(files_meta),
        "response": sanitized_response,
    }
    await _append_and_broadcast(entry)

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        media_type=resp_content_type,
    )


@app.post("/api/chat")
async def proxy_chat(request: Request) -> Response:
    started_at = time.time()
    job_id = _extract_job_id(request)

    try:
        payload = await request.json()
    except Exception:
        payload = None

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(LLM_MONITOR_TIMEOUT_SECONDS, connect=10.0)
        ) as client:
            upstream_resp = await client.post(
                f"{LLM_MONITOR_UPSTREAM_BASE_URL.rstrip('/')}/api/chat",
                json=payload,
                headers=_forward_headers(request),
            )
    except httpx.RequestError as exc:
        entry = {
            "id": uuid.uuid4().hex,
            "ts": time.time(),
            "endpoint": "/api/chat",
            "method": "POST",
            "job_id": job_id,
            "duration_ms": int((time.time() - started_at) * 1000),
            "status_code": 502,
            "request": _sanitize_chat_payload(payload),
            "response": {"error": str(exc)},
        }
        await _append_and_broadcast(entry)
        return Response(content=str(exc), status_code=502, media_type="text/plain")

    duration_ms = int((time.time() - started_at) * 1000)

    resp_content_type = upstream_resp.headers.get("content-type") or "application/octet-stream"
    sanitized_response: Any
    if "application/json" in resp_content_type.lower():
        try:
            sanitized_response = _sanitize_chat_response(upstream_resp.json())
        except Exception:
            sanitized_response = {"non_json": True}
    else:
        sanitized_response = {
            "content_type": resp_content_type,
            "text": upstream_resp.text[:LLM_MONITOR_MAX_TEXT_CHARS],
        }

    entry = {
        "id": uuid.uuid4().hex,
        "ts": time.time(),
        "endpoint": "/api/chat",
        "method": "POST",
        "job_id": job_id,
        "duration_ms": duration_ms,
        "status_code": upstream_resp.status_code,
        "request": _sanitize_chat_payload(payload),
        "response": sanitized_response,
    }
    await _append_and_broadcast(entry)

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        media_type=resp_content_type,
    )


def run(host: str = LLM_MONITOR_HOST, port: int = LLM_MONITOR_PORT) -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
