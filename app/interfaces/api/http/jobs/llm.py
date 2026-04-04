from __future__ import annotations

import os
from typing import Any

import httpx


def llm_base_url() -> str:
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = os.getenv("LLM_PORT", "8002")
    return os.getenv("LLM_BASE_URL", f"http://{host}:{port}")


def llm_timeout_seconds() -> float:
    try:
        return float(os.getenv("LLM_HTTP_TIMEOUT_SECONDS", "900"))
    except Exception:
        return 900.0


def coerce_int_env(name: str, default: int) -> int:
    try:
        raw = str(os.getenv(name, str(default))).strip()
        if not raw:
            return default
        return int(raw)
    except Exception:
        return default


def _extract_chat_content(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("text", "output_text", "content"):
            value = raw.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return _extract_chat_content(value)
        return ""
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            text = _extract_chat_content(item)
            if text:
                parts.append(text)
        return "".join(parts)
    return ""


def post_llm_chat(
    client: httpx.Client,
    *,
    job_id: str,
    mode: str = "romaneio_extractor",
    message: str,
    documents: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> tuple[str, str | None]:
    payload = {
        "message": message,
        "mode": mode,
        "images": images,
        "documents": documents,
    }
    response = client.post(
        f"{llm_base_url()}/api/chat",
        json=payload,
        headers={"X-Job-Id": job_id},
    )
    response.raise_for_status()
    data: Any
    try:
        data = response.json()
    except Exception:
        data = {"content": response.text}

    if not isinstance(data, dict):
        return "", None
    content = _extract_chat_content(data.get("content")).strip()
    saved_file = data.get("saved_file")
    return content, str(saved_file) if saved_file else None
