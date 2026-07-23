from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from typing import Any

import httpx

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


def use_openai_compat_provider() -> bool:
    """OpenAI-compatible gateway (9router, LiteLLM, OpenRouter-style, custom)."""
    return llm_provider() in {
        "openai",
        "openai_compat",
        "openai-compatible",
        "9router",
        "ninerouter",
        "nine_router",
        "openrouter",
        "litellm",
        "gateway",
    }


def kimi_base_url() -> str:
    return str(os.getenv("KIMI_BASE_URL") or "https://api.kimi.com/coding/v1").rstrip("/")


def kimi_chat_model() -> str:
    # Kimi Code K2.7 highspeed — same model family, lower latency endpoint.
    return str(os.getenv("KIMI_MODEL") or "kimi-for-coding-highspeed").strip()


def openai_compat_base_url() -> str:
    return str(
        os.getenv("LOJASYNC_OPENAI_BASE_URL")
        or os.getenv("OPENAI_COMPAT_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("NINE_ROUTER_BASE_URL")
        or os.getenv("ANTHROPIC_BASE_URL")
        or "http://127.0.0.1:20128/v1"
    ).rstrip("/")


def openai_compat_api_key() -> str:
    return str(
        os.getenv("LOJASYNC_OPENAI_API_KEY")
        or os.getenv("OPENAI_COMPAT_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("NINE_ROUTER_API_KEY")
        or os.getenv("BOMBA_LAB_NINE_ROUTER_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
        or os.getenv("OPENROUTER_API_KEY")
        or ""
    ).strip()


def openai_compat_chat_model(*, has_images: bool = False) -> str:
    if has_images:
        vision = str(
            os.getenv("LOJASYNC_LLM_VISION_MODEL")
            or os.getenv("OPENAI_COMPAT_VISION_MODEL")
            or os.getenv("OPENAI_VISION_MODEL")
            or ""
        ).strip()
        if vision:
            return vision
    return str(
        os.getenv("LOJASYNC_LLM_MODEL")
        or os.getenv("OPENAI_COMPAT_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("NINE_ROUTER_MODEL")
        or "kimi/kimi-for-coding-highspeed"
    ).strip()


def openai_compat_extra_body() -> dict[str, Any]:
    """Optional JSON body extras for the gateway (thinking, temperature, etc.)."""
    raw = str(os.getenv("LOJASYNC_LLM_EXTRA_BODY") or os.getenv("OPENAI_COMPAT_EXTRA_BODY") or "").strip()
    if not raw:
        # Sensible default for extraction: try disable thinking when gateway supports it.
        if truthy_env("LOJASYNC_LLM_DISABLE_THINKING", True):
            return {"thinking": {"type": "disabled"}}
        return {}
    try:
        import json

        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


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
    if use_openai_compat_provider():
        return openai_compat_base_url()
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
    # Off by default: extraction and approval are LLM-driven; local parsers must not replace LLM results.
    if use_kimi_provider() or use_openai_compat_provider():
        return truthy_env("KIMI_ALLOW_LOCAL_GUARD", False) or truthy_env("LOJASYNC_LLM_ALLOW_LOCAL_GUARD", False)
    return truthy_env("LOJASYNC_LLM_ALLOW_LOCAL_GUARD", False)


def _openai_compat_headers(job_id: str) -> dict[str, str]:
    api_key = openai_compat_api_key()
    if not api_key:
        raise RuntimeError(
            "Chave do gateway OpenAI-compat nao configurada "
            "(LOJASYNC_OPENAI_API_KEY / NINE_ROUTER_API_KEY / OPENAI_API_KEY)."
        )
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Job-Id": job_id,
    }


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


def _extract_pdf_embedded_text(
    contents: bytes,
    *,
    max_pages: int = 20,
) -> tuple[str, list[str]]:
    """Pull selectable text from a digital PDF (no rasterization)."""
    warnings: list[str] = []
    if not contents:
        return "", warnings
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return "", [f"PyMuPDF indisponivel para extrair texto do PDF ({exc})."]

    document = None
    try:
        document = fitz.open(stream=contents, filetype="pdf")
        total_pages = int(getattr(document, "page_count", 0) or len(document))
        page_limit = max(int(max_pages or 1), 1)
        parts: list[str] = []
        for index, page in enumerate(document):
            if index >= page_limit:
                break
            try:
                parts.append(str(page.get_text("text") or ""))
            except Exception:
                parts.append("")
        text = "\n".join(parts).strip()
        if total_pages > page_limit:
            warnings.append(
                f"PDF tem {total_pages} paginas; texto embutido limitado as primeiras {page_limit}."
            )
        return text, warnings
    except Exception as exc:
        return "", [f"Falha ao extrair texto embutido do PDF: {exc}"]
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass


def _pdf_embedded_text_is_useful(text: str) -> bool:
    cleaned = str(text or "").strip()
    min_chars = max(coerce_int_env("KIMI_PDF_TEXT_MIN_CHARS", 400), 1)
    min_rows = max(coerce_int_env("KIMI_PDF_TEXT_MIN_ROWS", 3), 1)
    if len(cleaned) < min_chars:
        return False
    # DANFE totals alone already unlock validation anchors and often enough line text for LLM.
    lower = cleaned.lower()
    if "valor total da nota" in lower or "valor total dos produtos" in lower:
        lines = [line for line in cleaned.splitlines() if line.strip()]
        if len(lines) >= 8:
            return True
    try:
        from app.application.imports.parsing import extract_structured_invoice_row_lines
    except Exception:
        lines = [line for line in cleaned.splitlines() if line.strip()]
        return len(lines) >= max(min_rows * 2, 6)
    rows = extract_structured_invoice_row_lines(cleaned)
    if len(rows) >= min_rows:
        return True
    # Digital DANFEs often fail the structured-row heuristic but still have dense product text.
    digit_lines = sum(1 for line in cleaned.splitlines() if re.search(r"\d{5,}", line))
    return digit_lines >= max(min_rows * 2, 6)


def _render_pdf_pages_for_vision(
    contents: bytes,
    filename: str,
    *,
    provider_label: str = "Z.AI",
    max_pages_env: str = "ZAI_VISION_MAX_PAGES",
    dpi_env: str = "ZAI_PDF_RENDER_DPI",
    default_max_pages: int = 12,
    default_dpi: int = 180,
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
        max_pages = max(coerce_int_env(max_pages_env, default_max_pages), 1)
        dpi = max(coerce_int_env(dpi_env, default_dpi), 72)
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
    # Kimi defaults favor latency: fewer pages, lighter DPI, no vertical page split by default.
    is_kimi = env_prefix.upper() == "KIMI"
    default_max_pages = 8 if is_kimi else 12
    default_dpi = 144 if is_kimi else 180
    default_slices = 1 if is_kimi else 2

    if _is_pdf_file(filename, content_type):
        images, render_warnings = _render_pdf_pages_for_vision(
            contents,
            filename or "romaneio.pdf",
            provider_label=provider_label,
            max_pages_env=f"{env_prefix}_VISION_MAX_PAGES",
            dpi_env=f"{env_prefix}_PDF_RENDER_DPI",
            default_max_pages=default_max_pages,
            default_dpi=default_dpi,
        )
        warnings.extend(render_warnings)
        rendered_pages = len(images)
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
            "data_info": {"mode": "vision", "rendered_pages": rendered_pages, "images": len(images), "page_slices": slice_count},
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
    """Route Kimi inputs: TXT/PDF → text documents; pure images → vision pages."""
    model = kimi_chat_model()
    warnings: list[str] = []

    # Plain text files always use the text path.
    if _is_plain_text_file(filename, content_type):
        text, text_warnings = decode_text_content(contents, filename or "romaneio", content_type)
        warnings.extend(text_warnings)
        return {
            "documents": [{"name": filename or "romaneio", "content": text.strip()}] if text.strip() else [],
            "images": [],
            "errors": warnings,
            "provider": "kimi_code_text",
            "model": model,
            "usage": {},
            "data_info": {"mode": "text", "chars": len(text or "")},
        }

    # PDFs always try embedded text first (digital DANFE). Vision only if text is empty/unusable.
    if _is_pdf_file(filename, content_type):
        pdf_text, pdf_text_warnings = _extract_pdf_embedded_text(
            contents,
            max_pages=max(coerce_int_env("KIMI_PDF_TEXT_MAX_PAGES", 20), 1),
        )
        warnings.extend(pdf_text_warnings)
        # Prefer text path for any PDF that has usable embedded text.
        if truthy_env("KIMI_PDF_PREFER_TEXT", True) and (
            _pdf_embedded_text_is_useful(pdf_text) or len(str(pdf_text or "").strip()) >= 200
        ):
            return {
                "documents": [{"name": filename or "romaneio.pdf", "content": pdf_text.strip()}],
                "images": [],
                "errors": warnings,
                "provider": "kimi_code_pdf_text",
                "model": model,
                "usage": {},
                "data_info": {
                    "mode": "pdf_text",
                    "chars": len(pdf_text.strip()),
                    "prefer_text": True,
                },
                "validation_text": pdf_text.strip(),
            }
        # Scanned PDF (no text): fall back to vision pages.
        prepared = _prepare_openai_vision_upload(
            contents=contents,
            filename=filename,
            content_type=content_type,
            provider_slug="kimi_code",
            provider_label="Kimi",
            model=model,
            env_prefix="KIMI",
        )
        prepared = dict(prepared)
        errors = list(prepared.get("errors") or [])
        errors.extend(warnings)
        if not pdf_text.strip():
            errors.append("PDF sem texto embutido util; usando vision por pagina.")
        prepared["errors"] = errors
        if pdf_text.strip():
            prepared["validation_text"] = pdf_text.strip()
            data_info = dict(prepared.get("data_info") or {})
            data_info["pdf_text_chars"] = len(pdf_text.strip())
            data_info["pdf_text_for_validation"] = True
            prepared["data_info"] = data_info
        return prepared

    # Pure images (png/jpg/webp): vision only.
    if _is_image_file(filename, content_type):
        return _prepare_openai_vision_upload(
            contents=contents,
            filename=filename,
            content_type=content_type,
            provider_slug="kimi_code",
            provider_label="Kimi",
            model=model,
            env_prefix="KIMI",
        )

    return {
        "documents": [],
        "images": [],
        "errors": [f"Tipo de arquivo nao suportado para o Kimi: {filename or content_type or 'desconhecido'}"],
        "provider": "kimi_code",
        "model": model,
        "usage": {},
        "data_info": {"mode": "unsupported"},
    }


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


def _extract_openai_response_text(raw_text: str, data: Any = None) -> tuple[str, dict[str, Any] | None]:
    """Parse OpenAI-compat JSON or SSE stream into assistant text + last usage blob."""
    text = ""
    usage: dict[str, Any] | None = None
    if isinstance(data, dict):
        text = _extract_zai_chat_content(data).strip()
        if isinstance(data.get("usage"), dict):
            usage = data["usage"]
        if text:
            return text, usage

    body = str(raw_text or "")
    if "data:" in body:
        parts: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                chunk = json.loads(payload)
            except Exception:
                continue
            if not isinstance(chunk, dict):
                continue
            if isinstance(chunk.get("usage"), dict):
                usage = chunk["usage"]
            piece = _extract_zai_chat_content(chunk)
            if piece:
                parts.append(piece)
        text = "".join(parts).strip()
        if text:
            return text, usage

    # Fallback: whole body as JSON
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        text = _extract_zai_chat_content(parsed).strip()
        if isinstance(parsed.get("usage"), dict):
            usage = parsed["usage"]
    return text, usage


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

    if use_openai_compat_provider():
        # Same local text/vision routing as Kimi; chat goes to the modular gateway.
        prepared = _prepare_kimi_vision_upload(contents=contents, filename=filename, content_type=content_type)
        prepared = dict(prepared)
        model = openai_compat_chat_model(has_images=bool(prepared.get("images")))
        prepared["model"] = model
        provider = str(prepared.get("provider") or "openai_compat")
        prepared["provider"] = provider.replace("kimi_code", "openai_compat")
        return prepared

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
            slice_count = max(coerce_int_env("LLM_VISION_PAGE_SLICES", 2), 1)
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
    from app.application.imports.llm_prompts import build_kimi_user_prompt

    # Shared user-body builder (context-rich). Used by Kimi and Z.AI.
    return build_kimi_user_prompt(mode=mode, message=message, documents=documents)


def _accumulate_llm_usage(metrics: dict[str, Any] | None, usage: Any) -> None:
    if metrics is None or not isinstance(usage, dict):
        return
    prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens) or 0)
    metrics["llm_prompt_tokens"] = int(metrics.get("llm_prompt_tokens") or 0) + max(prompt_tokens, 0)
    metrics["llm_completion_tokens"] = int(metrics.get("llm_completion_tokens") or 0) + max(completion_tokens, 0)
    metrics["llm_total_tokens"] = int(metrics.get("llm_total_tokens") or 0) + max(total_tokens, 0)
    details = list(metrics.get("llm_usage_calls") or [])
    details.append(
        {
            "prompt_tokens": max(prompt_tokens, 0),
            "completion_tokens": max(completion_tokens, 0),
            "total_tokens": max(total_tokens, 0),
        }
    )
    metrics["llm_usage_calls"] = details


def _build_openai_style_messages(
    *,
    mode: str,
    message: str,
    documents: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    from app.application.imports.llm_prompts import ROMANEIO_SYSTEM_PROMPT, build_kimi_user_prompt

    user_prompt = build_kimi_user_prompt(mode=mode, message=message, documents=documents)
    content_blocks: list[dict[str, Any]] = []
    if images:
        for image in images:
            if not isinstance(image, dict):
                continue
            data_url = _image_to_data_url(image)
            if data_url:
                content_blocks.append({"type": "image_url", "image_url": {"url": data_url}})
        if user_prompt:
            content_blocks.append({"type": "text", "text": user_prompt})
    has_image_blocks = bool(content_blocks) and bool(images)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": ROMANEIO_SYSTEM_PROMPT},
        {"role": "user", "content": content_blocks if has_image_blocks else user_prompt},
    ]
    return messages, has_image_blocks


def post_llm_chat(
    client: httpx.Client,
    *,
    job_id: str,
    mode: str = "romaneio_extractor",
    message: str,
    documents: list[dict[str, Any]],
    images: list[dict[str, Any]],
    metrics: dict[str, Any] | None = None,
) -> tuple[str, str | None]:
    if use_openai_compat_provider():
        messages, has_image_blocks = _build_openai_style_messages(
            mode=mode, message=message, documents=documents, images=images
        )
        model = openai_compat_chat_model(has_images=has_image_blocks)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": coerce_int_env("LOJASYNC_LLM_MAX_TOKENS", coerce_int_env("OPENAI_COMPAT_MAX_TOKENS", 16384)),
        }
        extra = openai_compat_extra_body()
        if extra:
            # Don't force thinking.disabled if model rejects it — still try; caller can set LOJASYNC_LLM_DISABLE_THINKING=0
            payload.update(extra)
        if metrics is not None:
            metrics["llm_provider"] = llm_provider()
            metrics["llm_model"] = model
            metrics["llm_base_url"] = openai_compat_base_url()
        response = client.post(
            f"{openai_compat_base_url()}/chat/completions",
            json=payload,
            headers=_openai_compat_headers(job_id),
        )
        status_code = int(getattr(response, "status_code", 0) or 0)
        if status_code >= 400:
            # Retry once without thinking extras if gateway complains.
            detail = (getattr(response, "text", None) or "")[:400].lower()
            if extra and ("thinking" in detail or "temperature" in detail or "invalid" in detail):
                payload.pop("thinking", None)
                payload.pop("temperature", None)
                response = client.post(
                    f"{openai_compat_base_url()}/chat/completions",
                    json=payload,
                    headers=_openai_compat_headers(job_id),
                )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = None
        raw_text = getattr(response, "text", None) or ""
        content, usage = _extract_openai_response_text(raw_text, data)
        if usage:
            _accumulate_llm_usage(metrics, usage)
        elif isinstance(data, dict):
            _accumulate_llm_usage(metrics, data.get("usage"))
        if metrics is not None and isinstance(data, dict) and data.get("model"):
            metrics["llm_model_response"] = str(data.get("model"))
        return content.strip(), None

    if use_kimi_provider():
        messages, has_image_blocks = _build_openai_style_messages(
            mode=mode, message=message, documents=documents, images=images
        )
        payload = {
            "model": kimi_chat_model(),
            "messages": messages,
            "max_tokens": coerce_int_env("KIMI_MAX_TOKENS", 16384),
        }
        # Prefer disabled thinking for extraction latency/quality (override with KIMI_DISABLE_THINKING=0).
        if truthy_env("KIMI_DISABLE_THINKING", True):
            payload["thinking"] = {"type": "disabled"}
        if metrics is not None:
            metrics["llm_provider"] = "kimi"
            metrics["llm_model"] = kimi_chat_model()
        response = client.post(
            f"{kimi_base_url()}/chat/completions",
            json=payload,
            headers=_kimi_headers(job_id),
        )
        _raise_kimi_for_status(response)
        try:
            data = response.json()
        except Exception:
            data = {"content": response.text}
        if isinstance(data, dict):
            _accumulate_llm_usage(metrics, data.get("usage"))
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
