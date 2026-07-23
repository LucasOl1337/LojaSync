from __future__ import annotations

import base64
import mimetypes
import os
from typing import Any

import httpx

from app.application.imports.evidence_pipeline import use_evidence_pipeline
from app.application.imports.parsing import decode_text_content, slice_image_payloads


def llm_provider() -> str:
    configured = str(os.getenv("LOJASYNC_LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "").strip().lower()
    if configured:
        return configured
    return "legacy"


def use_zai_provider() -> bool:
    return llm_provider() in {"zai", "z.ai", "glm", "glm-api"}


def use_kimi_provider() -> bool:
    return llm_provider() in {"kimi", "kimi-code", "kimi_code", "moonshot"}


def kimi_base_url() -> str:
    return str(os.getenv("KIMI_BASE_URL") or "https://api.kimi.com/coding/v1").rstrip("/")


def kimi_chat_model() -> str:
    return str(os.getenv("KIMI_MODEL") or "kimi-for-coding").strip()


def zai_base_url() -> str:
    return str(os.getenv("ZAI_BASE_URL") or "https://api.z.ai/api/coding/paas/v4").rstrip("/")


def zai_layout_base_url() -> str:
    return str(os.getenv("ZAI_LAYOUT_BASE_URL") or os.getenv("ZAI_OCR_BASE_URL") or "https://api.z.ai/api/paas/v4").rstrip("/")


def zai_upload_mode() -> str:
    configured = str(os.getenv("ZAI_UPLOAD_MODE") or os.getenv("ZAI_IMPORT_MODE") or "").strip().lower()
    return configured or "vision"


def zai_chat_model(*, has_images: bool) -> str:
    if has_images:
        return str(os.getenv("ZAI_VISION_MODEL") or "glm-4.6v").strip()
    return str(os.getenv("ZAI_CHAT_MODEL") or "glm-5.1").strip()


def llm_base_url() -> str:
    if use_kimi_provider():
        return kimi_base_url()
    if use_zai_provider():
        return zai_base_url()
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


def truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def allow_local_validation_guard() -> bool:
    if use_kimi_provider():
        return truthy_env("KIMI_ALLOW_LOCAL_GUARD", False)
    return truthy_env("LOJASYNC_LLM_ALLOW_LOCAL_GUARD", True)


def _kimi_api_key() -> str:
    return str(os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY") or "").strip()


def _kimi_headers(job_id: str) -> dict[str, str]:
    api_key = _kimi_api_key()
    if not api_key:
        raise RuntimeError("KIMI_API_KEY/MOONSHOT_API_KEY nao configurada para usar o provedor Kimi.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Job-Id": job_id,
    }


def _zai_api_key() -> str:
    return str(os.getenv("ZAI_API_KEY") or os.getenv("GLM_API_KEY") or "").strip()


def _zai_headers(job_id: str) -> dict[str, str]:
    api_key = _zai_api_key()
    if not api_key:
        raise RuntimeError("ZAI_API_KEY/GLM_API_KEY nao configurada para usar o provedor GLM.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Job-Id": job_id,
    }


def _extract_zai_error_message(data: Any) -> str:
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            for key in ("message", "code", "type"):
                value = str(error.get(key) or "").strip()
                if value:
                    return value
        for key in ("message", "detail", "error"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _raise_zai_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = _extract_zai_error_message(response.json())
        except Exception:
            detail = str(getattr(response, "text", "") or "").strip()
        status_code = response.status_code
        message = f"ZAI API retornou HTTP {status_code}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc


def _raise_kimi_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = _extract_zai_error_message(response.json())
        except Exception:
            detail = str(getattr(response, "text", "") or "").strip()
        status_code = response.status_code
        message = f"Kimi API retornou HTTP {status_code}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc


def _is_zai_balance_or_quota_error(exc: Exception) -> bool:
    message = str(exc)
    normalized = message.lower()
    return (
        "http 429" in normalized
        or "insufficient balance" in normalized
        or "no resource package" in normalized
        or "余额不足" in message
        or "资源包" in message
    )


def _guess_content_type(filename: str, content_type: str | None) -> str:
    value = str(content_type or "").strip()
    if value and value != "application/octet-stream":
        return value
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or value or "application/octet-stream"


def _is_pdf_file(filename: str, content_type: str | None) -> bool:
    lower_name = str(filename or "").lower()
    lower_type = str(content_type or "").lower()
    return lower_name.endswith(".pdf") or "pdf" in lower_type


def _is_image_file(filename: str, content_type: str | None) -> bool:
    lower_name = str(filename or "").lower()
    lower_type = str(content_type or "").lower()
    return lower_name.endswith((".png", ".jpg", ".jpeg", ".webp")) or lower_type.startswith("image/")


def _is_plain_text_file(filename: str, content_type: str | None) -> bool:
    lower_name = str(filename or "").lower()
    lower_type = str(content_type or "").lower()
    return (
        lower_name.endswith((".txt", ".csv", ".tsv", ".json", ".md", ".log"))
        or lower_type.startswith("text/")
        or "json" in lower_type
        or "csv" in lower_type
    )


def _to_data_url(contents: bytes, filename: str, content_type: str | None) -> str:
    media_type = _guess_content_type(filename, content_type)
    encoded = base64.b64encode(contents).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _image_to_data_url(image: dict[str, Any]) -> str:
    data = str(image.get("data") or "").strip()
    if not data:
        return ""
    if data.startswith("data:"):
        return data
    mime = str(image.get("mime") or image.get("content_type") or "image/png").strip() or "image/png"
    return f"data:{mime};base64,{data}"


def _image_payload_from_bytes(contents: bytes, filename: str, content_type: str | None) -> dict[str, Any]:
    mime = _guess_content_type(filename, content_type)
    return {
        "name": f"{filename or 'romaneio'}#p1",
        "mime": mime if mime.startswith("image/") else "image/png",
        "data": base64.b64encode(contents).decode("ascii"),
    }


def _render_pdf_pages_for_vision(
    contents: bytes,
    filename: str,
    *,
    provider_label: str = "Z.AI",
    max_pages_env: str = "ZAI_VISION_MAX_PAGES",
    dpi_env: str = "ZAI_PDF_RENDER_DPI",
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not contents:
        return [], warnings
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return [], [f"Falha ao preparar PDF para o modelo visual da {provider_label}: PyMuPDF indisponivel ({exc})."]

    images: list[dict[str, Any]] = []
    document = None
    try:
        document = fitz.open(stream=contents, filetype="pdf")
        total_pages = int(getattr(document, "page_count", 0) or len(document))
        max_pages = max(coerce_int_env(max_pages_env, 12), 1)
        dpi = max(coerce_int_env(dpi_env, 180), 72)
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for index, page in enumerate(document):
            if index >= max_pages:
                break
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pixmap.tobytes("png")
            images.append(
                {
                    "name": f"{filename or 'romaneio.pdf'}#p{index + 1}",
                    "mime": "image/png",
                    "data": base64.b64encode(png_bytes).decode("ascii"),
                }
            )
        if total_pages > max_pages:
            warnings.append(
                f"PDF tem {total_pages} paginas; enviando as primeiras {max_pages} paginas ao modelo visual da {provider_label}."
            )
    except Exception as exc:
        warnings.append(f"Falha ao renderizar PDF para o modelo visual da {provider_label}: {exc}")
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass
    return images, warnings


def _flatten_layout_content(layout_details: Any) -> str:
    if not isinstance(layout_details, list):
        return ""
    parts: list[str] = []
    for page in layout_details:
        if not isinstance(page, list):
            continue
        for item in page:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if content:
                parts.append(content)
    return "\n\n".join(parts).strip()


def _prepare_openai_vision_upload(
    *,
    contents: bytes,
    filename: str,
    content_type: str | None,
    provider_slug: str,
    provider_label: str,
    model: str,
    env_prefix: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    if _is_pdf_file(filename, content_type):
        images, render_warnings = _render_pdf_pages_for_vision(
            contents,
            filename or "romaneio.pdf",
            provider_label=provider_label,
            max_pages_env=f"{env_prefix}_VISION_MAX_PAGES",
            dpi_env=f"{env_prefix}_PDF_RENDER_DPI",
        )
        warnings.extend(render_warnings)
        rendered_pages = len(images)
        # Evidence-first default: full pages first (1). Pre-slicing every page
        # forces the cropped prompt and drops boundary rows. Recovery slices
        # are applied later only when completeness fails.
        default_slices = 1 if env_prefix.upper() in {"KIMI", "ZAI"} else 2
        # Honor explicit legacy pre-slice via LOJASYNC_IMPORT_PIPELINE=legacy
        # or an explicit *_VISION_PAGE_SLICES > 1.
        pipeline = str(os.getenv("LOJASYNC_IMPORT_PIPELINE") or os.getenv("IMPORT_PIPELINE") or "evidence").strip().lower()
        if pipeline in {"legacy", "classic", "old"}:
            default_slices = 2
        slice_count = max(coerce_int_env(f"{env_prefix}_VISION_PAGE_SLICES", default_slices), 1)
        if slice_count > 1 and images:
            images = slice_image_payloads(images, vertical_slices=slice_count)
        return {
            "documents": [],
            "images": images,
            "errors": warnings,
            "provider": f"{provider_slug}_vision",
            "model": model,
            "usage": {},
            "data_info": {
                "mode": "vision",
                "rendered_pages": rendered_pages,
                "images": len(images),
                "page_slices": slice_count,
                "import_pipeline": pipeline or "evidence",
            },
        }

    if _is_image_file(filename, content_type):
        return {
            "documents": [],
            "images": [_image_payload_from_bytes(contents, filename or "romaneio.png", content_type)],
            "errors": [],
            "provider": f"{provider_slug}_vision",
            "model": model,
            "usage": {},
            "data_info": {"mode": "vision", "pages": 1},
        }

    if _is_plain_text_file(filename, content_type):
        text, text_warnings = decode_text_content(contents, filename or "romaneio", content_type)
        warnings.extend(text_warnings)
        return {
            "documents": [{"name": filename or "romaneio", "content": text.strip()}] if text.strip() else [],
            "images": [],
            "errors": warnings,
            "provider": f"{provider_slug}_text",
            "model": model,
            "usage": {},
            "data_info": {"mode": "text"},
        }

    return {
        "documents": [],
        "images": [],
        "errors": [f"Tipo de arquivo nao suportado para entrada visual da {provider_label}."],
        "provider": f"{provider_slug}_vision",
        "model": model,
        "usage": {},
        "data_info": {"mode": "vision", "pages": 0},
    }


def _prepare_zai_vision_upload(
    *,
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> dict[str, Any]:
    return _prepare_openai_vision_upload(
        contents=contents,
        filename=filename,
        content_type=content_type,
        provider_slug="zai",
        provider_label="Z.AI",
        model=zai_chat_model(has_images=not _is_plain_text_file(filename, content_type)),
        env_prefix="ZAI",
    )


def _prepare_kimi_vision_upload(
    *,
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> dict[str, Any]:
    return _prepare_openai_vision_upload(
        contents=contents,
        filename=filename,
        content_type=content_type,
        provider_slug="kimi_code",
        provider_label="Kimi",
        model=kimi_chat_model(),
        env_prefix="KIMI",
    )


def _extract_zai_chat_content(data: Any) -> str:
    if not isinstance(data, dict):
        return _extract_chat_content(data)
    choices = data.get("choices")
    if isinstance(choices, list):
        parts: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                text = _extract_chat_content(message.get("content"))
                if text:
                    parts.append(text)
            delta = choice.get("delta")
            if isinstance(delta, dict):
                text = _extract_chat_content(delta.get("content"))
                if text:
                    parts.append(text)
        if parts:
            return "".join(parts)
    return _extract_chat_content(data.get("content"))


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


def upload_llm_file(
    client: httpx.Client,
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> dict[str, Any]:
    if use_kimi_provider():
        return _prepare_kimi_vision_upload(contents=contents, filename=filename, content_type=content_type)

    if not use_zai_provider():
        response = client.post(
            f"{llm_base_url()}/api/upload",
            files={
                "files": (
                    filename or "romaneio",
                    contents,
                    content_type or "application/octet-stream",
                )
            },
            headers={"X-Job-Id": job_id},
        )
        response.raise_for_status()
        parsed: Any = response.json()
        if isinstance(parsed, dict):
            images = parsed.get("images")
            slice_count = max(
                coerce_int_env("LLM_VISION_PAGE_SLICES", 1 if use_evidence_pipeline() else 2),
                1,
            )
            if slice_count > 1 and isinstance(images, list) and images:
                sliced_images = slice_image_payloads(images, vertical_slices=slice_count)
                parsed = dict(parsed)
                parsed["images"] = sliced_images
                data_info = parsed.get("data_info")
                if not isinstance(data_info, dict):
                    data_info = {}
                parsed["data_info"] = {
                    **data_info,
                    "mode": data_info.get("mode") or "legacy",
                    "page_slices": slice_count,
                    "original_images": len(images),
                    "images": len(sliced_images),
                }
        return parsed if isinstance(parsed, dict) else {}

    upload_mode = zai_upload_mode()
    if upload_mode in {"vision", "vlm", "visual", "coding", "coding-vision"}:
        return _prepare_zai_vision_upload(contents=contents, filename=filename, content_type=content_type)

    payload = {
        "model": str(os.getenv("ZAI_OCR_MODEL") or "glm-ocr"),
        "file": _to_data_url(contents, filename, content_type),
        "return_crop_images": False,
        "need_layout_visualization": False,
        "request_id": job_id[:64],
    }
    try:
        response = client.post(
            f"{zai_layout_base_url()}/layout_parsing",
            json=payload,
            headers=_zai_headers(job_id),
        )
        _raise_zai_for_status(response)
        parsed = response.json()
        data = parsed if isinstance(parsed, dict) else {}
        md_results = str(data.get("md_results") or "").strip()
        content = md_results or _flatten_layout_content(data.get("layout_details"))
        return {
            "documents": [{"name": filename or "romaneio", "content": content}] if content else [],
            "images": [],
            "errors": [],
            "provider": "zai",
            "model": data.get("model") or payload["model"],
            "usage": data.get("usage") or {},
            "data_info": data.get("data_info") or {},
        }
    except Exception as exc:
        if not _is_zai_balance_or_quota_error(exc) or not truthy_env("ZAI_ALLOW_LOCAL_TEXT_FALLBACK", False):
            raise
        local_text, local_warnings = decode_text_content(contents, filename or "romaneio", content_type)
        if not local_text.strip():
            raise
        warnings = [
            f"ZAI OCR indisponivel ({exc}); usando texto extraido localmente do arquivo.",
            *local_warnings,
        ]
        return {
            "documents": [{"name": filename or "romaneio", "content": local_text.strip()}],
            "images": [],
            "errors": warnings,
            "provider": "zai_local_text_fallback",
            "model": "local_pdf_text",
            "usage": {},
            "data_info": {"fallback": "local_text"},
        }


def _build_zai_chat_prompt(
    *,
    mode: str,
    message: str,
    documents: list[dict[str, Any]],
) -> str:
    parts = [message.strip()]
    if mode:
        parts.append(f"Modo: {mode}.")
    for index, document in enumerate(documents, start=1):
        name = str(document.get("name") or f"documento_{index}").strip()
        content = str(document.get("content") or "").strip()
        if content:
            parts.append(f"Documento {index}: {name}\n{content}")
    return "\n\n".join(part for part in parts if part).strip()


def post_llm_chat(
    client: httpx.Client,
    *,
    job_id: str,
    mode: str = "romaneio_extractor",
    message: str,
    documents: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> tuple[str, str | None]:
    if use_kimi_provider():
        prompt = _build_zai_chat_prompt(mode=mode, message=message, documents=documents)
        content_blocks: list[dict[str, Any]] = []
        if images:
            for image in images:
                if not isinstance(image, dict):
                    continue
                data_url = _image_to_data_url(image)
                if data_url:
                    content_blocks.append({"type": "image_url", "image_url": {"url": data_url}})
            if prompt:
                content_blocks.append({"type": "text", "text": prompt})
        has_image_blocks = bool(content_blocks)
        response = client.post(
            f"{kimi_base_url()}/chat/completions",
            json={
                "model": kimi_chat_model(),
                "messages": [{"role": "user", "content": content_blocks if has_image_blocks else prompt}],
                "max_tokens": coerce_int_env("KIMI_MAX_TOKENS", 16384),
            },
            headers=_kimi_headers(job_id),
        )
        _raise_kimi_for_status(response)
        try:
            data: Any = response.json()
        except Exception:
            data = {"content": response.text}
        return _extract_zai_chat_content(data).strip(), None

    if use_zai_provider():
        prompt = _build_zai_chat_prompt(mode=mode, message=message, documents=documents)
        content_blocks: list[dict[str, Any]] = []
        if images:
            for image in images:
                if not isinstance(image, dict):
                    continue
                data_url = _image_to_data_url(image)
                if data_url:
                    content_blocks.append({"type": "image_url", "image_url": {"url": data_url}})
            if prompt:
                content_blocks.append({"type": "text", "text": prompt})
        has_image_blocks = bool(content_blocks)
        messages: list[dict[str, Any]] = [{"role": "user", "content": content_blocks if has_image_blocks else prompt}]
        response = client.post(
            f"{zai_base_url()}/chat/completions",
            json={
                "model": zai_chat_model(has_images=has_image_blocks),
                "messages": messages,
                "max_tokens": coerce_int_env(
                    "ZAI_VISION_MAX_TOKENS" if has_image_blocks else "ZAI_CHAT_MAX_TOKENS",
                    16384,
                ),
                "temperature": 0,
                "thinking": {"type": "disabled"},
            },
            headers=_zai_headers(job_id),
        )
        _raise_zai_for_status(response)
        try:
            data: Any = response.json()
        except Exception:
            data = {"content": response.text}
        return _extract_zai_chat_content(data).strip(), None

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
