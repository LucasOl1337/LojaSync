from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import string
import time
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

import httpx

from app.domain.grades.parser import parse_grade_extraction
from app.domain.products.entities import Product
from app.interfaces.api.http.route_models import (
    GradeExtractionProduct,
    GradeExtractionResponse,
    GradeExtractionStatusResponse,
    ImportRomaneioResultResponse,
    ImportRomaneioStatusResponse,
)
from app.interfaces.api.http.route_shared import CATALOG_SIZES

logger = logging.getLogger(__name__)

IMPORT_JOB_STAGES = {
    "pending": "Aguardando inicio",
    "uploading": "Enviando arquivo para servico LLM",
    "processing": "Processando com servico LLM",
    "parsing": "Interpretando itens detectados",
    "completed": "Concluido",
    "error": "Falha no processamento",
}
_import_jobs: dict[str, ImportRomaneioStatusResponse] = {}
_import_results: dict[str, ImportRomaneioResultResponse] = {}
_import_lock = RLock()

GRADE_JOB_STAGES = {
    "pending": "Aguardando inicio",
    "uploading": "Enviando nota para servico LLM",
    "processing": "Detectando grades via LLM",
    "parsing": "Interpretando grades e aplicando nos produtos",
    "completed": "Processo de grades concluido",
    "error": "Processamento de grades interrompido",
}
_grade_jobs: dict[str, GradeExtractionStatusResponse] = {}
_grade_results: dict[str, GradeExtractionResponse] = {}
_grade_lock = RLock()

ROMANEIO_IMAGE_MESSAGE = (
    "The attached image is a scanned invoice product table. "
    "Extract every visible product row. "
    "Use the short SKU/product code as codigo, not NCM/SH, CFOP, barcode, or long reference numbers. "
    "Copy sizes exactly as printed; never convert numeric sizes to letter sizes. "
    "If a trailing token is only a size, put it in tamanho and do not append it to codigo."
)
ROMANEIO_CROPPED_IMAGE_MESSAGE = (
    "The attached image is a cropped segment of a tall scanned invoice product table. "
    "Extract only the visible product rows from this crop. "
    "Use the short SKU/product code as codigo, not NCM/SH, CFOP, barcode, or long reference numbers. "
    "Copy sizes exactly as printed; never convert numeric sizes to letter sizes. "
    "If a trailing token is only a size, put it in tamanho and do not append it to codigo."
)


def create_import_job() -> ImportRomaneioStatusResponse:
    now = time.time()
    job = ImportRomaneioStatusResponse(
        job_id=uuid.uuid4().hex,
        stage="pending",
        message=IMPORT_JOB_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    with _import_lock:
        _import_jobs[job.job_id] = job
    return job


def update_import_job(
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    error: str | None = None,
    result: ImportRomaneioResultResponse | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    with _import_lock:
        job = _import_jobs.get(job_id)
        if job is None:
            return
        job.stage = stage
        job.message = message or IMPORT_JOB_STAGES.get(stage, stage)
        job.updated_at = time.time()
        if error is not None:
            job.error = error
        if metrics:
            merged = dict(job.metrics or {})
            merged.update(metrics)
            job.metrics = merged
        if result is not None or stage == "completed":
            job.completed_at = job.updated_at
        if result is not None:
            _import_results[job_id] = result


def get_import_job(job_id: str) -> ImportRomaneioStatusResponse | None:
    with _import_lock:
        return _import_jobs.get(job_id)


def get_import_result(job_id: str) -> ImportRomaneioResultResponse | None:
    with _import_lock:
        return _import_results.get(job_id)


def remove_import_job(job_id: str) -> bool:
    with _import_lock:
        exists = job_id in _import_jobs or job_id in _import_results
        _import_jobs.pop(job_id, None)
        _import_results.pop(job_id, None)
    return exists


def create_grade_job() -> GradeExtractionStatusResponse:
    now = time.time()
    job = GradeExtractionStatusResponse(
        job_id=uuid.uuid4().hex,
        stage="pending",
        message=GRADE_JOB_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    with _grade_lock:
        _grade_jobs[job.job_id] = job
    return job


def update_grade_job(
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    error: str | None = None,
    result: GradeExtractionResponse | None = None,
) -> None:
    with _grade_lock:
        job = _grade_jobs.get(job_id)
        if job is None:
            return
        job.stage = stage
        job.message = message or GRADE_JOB_STAGES.get(stage, stage)
        job.updated_at = time.time()
        if error is not None:
            job.error = error
        if result is not None or stage == "completed":
            job.completed_at = job.updated_at
        if result is not None:
            _grade_results[job_id] = result


def get_grade_job(job_id: str) -> GradeExtractionStatusResponse | None:
    with _grade_lock:
        return _grade_jobs.get(job_id)


def get_grade_result(job_id: str) -> GradeExtractionResponse | None:
    with _grade_lock:
        return _grade_results.get(job_id)


def remove_grade_job(job_id: str) -> bool:
    with _grade_lock:
        exists = job_id in _grade_jobs or job_id in _grade_results
        _grade_jobs.pop(job_id, None)
        _grade_results.pop(job_id, None)
    return exists


def llm_base_url() -> str:
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = os.getenv("LLM_PORT", "8002")
    return os.getenv("LLM_BASE_URL", f"http://{host}:{port}")


def llm_timeout_seconds() -> float:
    try:
        return float(os.getenv("LLM_HTTP_TIMEOUT_SECONDS", "900"))
    except Exception:
        return 900.0


def _coerce_int_env(name: str, default: int) -> int:
    try:
        raw = str(os.getenv(name, str(default))).strip()
        if not raw:
            return default
        return int(raw)
    except Exception:
        return default


def _env_flag(name: str, default: str = "0") -> bool:
    value = str(os.getenv(name, default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _extract_text_from_pdf(contents: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not contents:
        return "", warnings
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(contents))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
        return "\n\n".join(parts).strip(), warnings
    except Exception as exc:
        warnings.append(f"Falha ao extrair texto do PDF: {exc}")
        return "", warnings


def _decode_text_content(
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not contents:
        return "", warnings
    lower_name = (filename or "").lower()
    lower_type = (content_type or "").lower()

    if lower_name.endswith(".pdf") or "pdf" in lower_type:
        return _extract_text_from_pdf(contents)

    is_text_type = (
        lower_name.endswith((".txt", ".csv", ".tsv", ".json", ".md", ".log"))
        or lower_type.startswith("text/")
        or "json" in lower_type
        or "csv" in lower_type
    )
    if not is_text_type:
        warnings.append(
            "Tipo de arquivo nao textual para parser local; aguardando retorno estruturado do LLM."
        )
        return "", warnings

    for encoding in ("utf-8", "latin-1"):
        try:
            return contents.decode(encoding), warnings
        except Exception:
            continue
    return "", warnings


def _normalize_header_token(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("código", "codigo")
    normalized = normalized.replace("descrição", "descricao")
    normalized = normalized.replace("preço", "preco")
    return normalized


def _parse_qty(raw: Any) -> int:
    value = str(raw or "").replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", ".")
    try:
        qty = int(round(float(value)))
    except Exception:
        qty = 1
    if qty <= 0:
        return 1
    if qty > 100000:
        return 1
    return qty


def _normalize_price(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        return f"{float(raw):.2f}".replace(".", ",")
    text = str(raw).strip()
    if len(text) > 40:
        text = text[:40]
    return text


def _normalize_product_grades(raw: Any) -> list[dict[str, Any]] | None:
    if not raw:
        return None
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for tamanho, quantidade in raw.items():
            size = str(tamanho or "").strip()
            qty = _parse_qty(quantidade)
            if not size or qty <= 0:
                continue
            items.append({"tamanho": size, "quantidade": qty})
        return items or None
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                size = str(entry.get("tamanho") or entry.get("size") or "").strip()
                qty = _parse_qty(entry.get("quantidade"))
            else:
                size = str(getattr(entry, "tamanho", "") or getattr(entry, "size", "") or "").strip()
                qty = _parse_qty(getattr(entry, "quantidade", None))
            if not size or qty <= 0:
                continue
            items.append({"tamanho": size, "quantidade": qty})
        return items or None
    return None


def _coerce_size_hint(raw: Any) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    value = re.sub(r"(?i)\b(?:tam(?:anho)?\.?)\b", "", value).strip(" -_/()[]{}")
    candidate = re.sub(r"[^A-Za-z0-9]+", "", value).upper()
    if not candidate:
        return ""
    if re.fullmatch(r"\d{1,3}", candidate):
        return candidate
    if candidate in {"U", "PP", "P", "M", "G", "GG", "XG", "XXG", "G1", "G2", "G3", "G4"}:
        return candidate
    return ""


def _extract_embedded_size(value: Any) -> str:
    source = str(value or "").strip()
    if not source:
        return ""
    match = re.search(
        r"(?i)(?:\b(?:tam(?:anho)?\.?)\s*[:\-]?\s*|\s+)([0-9]{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4])\s*$",
        source,
    )
    if match:
        return _coerce_size_hint(match.group(1))
    return ""


def _split_code_and_size(code: Any) -> tuple[str, str]:
    value = str(code or "").strip()
    if not value:
        return "", ""
    match = re.fullmatch(r"([0-9A-Za-z._/-]+)\s+([0-9]{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4])", value, flags=re.IGNORECASE)
    if not match:
        return value, ""
    size = _coerce_size_hint(match.group(2))
    if not size:
        return value, ""
    return match.group(1).strip(), size


def _build_romaneio_image_message(images: list[dict[str, Any]]) -> str:
    names = [str(image.get("name") or "").lower() for image in (images or []) if isinstance(image, dict)]
    if any("#slice" in name for name in names):
        return ROMANEIO_CROPPED_IMAGE_MESSAGE
    if any("#p" in name for name in names):
        return ROMANEIO_IMAGE_MESSAGE
    return ""


def _build_product(
    codigo: Any,
    nome: Any,
    quantidade: Any,
    preco: Any,
    *,
    descricao_completa: Any = None,
    grades: Any = None,
) -> Product:
    code = str(codigo or "").strip()
    name = str(nome or "").strip()
    if len(code) > 80:
        code = code[:80].strip()
    if len(name) > 220:
        name = name[:220].strip()
    full_description = str(descricao_completa or name or "").strip() or None
    normalized_grades = _normalize_product_grades(grades)
    parsed_qty = _parse_qty(quantidade)
    if normalized_grades:
        total_qty = sum(int(item["quantidade"]) for item in normalized_grades)
        if total_qty > 0:
            parsed_qty = total_qty
    return Product(
        nome=name,
        codigo=code,
        codigo_original=code,
        quantidade=parsed_qty,
        preco=_normalize_price(preco),
        categoria="",
        marca="",
        preco_final=None,
        descricao_completa=full_description,
        grades=normalized_grades,
    )


def _products_to_text(records: list[Product]) -> str:
    if not records:
        return ""
    lines = ["codigo|nome|quantidade|preco"]
    for item in records:
        lines.append(
            "|".join(
                [
                    str(item.codigo or "").strip(),
                    str(item.nome or "").strip(),
                    str(int(item.quantidade or 0)),
                    str(item.preco or "").strip(),
                ]
            )
        )
    return "\n".join(lines)


def _has_digits(value: str) -> bool:
    return bool(re.search(r"\d", value or ""))


def _parse_romaneio_lines(content: str) -> list[Product]:
    products: list[Product] = []
    delimiter_only = re.compile(r"^[\s\-|]+$")

    for raw_line in (content or "").splitlines():
        line = raw_line.strip()
        if not line or delimiter_only.match(line):
            continue
        parts = [segment.strip() for segment in line.split("|") if segment.strip()]
        if len(parts) < 3:
            continue
        codigo = parts[0]
        if not _has_digits(codigo):
            continue
        nome = parts[1] if len(parts) > 1 else ""
        quantidade = parts[2] if len(parts) > 2 else "1"
        preco = parts[3] if len(parts) > 3 else ""
        products.append(_build_product(codigo, nome, quantidade, preco))
    return products


def save_romaneio_text(data_dir: Path, content: str) -> Path:
    romaneio_dir = data_dir / "romaneios"
    romaneio_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output = romaneio_dir / f"romaneio_{timestamp}.txt"
    output.write_text(content or "", encoding="utf-8")
    return output


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


def _split_text_chunks(text: str, *, max_chars: int = 8000) -> list[str]:
    value = (text or "").strip()
    if not value:
        return []
    if len(value) <= max_chars:
        return [value]
    parts: list[str] = []
    remaining = value
    min_break = max(int(max_chars * 0.3), 1)
    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining.strip())
            break
        cut = max_chars
        nl = remaining.rfind("\n", 0, max_chars + 1)
        if nl >= min_break:
            cut = nl + 1
        else:
            sp = remaining.rfind(" ", 0, max_chars + 1)
            if sp >= min_break:
                cut = sp + 1
        chunk = remaining[:cut].strip()
        if chunk:
            parts.append(chunk)
        remaining = remaining[cut:].strip()
    return [part for part in parts if part]


def _split_image_batches(images: list[dict[str, Any]], *, batch_size: int = 1) -> list[list[dict[str, Any]]]:
    safe_size = max(int(batch_size or 1), 1)
    if not images:
        return []
    return [images[index : index + safe_size] for index in range(0, len(images), safe_size)]


def _slice_image_payloads(images: list[dict[str, Any]], *, vertical_slices: int) -> list[dict[str, Any]]:
    slice_count = max(int(vertical_slices or 1), 1)
    if slice_count <= 1 or not images:
        return images
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return images

    expanded: list[dict[str, Any]] = []
    for image in images:
        if not isinstance(image, dict):
            continue
        name = str(image.get("name") or "").strip()
        mime = str(image.get("mime") or "image/png").strip() or "image/png"
        data = str(image.get("data") or "").strip()
        if not data or "#p" not in name.lower() or "#slice" in name.lower():
            expanded.append(image)
            continue
        try:
            raw = base64.b64decode(data)
            with Image.open(io.BytesIO(raw)) as loaded:
                source = loaded.convert("RGB")
                width, height = source.size
                if width <= 0 or height <= 0:
                    expanded.append(image)
                    continue
                for index in range(slice_count):
                    top = int(round(height * index / slice_count))
                    bottom = int(round(height * (index + 1) / slice_count))
                    if bottom <= top:
                        continue
                    crop = source.crop((0, top, width, bottom))
                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG")
                    expanded.append(
                        {
                            "name": f"{name}#slice{index + 1}",
                            "mime": "image/png",
                            "data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
                        }
                    )
        except Exception:
            expanded.append(image)
    return expanded or images


def _json_candidate_sections(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    sections: list[str] = []
    for match in re.finditer(r"```(?:json)?\s*", raw, flags=re.IGNORECASE):
        tail = raw[match.end() :].strip()
        if tail:
            sections.append(tail)
    sections.append(raw)
    ordered: list[str] = []
    seen: set[str] = set()
    for section in sections:
        if not section or section in seen:
            continue
        seen.add(section)
        ordered.append(section)
    return ordered


def _payload_items_from_json(payload: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_items = payload.get("items")
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(item)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                items.append(item)
    return items


def _extract_json_payloads(section: str) -> list[Any]:
    source = str(section or "").strip()
    if not source:
        return []
    decoder = json.JSONDecoder()
    payloads: list[Any] = []
    index = 0
    total = len(source)
    while index < total:
        while index < total and source[index].isspace():
            index += 1
        if index >= total:
            break
        try:
            payload, next_index = decoder.raw_decode(source, index)
        except Exception:
            candidates = [pos for pos in (source.find("{", index + 1), source.find("[", index + 1)) if pos >= 0]
            if not candidates:
                break
            index = min(candidates)
            continue
        payloads.append(payload)
        index = max(next_index, index + 1)
    return payloads


def _extract_partial_json_objects(section: str) -> list[dict[str, Any]]:
    source = str(section or "")
    if not source:
        return []

    starts: list[tuple[int, bool]] = []
    items_match = re.search(r'"items"\s*:', source)
    if items_match:
        array_start = source.find("[", items_match.end())
        if array_start >= 0:
            starts.append((array_start + 1, True))
    starts.append((0, False))

    for start_index, stop_on_array_close in starts:
        objects: list[dict[str, Any]] = []
        in_string = False
        escaped = False
        brace_depth = 0
        object_start: int | None = None

        for index in range(start_index, len(source)):
            char = source[index]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if object_start is None:
                if stop_on_array_close and char == "]":
                    break
                if char == "{":
                    object_start = index
                    brace_depth = 1
                continue

            if char == "{":
                brace_depth += 1
                continue
            if char != "}":
                continue

            brace_depth -= 1
            if brace_depth > 0:
                continue

            fragment = source[object_start : index + 1]
            object_start = None
            try:
                payload = json.loads(fragment)
            except Exception:
                continue
            payload_items = _payload_items_from_json(payload)
            if payload_items:
                objects.extend(payload_items)
                continue
            if not isinstance(payload, dict):
                continue
            if not any(key in payload for key in ("codigo", "code", "cod", "sku", "referencia", "ref")):
                continue
            objects.append(payload)

        if objects:
            return objects

    return []


def _extract_json_items(text: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(items: list[dict[str, Any]]) -> None:
        for item in items:
            try:
                fingerprint = json.dumps(item, sort_keys=True, ensure_ascii=False)
            except Exception:
                fingerprint = str(item)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            collected.append(item)

    for section in _json_candidate_sections(text):
        for payload in _extract_json_payloads(section):
            _append(_payload_items_from_json(payload))
    if collected:
        return collected

    for section in _json_candidate_sections(text):
        _append(_extract_partial_json_objects(section))
    return collected


def _map_keys_lower(payload: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_header_token(str(key)): value for key, value in payload.items()}


def _find_header_indexes(headers: list[str]) -> dict[str, int]:
    lowered = [_normalize_header_token(item) for item in headers]

    def _first(candidates: tuple[str, ...]) -> int:
        for idx, name in enumerate(lowered):
            if any(candidate in name for candidate in candidates):
                return idx
        return -1

    mapping: dict[str, int] = {}
    code_i = _first(("codigo", "cod", "sku", "ref", "code"))
    desc_i = _first(("descricao", "description", "produto", "item", "nome", "desc"))
    qty_i = _first(("quantidade", "qtd", "qtde", "qde", "quantity", "qty"))
    price_i = _first(("preco", "price", "valor", "unit", "custo"))
    if code_i >= 0:
        mapping["code"] = code_i
    if desc_i >= 0:
        mapping["desc"] = desc_i
    if qty_i >= 0:
        mapping["qty"] = qty_i
    if price_i >= 0:
        mapping["price"] = price_i
    return mapping


def _records_from_json_items(items: list[dict[str, Any]]) -> list[Product]:
    records: list[Product] = []
    if not items:
        return records
    code_keys = ("codigo", "code", "cod", "sku", "referencia", "ref")
    desc_keys = ("nome_curto", "short_name", "nome_limpo", "descricao_resumida", "descricao", "description", "produto", "nome", "item")
    raw_desc_keys = ("descricao_original", "raw_description", "descricao_completa", "original_description")
    qty_keys = ("quantidade", "qtd", "qtde", "qde", "quantity", "qty")
    price_keys = ("preco", "price", "valor", "unit_price", "unitario")
    size_keys = ("tamanho", "size")
    grades_keys = ("grades", "grade")

    for item in items:
        lower = _map_keys_lower(item)

        def _pick(keys: tuple[str, ...]) -> Any:
            for key in keys:
                if key in lower:
                    return lower[key]
            return None

        codigo = str(_pick(code_keys) or "").strip()
        raw_description = str(_pick(raw_desc_keys) or _pick(("descricao", "description", "produto", "item", "nome")) or "").strip()
        nome = str(_pick(desc_keys) or raw_description).strip()
        grades_payload = _pick(grades_keys)
        size_payload = _pick(size_keys)
        codigo, code_size_hint = _split_code_and_size(codigo)
        explicit_size = _coerce_size_hint(size_payload)
        inferred_size = explicit_size or code_size_hint or _extract_embedded_size(raw_description) or _extract_embedded_size(nome)
        normalized_grades = _normalize_product_grades(grades_payload)
        if normalized_grades is None and inferred_size:
            normalized_grades = _normalize_product_grades(
                [{"tamanho": inferred_size, "quantidade": _pick(qty_keys)}]
            )
        if not codigo or not _has_digits(codigo) or not nome:
            continue
        records.append(
            _build_product(
                codigo,
                nome,
                _pick(qty_keys),
                _pick(price_keys),
                descricao_completa=raw_description or nome,
                grades=normalized_grades,
            )
        )
    return records


def _parse_delimited(text: str, delimiter: str) -> list[Product]:
    usable: list[list[str]] = []
    for line in (text or "").splitlines():
        if delimiter not in line:
            continue
        parts = [part.strip() for part in line.split(delimiter) if part.strip()]
        if len(parts) >= 2:
            usable.append(parts)
    if not usable:
        return []

    header_map: dict[str, int] = {}
    first = usable[0]
    if any(
        keyword in _normalize_header_token(cell)
        for cell in first
        for keyword in ("codigo", "descricao", "quantidade", "preco", "code", "description", "quantity", "price")
    ):
        header_map = _find_header_indexes(first)
        usable = usable[1:]

    records: list[Product] = []
    for parts in usable:
        codigo = (
            parts[header_map["code"]]
            if "code" in header_map and header_map["code"] < len(parts)
            else (parts[0] if parts else "")
        )
        nome = (
            parts[header_map["desc"]]
            if "desc" in header_map and header_map["desc"] < len(parts)
            else (parts[1] if len(parts) > 1 else "")
        )
        if not codigo or not _has_digits(codigo) or not nome:
            continue
        quantidade = (
            parts[header_map["qty"]]
            if "qty" in header_map and header_map["qty"] < len(parts)
            else (parts[2] if len(parts) > 2 else "1")
        )
        preco = (
            parts[header_map["price"]]
            if "price" in header_map and header_map["price"] < len(parts)
            else (parts[3] if len(parts) > 3 else "")
        )
        records.append(_build_product(codigo, nome, quantidade, preco))
    return records


def _parse_space_aligned_table(text: str) -> list[Product]:
    records: list[Product] = []
    price_regex = re.compile(r"(?i)^(?:r\$\s*)?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})$")
    header_regex = re.compile(r"(?i)\b(cod|codigo|ref|sku|descri|produto|item|quant|qtd|preco|price)\b")
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if header_regex.search(line) and not any(char.isdigit() for char in line.split()[0]):
            continue
        tokens = [token.strip() for token in re.split(r"\s{2,}", line) if token.strip()]
        if len(tokens) < 2:
            continue
        codigo = tokens[0]
        if " " in codigo or not _has_digits(codigo):
            continue
        code_alnum = re.sub(r"[^0-9A-Za-z]", "", codigo)
        if len(code_alnum) < 4:
            continue

        qty_raw: Any = None
        price_raw = ""
        desc_tokens: list[str]
        if len(tokens) >= 4 and price_regex.match(tokens[-1]):
            price_raw = tokens[-1]
            qty_raw = tokens[-2]
            desc_tokens = tokens[1:-2]
        elif len(tokens) >= 3 and re.fullmatch(r"\d+", tokens[-1] or ""):
            qty_raw = tokens[-1]
            desc_tokens = tokens[1:-1]
        else:
            desc_tokens = tokens[1:]

        nome = " ".join(desc_tokens).strip()
        if not nome:
            continue
        records.append(_build_product(codigo, nome, qty_raw or 1, price_raw))
    return records


def _parse_markdown_table(text: str) -> list[Product]:
    lines = (text or "").splitlines()
    rows: list[list[str]] = []
    header: list[str] = []
    separator_found = False
    for index in range(len(lines) - 1):
        row = lines[index]
        separator = lines[index + 1]
        if "|" in row and re.match(r"^\s*\|?\s*:?-{3,}.*", separator):
            header = [cell.strip() for cell in row.split("|") if cell.strip()]
            separator_found = True
            start = index + 2
            for inner in range(start, len(lines)):
                current = lines[inner].strip()
                if not current:
                    break
                if "|" not in current:
                    continue
                parts = [cell.strip() for cell in current.split("|") if cell.strip()]
                if len(parts) >= 2:
                    rows.append(parts)
            break
    if not separator_found or not header or not rows:
        return []

    idx = _find_header_indexes(header)
    parsed: list[Product] = []
    for parts in rows:
        codigo = parts[idx["code"]] if "code" in idx and idx["code"] < len(parts) else (parts[0] if parts else "")
        nome = parts[idx["desc"]] if "desc" in idx and idx["desc"] < len(parts) else (parts[1] if len(parts) > 1 else "")
        if not codigo or not _has_digits(codigo) or not nome:
            continue
        quantidade = parts[idx["qty"]] if "qty" in idx and idx["qty"] < len(parts) else (parts[2] if len(parts) > 2 else "1")
        preco = parts[idx["price"]] if "price" in idx and idx["price"] < len(parts) else (parts[3] if len(parts) > 3 else "")
        parsed.append(_build_product(codigo, nome, quantidade, preco))
    return parsed


def _parse_llm_romaneio(text: str) -> list[Product]:
    items = _extract_json_items(text)
    from_json = _records_from_json_items(items) if items else []
    if from_json:
        return from_json
    markdown = _parse_markdown_table(text)
    if markdown:
        return markdown
    for delimiter in ("|", ";", "\t", ","):
        parsed = _parse_delimited(text, delimiter)
        if parsed:
            return parsed
    aligned = _parse_space_aligned_table(text)
    if aligned:
        return aligned
    return _parse_romaneio_lines(text)


def _text_noise_ratio(text: str) -> float:
    value = text or ""
    if not value:
        return 0.0
    suspicious = 0
    total = 0
    allowed_extra = set(" .,;:-_/\\|()[]{}+*#@$%!?\"'`~^&<=>")
    for char in value:
        if char in "\n\r\t":
            continue
        total += 1
        if char in string.printable:
            continue
        if char.isalpha() or char.isdigit():
            continue
        if char in allowed_extra:
            continue
        suspicious += 1
    if total == 0:
        return 0.0
    return suspicious / total


def _looks_like_binary_blob(text: str) -> bool:
    value = text or ""
    if not value:
        return False
    if "\x00" in value:
        return True
    if re.search(r"[A-Za-z0-9+/]{120,}={0,2}", value):
        return True
    return _text_noise_ratio(value) > 0.30


def _is_plausible_product(record: Product) -> bool:
    code = (record.codigo or "").strip()
    name = (record.nome or "").strip()
    if not code or not name:
        return False
    if " " in code:
        return False
    if re.search(r"[^0-9A-Za-z._/-]", code):
        return False
    if _looks_like_binary_blob(code) or _looks_like_binary_blob(name):
        return False

    code_alnum = re.sub(r"[^0-9A-Za-z]", "", code)
    if len(code_alnum) < 4 or len(code_alnum) > 60:
        return False
    if code_alnum.isdigit() and len(code_alnum) < 4:
        return False
    if not _has_digits(code):
        return False

    if len(name) < 2 or len(name) > 220:
        return False
    alpha_count = sum(1 for char in name if char.isalpha())
    if alpha_count < 2:
        return False
    if _text_noise_ratio(name) > 0.20:
        return False
    readable_chars = sum(1 for char in name if char.isalnum() or char.isspace() or char in "-_/.,")
    if readable_chars / max(len(name), 1) < 0.72:
        return False
    if any(len(token) > 40 for token in name.split() if token):
        return False

    lowered_name = _normalize_header_token(name)
    meta_patterns = (
        "data",
        "hora",
        "cnpj",
        "pedido",
        "numero",
        "desconto",
        "valor total",
        "serie",
    )
    if any(pattern in lowered_name for pattern in meta_patterns):
        return False

    if record.quantidade <= 0 or record.quantidade > 100000:
        return False
    return True


def _filter_suspect_records(records: list[Product]) -> list[Product]:
    filtered: list[Product] = []
    grouped: dict[tuple[str, str, str, tuple[tuple[str, int], ...]], Product] = {}
    ordered_keys: list[tuple[str, str, str, tuple[tuple[str, int], ...]]] = []
    for record in records or []:
        if not _is_plausible_product(record):
            continue
        product = _build_product(
            record.codigo,
            record.nome,
            record.quantidade,
            record.preco,
            descricao_completa=record.descricao_completa or record.nome,
            grades=record.grades,
        )
        grades_map: dict[str, int] = {}
        for item in (_normalize_product_grades(product.grades) or []):
            size = str(item.get("tamanho") or item.get("size") or "").strip()
            qty = int(item.get("quantidade") or 0)
            if size and qty > 0:
                grades_map[size] = grades_map.get(size, 0) + qty
        grades_key = tuple(sorted(grades_map.items()))
        key = (
            product.codigo.strip().lower(),
            product.nome.strip().lower(),
            (product.preco or "").strip(),
            grades_key,
        )
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = product
            ordered_keys.append(key)
            continue
        if product.descricao_completa and len(product.descricao_completa) >= len(existing.descricao_completa or ""):
            existing.descricao_completa = product.descricao_completa
        if grades_map:
            merged_grades: dict[str, int] = {}
            for item in (_normalize_product_grades(existing.grades) or []):
                size = str(item.get("tamanho") or "").strip()
                qty = int(item.get("quantidade") or 0)
                if size and qty > 0:
                    merged_grades[size] = merged_grades.get(size, 0) + qty
            for size, qty in grades_map.items():
                merged_grades[size] = merged_grades.get(size, 0) + qty
            existing.grades = _normalize_product_grades(merged_grades)
            existing.quantidade = sum(int(item.get("quantidade") or 0) for item in (existing.grades or []))
        else:
            existing.quantidade += int(product.quantidade or 0)
    for key in ordered_keys:
        filtered.append(grouped[key])
    return filtered


def _parse_pdf_tables_bytes(contents: bytes) -> list[Product]:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []

    records: list[Product] = []
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in (pdf.pages or []):
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    continue
                for table in tables:
                    if not table:
                        continue
                    header = [(cell or "").strip() for cell in table[0]]
                    idx = _find_header_indexes([cell for cell in header if cell])
                    rows = table[1:] if idx else table
                    for row in rows:
                        cells = [(cell or "").strip() for cell in row]
                        if not cells:
                            continue
                        codigo = (
                            cells[idx["code"]]
                            if idx and "code" in idx and idx["code"] < len(cells)
                            else (cells[0] if cells else "")
                        )
                        nome = (
                            cells[idx["desc"]]
                            if idx and "desc" in idx and idx["desc"] < len(cells)
                            else (cells[1] if len(cells) > 1 else "")
                        )
                        if not codigo or not _has_digits(codigo) or not nome:
                            continue
                        quantidade = (
                            cells[idx["qty"]]
                            if idx and "qty" in idx and idx["qty"] < len(cells)
                            else (cells[2] if len(cells) > 2 else "1")
                        )
                        preco = (
                            cells[idx["price"]]
                            if idx and "price" in idx and idx["price"] < len(cells)
                            else (cells[3] if len(cells) > 3 else "")
                        )
                        records.append(_build_product(codigo, nome, quantidade, preco))
    except Exception:
        return records
    return records


def _parse_candidate_content(text: str) -> list[Product]:
    if not text.strip():
        return []
    if _looks_like_binary_blob(text):
        return []
    candidates = _parse_llm_romaneio(text)
    if candidates:
        return _filter_suspect_records(candidates)
    fallback = _parse_romaneio_lines(text)
    return _filter_suspect_records(fallback)


def _post_llm_chat(
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


def run_grade_extraction_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
) -> None:
    warnings: list[str] = []
    llm_text = ""

    update_grade_job(job_id, "uploading")
    try:
        timeout = httpx.Timeout(llm_timeout_seconds(), connect=10.0)
        files = {
            "files": (
                filename or "nota_fiscal",
                contents,
                content_type or "application/octet-stream",
            )
        }
        with httpx.Client(timeout=timeout) as client:
            upload_response = client.post(
                f"{llm_base_url()}/api/upload",
                files=files,
                headers={"X-Job-Id": job_id},
            )
            upload_response.raise_for_status()
            parsed_upload: Any = upload_response.json()
            upload_data = parsed_upload if isinstance(parsed_upload, dict) else {}

            upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
            warnings.extend([str(item) for item in upload_errors if str(item).strip()])

            documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
            images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
            upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()

            update_grade_job(job_id, "processing")
            chunks = _split_text_chunks(
                upload_docs_text,
                max_chars=_coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000),
            )
            if chunks:
                parts: list[str] = []
                total = len(chunks)
                for idx, chunk in enumerate(chunks, start=1):
                    update_grade_job(
                        job_id,
                        "processing",
                        message=f"Processando texto {idx}/{total} com servico LLM",
                    )
                    chat_text, _ = _post_llm_chat(
                        client,
                        job_id=job_id,
                        mode="grade_extractor",
                        message="",
                        documents=[{"name": f"parte_{idx}", "content": chunk}],
                        images=images if idx == 1 else [],
                    )
                    if chat_text:
                        parts.append(chat_text)
                llm_text = "\n\n".join(parts).strip()
            elif images:
                image_inputs = _slice_image_payloads(
                    images,
                    vertical_slices=_coerce_int_env("LLM_PDF_PAGE_VERTICAL_SLICES", 4),
                )
                image_batches = _split_image_batches(
                    image_inputs,
                    batch_size=_coerce_int_env("LLM_IMAGE_BATCH_SIZE", 1),
                )
                parts: list[str] = []
                total = len(image_batches)
                for idx, image_batch in enumerate(image_batches, start=1):
                    label = f"Processando imagens {idx}/{total} com servico LLM" if total > 1 else "Processando imagens com servico LLM"
                    update_grade_job(
                        job_id,
                        "processing",
                        message=label,
                    )
                    chat_text, _ = _post_llm_chat(
                        client,
                        job_id=job_id,
                        mode="grade_extractor",
                        message=_build_romaneio_image_message(image_batch),
                        documents=[],
                        images=image_batch,
                    )
                    if chat_text:
                        parts.append(chat_text)
                llm_text = "\n\n".join(parts).strip()
            else:
                warnings.append("Upload do LLM nao retornou documentos ou imagens.")
    except Exception as exc:
        logger.warning("Falha no pipeline LLM de grades (job_id=%s): %s", job_id, exc)
        warnings.append(f"Falha ao processar grades com o servico LLM: {exc}")

    update_grade_job(job_id, "parsing")
    parsed_items, parser_warnings = parse_grade_extraction(llm_text, allowed_sizes=CATALOG_SIZES)
    warnings.extend(parser_warnings)

    total_atualizados = 0
    detalhes: list[GradeExtractionProduct] = []
    for item in parsed_items:
        updated = service.update_grades_by_identifier(  # type: ignore[attr-defined]
            codigo=item.codigo,
            nome=item.nome,
            grades=item.grades,
        )
        atualizado = updated is not None
        if atualizado:
            total_atualizados += 1
        else:
            warnings.append(
                f"Produto nao localizado para aplicacao de grade (codigo={item.codigo or '-'}, nome={item.nome or '-'})"
            )
        detalhes.append(
            GradeExtractionProduct(
                codigo=item.codigo,
                nome=item.nome,
                grades=item.grades,
                atualizado=atualizado,
                warnings=item.warnings,
            )
        )

    result = GradeExtractionResponse(
        status="ok" if total_atualizados else "partial",
        total_itens=len(parsed_items),
        total_atualizados=total_atualizados,
        warnings=warnings,
        itens=detalhes,
        content=llm_text or None,
    )
    update_grade_job(job_id, "completed", result=result)


def run_import_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
    data_dir: Path,
) -> None:
    warnings: list[str] = []
    llm_text = ""
    upload_docs_text = ""
    local_text = ""
    saved_file: str | None = None
    parsed_items: list[Product] = []
    selected_source = ""
    selected_text = ""
    local_candidates: list[Product] = []
    pdf_rows: list[Product] = []
    llm_candidates: list[Product] = []
    llm_chat_attempted = False
    total_started = time.perf_counter()
    metrics: dict[str, Any] = {
        "file_name": filename or "romaneio",
        "content_type": content_type or "",
        "file_size_bytes": len(contents),
        "llm_base_url": llm_base_url(),
        "llm_timeout_seconds": llm_timeout_seconds(),
        "llm_upload_used": False,
        "llm_chat_used": False,
        "llm_chat_calls": 0,
        "llm_chat_total_ms": 0,
        "llm_chat_calls_details": [],
        "upload_documents_chars": 0,
        "upload_images": 0,
        "local_text_chars": 0,
        "pdf_table_items": 0,
        "selected_source": "",
    }

    update_import_job(
        job_id,
        "processing",
        message="Validando parser local antes do servico LLM",
        metrics=metrics,
    )
    upload_data: dict[str, Any] = {}
    local_first_enabled = _env_flag("ROMANEIO_LOCAL_FIRST", "1")

    decode_started = time.perf_counter()
    local_text, local_warnings = _decode_text_content(contents, filename, content_type)
    metrics["local_decode_ms"] = int((time.perf_counter() - decode_started) * 1000)
    metrics["local_text_chars"] = len(local_text or "")
    warnings.extend(local_warnings)

    if local_first_enabled and local_text.strip():
        local_parse_started = time.perf_counter()
        local_candidates = _parse_candidate_content(local_text)
        metrics["local_parse_ms"] = int((time.perf_counter() - local_parse_started) * 1000)
        metrics["local_candidate_items"] = len(local_candidates)
        if local_candidates:
            parsed_items = local_candidates
            selected_source = "local"
            selected_text = local_text
            warnings.append("Servico LLM pulado: parser local encontrou itens validos antes do upload.")

    is_pdf_input = (filename or "").lower().endswith(".pdf") or "pdf" in (content_type or "").lower()
    if local_first_enabled and not parsed_items and is_pdf_input:
        pdf_started = time.perf_counter()
        pdf_rows = _filter_suspect_records(_parse_pdf_tables_bytes(contents))
        metrics["pdf_tables_ms"] = int((time.perf_counter() - pdf_started) * 1000)
        metrics["pdf_table_items"] = len(pdf_rows)
        if pdf_rows:
            parsed_items = pdf_rows
            selected_source = "pdf_tables"
            selected_text = local_text
            warnings.append("Servico LLM pulado: tabelas do PDF foram extraidas localmente com sucesso.")

    if not parsed_items:
        update_import_job(
            job_id,
            "uploading",
            message="Enviando arquivo para servico LLM",
            metrics=metrics,
        )
        try:
            timeout = httpx.Timeout(llm_timeout_seconds(), connect=10.0)
            files = {
                "files": (
                    filename or "romaneio",
                    contents,
                    content_type or "application/octet-stream",
                )
            }
            upload_started = time.perf_counter()
            with httpx.Client(timeout=timeout) as client:
                upload_response = client.post(
                    f"{llm_base_url()}/api/upload",
                    files=files,
                    headers={"X-Job-Id": job_id},
                )
                metrics["llm_upload_ms"] = int((time.perf_counter() - upload_started) * 1000)
                metrics["llm_upload_used"] = True
                upload_response.raise_for_status()
                parsed_upload: Any = upload_response.json()
                if isinstance(parsed_upload, dict):
                    upload_data = parsed_upload

                upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
                warnings.extend([str(item) for item in upload_errors if str(item).strip()])

                documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
                images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
                upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()
                metrics["upload_documents_chars"] = len(upload_docs_text or "")
                metrics["upload_images"] = len(images)

                if upload_docs_text:
                    upload_parse_started = time.perf_counter()
                    upload_candidates = _parse_candidate_content(upload_docs_text)
                    metrics["upload_parse_ms"] = int((time.perf_counter() - upload_parse_started) * 1000)
                    metrics["upload_candidate_items"] = len(upload_candidates)
                    if upload_candidates:
                        parsed_items = upload_candidates
                        selected_source = "upload_docs"
                        selected_text = upload_docs_text
                        warnings.append("Chat do LLM pulado: o texto retornado no upload ja continha itens validos.")

                if not parsed_items:
                    update_import_job(
                        job_id,
                        "processing",
                        message="Processando com servico LLM",
                        metrics=metrics,
                    )
                    chunks = _split_text_chunks(
                        upload_docs_text,
                        max_chars=_coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000),
                    )
                    if chunks:
                        parts: list[str] = []
                        total = len(chunks)
                        metrics["llm_chunk_count"] = total
                        for idx, chunk in enumerate(chunks, start=1):
                            update_import_job(
                                job_id,
                                "processing",
                                message=f"Processando texto {idx}/{total} com servico LLM",
                                metrics=metrics,
                            )
                            call_started = time.perf_counter()
                            chat_text, chat_saved = _post_llm_chat(
                                client,
                                job_id=job_id,
                                message="",
                                documents=[{"name": f"parte_{idx}", "content": chunk}],
                                images=images if idx == 1 else [],
                            )
                            call_ms = int((time.perf_counter() - call_started) * 1000)
                            metrics["llm_chat_used"] = True
                            metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
                            metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms
                            details = list(metrics.get("llm_chat_calls_details") or [])
                            details.append(
                                {
                                    "chunk": idx,
                                    "duration_ms": call_ms,
                                    "document_chars": len(chunk),
                                    "images": len(images) if idx == 1 else 0,
                                }
                            )
                            metrics["llm_chat_calls_details"] = details
                            llm_chat_attempted = True
                            if chat_saved and not saved_file:
                                saved_file = chat_saved
                            if chat_text:
                                parts.append(chat_text)
                                llm_candidates.extend(_parse_candidate_content(chat_text))
                        llm_text = "\n\n".join(parts).strip()
                    elif images:
                        image_inputs = _slice_image_payloads(
                            images,
                            vertical_slices=_coerce_int_env("LLM_PDF_PAGE_VERTICAL_SLICES", 4),
                        )
                        image_batches = _split_image_batches(
                            image_inputs,
                            batch_size=_coerce_int_env("LLM_IMAGE_BATCH_SIZE", 1),
                        )
                        parts = []
                        total = len(image_batches)
                        metrics["llm_chunk_count"] = total
                        metrics["llm_chat_used"] = True
                        metrics["llm_chat_calls"] = 0
                        metrics["llm_chat_total_ms"] = 0
                        metrics["llm_chat_calls_details"] = []
                        for idx, image_batch in enumerate(image_batches, start=1):
                            label = f"Processando imagens {idx}/{total} com servico LLM" if total > 1 else "Processando imagens com servico LLM"
                            update_import_job(
                                job_id,
                                "processing",
                                message=label,
                                metrics=metrics,
                            )
                            call_started = time.perf_counter()
                            chat_text, chat_saved = _post_llm_chat(
                                client,
                                job_id=job_id,
                                message=_build_romaneio_image_message(image_batch),
                                documents=[],
                                images=image_batch,
                            )
                            call_ms = int((time.perf_counter() - call_started) * 1000)
                            metrics["llm_chat_calls"] = int(metrics.get("llm_chat_calls") or 0) + 1
                            metrics["llm_chat_total_ms"] = int(metrics.get("llm_chat_total_ms") or 0) + call_ms
                            details = list(metrics.get("llm_chat_calls_details") or [])
                            details.append(
                                {
                                    "chunk": idx,
                                    "duration_ms": call_ms,
                                    "document_chars": 0,
                                    "images": len(image_batch),
                                }
                            )
                            metrics["llm_chat_calls_details"] = details
                            llm_chat_attempted = True
                            if chat_saved and not saved_file:
                                saved_file = chat_saved
                            if chat_text:
                                parts.append(chat_text)
                                llm_candidates.extend(_parse_candidate_content(chat_text))
                        llm_text = "\n\n".join(parts).strip()
                    else:
                        warnings.append("Upload do LLM nao retornou documentos ou imagens.")
        except Exception as exc:
            logger.warning("Falha no pipeline de importacao LLM (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao processar com o servico LLM: {exc}")

    update_import_job(
        job_id,
        "parsing",
        message="Interpretando itens detectados",
        metrics=metrics,
    )

    if not parsed_items and llm_candidates:
        parsed_items = _filter_suspect_records(llm_candidates)
        if parsed_items:
            selected_source = "llm"
            selected_text = llm_text or selected_text

    if not parsed_items:
        for source, text in (
            ("llm", llm_text),
            ("upload_docs", upload_docs_text),
            ("local", local_text),
        ):
            current = (text or "").strip()
            if not current:
                continue
            candidates = _parse_candidate_content(current)
            if candidates:
                parsed_items = candidates
                selected_source = source
                selected_text = current
                break

    if not parsed_items and not pdf_rows and is_pdf_input:
        pdf_started = time.perf_counter()
        pdf_rows = _filter_suspect_records(_parse_pdf_tables_bytes(contents))
        metrics["pdf_tables_ms"] = int((time.perf_counter() - pdf_started) * 1000)
        metrics["pdf_table_items"] = len(pdf_rows)

    if not parsed_items and pdf_rows:
        parsed_items = pdf_rows
        selected_source = "pdf_tables"
        selected_text = selected_text or local_text

    if llm_chat_attempted and selected_source and selected_source != "llm":
        fallback_label = {
            "upload_docs": "texto bruto retornado no upload do LLM",
            "local": "parser local do arquivo",
            "pdf_tables": "parser local de tabelas PDF",
        }.get(selected_source, selected_source)
        warnings.append(f"Saida principal do LLM sem itens validos; usado fallback: {fallback_label}.")

    metrics["selected_source"] = selected_source or "none"
    metrics["selected_items"] = len(parsed_items)
    metrics["selected_items_raw"] = len(parsed_items)
    metrics["parsing_total_ms"] = int((time.perf_counter() - total_started) * 1000)

    compact_summary = {"originais": len(parsed_items), "resultantes": len(parsed_items), "removidos": 0, "atualizados_grades": 0}
    compact_import_batch = getattr(service, "compact_import_batch", None)
    if parsed_items and callable(compact_import_batch):
        try:
            compacted_items, compact_summary = compact_import_batch(parsed_items)  # type: ignore[misc]
            if compacted_items:
                parsed_items = compacted_items
            if compact_summary.get("atualizados_grades", 0) > 0:
                warnings.append(
                    "Grades detectadas no romaneio e compactadas automaticamente na lista importada."
                )
        except Exception as exc:
            logger.warning("Falha ao compactar grades do lote importado (job_id=%s): %s", job_id, exc)
            warnings.append(f"Falha ao compactar grades automaticamente: {exc}")
    metrics["import_compact_removed"] = int(compact_summary.get("removidos", 0) or 0)
    metrics["import_compact_groups"] = int(compact_summary.get("atualizados_grades", 0) or 0)
    metrics["selected_items"] = len(parsed_items)

    content_to_save = selected_text or llm_text or upload_docs_text or local_text
    if _looks_like_binary_blob(content_to_save):
        content_to_save = ""
    if not content_to_save and parsed_items:
        content_to_save = _products_to_text(parsed_items)

    if not content_to_save and not parsed_items:
        update_import_job(
            job_id,
            "error",
            error="Nao foi possivel extrair conteudo util do arquivo enviado.",
            metrics=metrics,
        )
        return

    try:
        persist_started = time.perf_counter()
        local_file = save_romaneio_text(data_dir, content_to_save)
        if parsed_items:
            service.create_many(parsed_items)  # type: ignore[attr-defined]
        else:
            warnings.append("Nenhum item de produto foi detectado no arquivo.")
        metrics["persist_ms"] = int((time.perf_counter() - persist_started) * 1000)
        metrics["total_ms"] = int((time.perf_counter() - total_started) * 1000)
        logger.info(
            "romaneio job %s finalizado em %sms (source=%s, upload_ms=%s, chat_calls=%s, chat_ms=%s, items=%s)",
            job_id,
            metrics["total_ms"],
            metrics["selected_source"],
            metrics.get("llm_upload_ms", 0),
            metrics.get("llm_chat_calls", 0),
            metrics.get("llm_chat_total_ms", 0),
            len(parsed_items),
        )

        result = ImportRomaneioResultResponse(
            status="ok",
            saved_file=saved_file,
            local_file=str(local_file),
            content=content_to_save,
            warnings=warnings,
            total_itens=len(parsed_items),
            metrics=metrics,
        )
        update_import_job(job_id, "completed", result=result, metrics=metrics)
    except Exception as exc:
        update_import_job(job_id, "error", error=f"Falha ao importar romaneio: {exc}", metrics=metrics)
