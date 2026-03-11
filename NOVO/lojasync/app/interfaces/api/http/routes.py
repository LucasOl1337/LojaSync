from __future__ import annotations

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
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.domain.grades.parser import parse_grade_extraction
from app.domain.products.entities import Product
from app.interfaces.api.schemas.products import (
    BrandPayload,
    BrandsResponse,
    MarginSettingsPayload,
    MarginSettingsResponse,
    ProductItemResponse,
    ProductListResponse,
    ProductPatchPayload,
    ProductPayload,
    ProductResponse,
    TotalsInfo,
    TotalsResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)
_CATALOG_SIZES = [
    "U",
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
    "XXG",
    "G1",
    "G2",
    "G3",
    "34",
    "36",
    "38",
    "40",
    "42",
    "44",
    "46",
    "48",
    "50",
    "52",
    "54",
    "56",
]


class BulkActionPayload(BaseModel):
    valor: str = ""


class ReorderPayload(BaseModel):
    keys: list[str] = Field(default_factory=list)


class SnapshotProductPayload(BaseModel):
    nome: str = ""
    codigo: str = ""
    codigo_original: str | None = None
    quantidade: int = Field(0, ge=0)
    preco: str = ""
    categoria: str = ""
    marca: str = ""
    preco_final: str | None = None
    descricao_completa: str | None = None
    grades: list[dict[str, Any]] | None = None
    cores: list[dict[str, Any]] | None = None
    timestamp: str | None = None


class SnapshotRestorePayload(BaseModel):
    items: list[SnapshotProductPayload] = Field(default_factory=list)


class SnapshotRestoreResponse(BaseModel):
    total: int


class FormatCodesPayload(BaseModel):
    remover_prefixo5: bool = False
    remover_zeros_a_esquerda: bool = False
    ultimos_digitos: int | None = Field(default=None, ge=1, le=50)
    primeiros_digitos: int | None = Field(default=None, ge=1, le=50)
    remover_ultimos_numeros: int | None = Field(default=None, ge=1, le=50)
    remover_primeiros_numeros: int | None = Field(default=None, ge=1, le=50)


class FormatCodesResponse(BaseModel):
    total: int
    alterados: int
    prefixo: str | None = None


class RestoreCodesResponse(BaseModel):
    total: int
    restaurados: int


class JoinGradesResponse(BaseModel):
    originais: int
    resultantes: int
    removidos: int
    atualizados_grades: int


class CreateSetPayload(BaseModel):
    key_a: str = Field(..., min_length=1)
    key_b: str = Field(..., min_length=1)


class CreateSetResponse(BaseModel):
    created: int
    removed: int
    remaining_a: int
    remaining_b: int


class MarginPayload(BaseModel):
    percentual: float | None = Field(default=None, gt=0)
    margem: float | None = Field(default=None, gt=0)


class MarginResponse(BaseModel):
    total_atualizados: int
    margem_utilizada: float
    percentual_utilizado: float


class TargetPoint(BaseModel):
    x: int
    y: int


class TargetsPayload(BaseModel):
    title: str | None = None
    byte_empresa_posicao: TargetPoint | None = None
    campo_descricao: TargetPoint | None = None
    tres_pontinhos: TargetPoint | None = None


class TargetsResponse(BaseModel):
    title: str | None = None
    byte_empresa_posicao: TargetPoint | None = None
    campo_descricao: TargetPoint | None = None
    tres_pontinhos: TargetPoint | None = None


class TargetCapturePayload(BaseModel):
    target: str = Field(..., min_length=1)


class TargetCaptureResponse(BaseModel):
    target: str
    point: TargetPoint


class ImproveDescriptionPayload(BaseModel):
    remover_numeros: bool = False
    remover_especiais: bool = False
    remover_termos: list[str] = Field(default_factory=list)


class ImproveDescriptionResponse(BaseModel):
    total: int
    modificados: int


class ImportRomaneioStartResponse(BaseModel):
    job_id: str


class ImportRomaneioStatusResponse(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None


class ImportRomaneioResultResponse(BaseModel):
    status: str
    saved_file: str | None = None
    local_file: str | None = None
    content: str | None = None
    warnings: list[str] = Field(default_factory=list)
    total_itens: int = 0


class GradeConfigPayload(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    buttons: dict[str, TargetPoint] | None = None
    first_quant_cell: TargetPoint | None = None
    second_quant_cell: TargetPoint | None = None
    row_height: int | None = None
    model_index: int | None = None
    model_hotkey: str | None = None
    erp_size_order: list[str] | None = None


class GradeRunPayload(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    grades: dict[str, int] | None = None
    grades_json: str | None = None
    model_index: int | None = None
    pause: float | None = None
    speed: float | None = None


class GradesBatchPayload(BaseModel):
    tasks: list[GradeRunPayload] = Field(default_factory=list)
    pause: float | None = None
    speed: float | None = None


class GradeExtractionProduct(BaseModel):
    codigo: str | None = None
    nome: str | None = None
    grades: dict[str, int] = Field(default_factory=dict)
    atualizado: bool
    warnings: list[str] = Field(default_factory=list)


class GradeExtractionResponse(BaseModel):
    status: str
    total_itens: int
    total_atualizados: int
    warnings: list[str] = Field(default_factory=list)
    itens: list[GradeExtractionProduct] = Field(default_factory=list)
    content: str | None = None


class GradeExtractionStatusResponse(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: float | None = None
    error: str | None = None


class GradeExtractionStartResponse(BaseModel):
    job_id: str


def _service(request: Request):
    return request.app.state.container["product_service"]


def _automation(request: Request):
    return request.app.state.container["automation_service"]


def _to_response(product: Product) -> ProductResponse:
    grades = (
        [{"tamanho": item.tamanho, "quantidade": int(item.quantidade)} for item in (product.grades or [])]
        if product.grades
        else None
    )
    cores = (
        [{"cor": item.cor, "quantidade": int(item.quantidade)} for item in (product.cores or [])]
        if product.cores
        else None
    )
    return ProductResponse(
        nome=product.nome,
        codigo=product.codigo,
        codigo_original=product.codigo_original,
        quantidade=product.quantidade,
        preco=product.preco,
        categoria=product.categoria,
        marca=product.marca,
        preco_final=product.preco_final,
        descricao_completa=product.descricao_completa,
        grades=grades,
        cores=cores,
        timestamp=product.timestamp,
        ordering_key=product.ordering_key(),
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.websocket("/ws/ui")
async def ui_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "ui.connected", "ts": time.time()})
    try:
        while True:
            # The current frontend sends ping text periodically.
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


_IMPORT_JOB_STAGES = {
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

_GRADE_JOB_STAGES = {
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


def _create_import_job() -> ImportRomaneioStatusResponse:
    now = time.time()
    job = ImportRomaneioStatusResponse(
        job_id=uuid.uuid4().hex,
        stage="pending",
        message=_IMPORT_JOB_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    with _import_lock:
        _import_jobs[job.job_id] = job
    return job


def _update_import_job(
    job_id: str,
    stage: str,
    *,
    message: str | None = None,
    error: str | None = None,
    result: ImportRomaneioResultResponse | None = None,
) -> None:
    with _import_lock:
        job = _import_jobs.get(job_id)
        if job is None:
            return
        job.stage = stage
        job.message = message or _IMPORT_JOB_STAGES.get(stage, stage)
        job.updated_at = time.time()
        if error is not None:
            job.error = error
        if result is not None or stage == "completed":
            job.completed_at = job.updated_at
        if result is not None:
            _import_results[job_id] = result


def _create_grade_job() -> GradeExtractionStatusResponse:
    now = time.time()
    job = GradeExtractionStatusResponse(
        job_id=uuid.uuid4().hex,
        stage="pending",
        message=_GRADE_JOB_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    with _grade_lock:
        _grade_jobs[job.job_id] = job
    return job


def _update_grade_job(
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
        job.message = message or _GRADE_JOB_STAGES.get(stage, stage)
        job.updated_at = time.time()
        if error is not None:
            job.error = error
        if result is not None or stage == "completed":
            job.completed_at = job.updated_at
        if result is not None:
            _grade_results[job_id] = result


def _llm_base_url() -> str:
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = os.getenv("LLM_PORT", "8002")
    return os.getenv("LLM_BASE_URL", f"http://{host}:{port}")


def _llm_timeout_seconds() -> float:
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
    normalized = normalized.replace("c\u00f3digo", "codigo")
    normalized = normalized.replace("descri\u00e7\u00e3o", "descricao")
    normalized = normalized.replace("pre\u00e7o", "preco")
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


def _build_product(codigo: Any, nome: Any, quantidade: Any, preco: Any) -> Product:
    code = str(codigo or "").strip()
    name = str(nome or "").strip()
    if len(code) > 80:
        code = code[:80].strip()
    if len(name) > 220:
        name = name[:220].strip()
    return Product(
        nome=name,
        codigo=code,
        codigo_original=code,
        quantidade=_parse_qty(quantidade),
        preco=_normalize_price(preco),
        categoria="",
        marca="",
        preco_final=None,
        descricao_completa=None,
    )


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


def _save_romaneio_text(data_dir: Path, content: str) -> Path:
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


def _extract_json_items(text: str) -> list[dict[str, Any]]:
    payload: Any = None
    raw = (text or "").strip()
    try:
        if raw.startswith("{") or raw.startswith("["):
            payload = json.loads(raw)
    except Exception:
        payload = None

    if payload is None:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", text or "", flags=re.IGNORECASE | re.DOTALL)
        for block in blocks:
            try:
                payload = json.loads(block)
                break
            except Exception:
                continue

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
    desc_keys = ("descricao", "description", "produto", "nome", "item")
    qty_keys = ("quantidade", "qtd", "qtde", "qde", "quantity", "qty")
    price_keys = ("preco", "price", "valor", "unit_price", "unitario")

    for item in items:
        lower = _map_keys_lower(item)

        def _pick(keys: tuple[str, ...]) -> Any:
            for key in keys:
                if key in lower:
                    return lower[key]
            return None

        codigo = str(_pick(code_keys) or "").strip()
        nome = str(_pick(desc_keys) or "").strip()
        if not codigo or not _has_digits(codigo) or not nome:
            continue
        records.append(_build_product(codigo, nome, _pick(qty_keys), _pick(price_keys)))
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
    dedupe: set[tuple[str, str, int, str]] = set()
    for record in records or []:
        if not _is_plausible_product(record):
            continue
        product = _build_product(
            record.codigo,
            record.nome,
            record.quantidade,
            record.preco,
        )
        key = (
            product.codigo.strip().lower(),
            product.nome.strip().lower(),
            int(product.quantidade),
            (product.preco or "").strip(),
        )
        if key in dedupe:
            continue
        dedupe.add(key)
        filtered.append(product)
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
        f"{_llm_base_url()}/api/chat",
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


def _run_grade_extraction_job(
    *,
    job_id: str,
    contents: bytes,
    filename: str,
    content_type: str | None,
    service: object,
) -> None:
    warnings: list[str] = []
    llm_text = ""

    _update_grade_job(job_id, "uploading")
    try:
        timeout = httpx.Timeout(_llm_timeout_seconds(), connect=10.0)
        files = {
            "files": (
                filename or "nota_fiscal",
                contents,
                content_type or "application/octet-stream",
            )
        }
        with httpx.Client(timeout=timeout) as client:
            upload_response = client.post(
                f"{_llm_base_url()}/api/upload",
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

            _update_grade_job(job_id, "processing")
            chunks = _split_text_chunks(
                upload_docs_text,
                max_chars=_coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000),
            )
            if chunks:
                parts: list[str] = []
                total = len(chunks)
                for idx, chunk in enumerate(chunks, start=1):
                    _update_grade_job(
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
                _update_grade_job(
                    job_id,
                    "processing",
                    message="Processando imagens com servico LLM",
                )
                llm_text, _ = _post_llm_chat(
                    client,
                    job_id=job_id,
                    mode="grade_extractor",
                    message="",
                    documents=[],
                    images=images,
                )
            else:
                warnings.append("Upload do LLM nao retornou documentos ou imagens.")
    except Exception as exc:
        logger.warning("Falha no pipeline LLM de grades (job_id=%s): %s", job_id, exc)
        warnings.append(f"Falha ao processar grades com o servico LLM: {exc}")

    _update_grade_job(job_id, "parsing")
    parsed_items, parser_warnings = parse_grade_extraction(llm_text, allowed_sizes=_CATALOG_SIZES)
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
    _update_grade_job(job_id, "completed", result=result)


def _run_import_job(
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

    _update_import_job(job_id, "uploading")
    upload_data: dict[str, Any] = {}

    try:
        timeout = httpx.Timeout(_llm_timeout_seconds(), connect=10.0)
        files = {
            "files": (
                filename or "romaneio",
                contents,
                content_type or "application/octet-stream",
            )
        }
        with httpx.Client(timeout=timeout) as client:
            upload_response = client.post(
                f"{_llm_base_url()}/api/upload",
                files=files,
                headers={"X-Job-Id": job_id},
            )
            upload_response.raise_for_status()
            parsed_upload: Any = upload_response.json()
            if isinstance(parsed_upload, dict):
                upload_data = parsed_upload

            upload_errors = upload_data.get("errors") if isinstance(upload_data.get("errors"), list) else []
            warnings.extend([str(item) for item in upload_errors if str(item).strip()])

            documents = [doc for doc in (upload_data.get("documents") or []) if isinstance(doc, dict)]
            images = [img for img in (upload_data.get("images") or []) if isinstance(img, dict)]
            upload_docs_text = "\n\n".join(str(doc.get("content") or "") for doc in documents).strip()

            _update_import_job(job_id, "processing")
            chunks = _split_text_chunks(
                upload_docs_text,
                max_chars=_coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000),
            )
            if chunks:
                parts: list[str] = []
                total = len(chunks)
                for idx, chunk in enumerate(chunks, start=1):
                    _update_import_job(
                        job_id,
                        "processing",
                        message=f"Processando texto {idx}/{total} com servico LLM",
                    )
                    chat_text, chat_saved = _post_llm_chat(
                        client,
                        job_id=job_id,
                        message="",
                        documents=[{"name": f"parte_{idx}", "content": chunk}],
                        images=images if idx == 1 else [],
                    )
                    if chat_saved and not saved_file:
                        saved_file = chat_saved
                    if chat_text:
                        parts.append(chat_text)
                llm_text = "\n\n".join(parts).strip()
            elif images:
                _update_import_job(
                    job_id,
                    "processing",
                    message="Processando imagens com servico LLM",
                )
                chat_text, chat_saved = _post_llm_chat(
                    client,
                    job_id=job_id,
                    message="",
                    documents=[],
                    images=images,
                )
                if chat_saved and not saved_file:
                    saved_file = chat_saved
                llm_text = chat_text
            else:
                warnings.append("Upload do LLM nao retornou documentos ou imagens.")
    except Exception as exc:
        logger.warning("Falha no pipeline de importacao LLM (job_id=%s): %s", job_id, exc)
        warnings.append(f"Falha ao processar com o servico LLM: {exc}")

    local_text, local_warnings = _decode_text_content(contents, filename, content_type)
    warnings.extend(local_warnings)

    _update_import_job(job_id, "parsing")
    selected_source = ""
    selected_text = ""
    parsed_items: list[Product] = []

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

    if not parsed_items:
        pdf_rows = _filter_suspect_records(_parse_pdf_tables_bytes(contents))
        if pdf_rows:
            parsed_items = pdf_rows
            selected_source = "pdf_tables"
            warnings.append("Fallback usado: tabelas extraidas diretamente do PDF.")

    if selected_source and selected_source != "llm":
        fallback_label = {
            "upload_docs": "texto bruto retornado no upload do LLM",
            "local": "parser local do arquivo",
            "pdf_tables": "parser local de tabelas PDF",
        }.get(selected_source, selected_source)
        warnings.append(f"Saida principal do LLM sem itens validos; usado fallback: {fallback_label}.")

    content_to_save = selected_text or llm_text or upload_docs_text or local_text
    if _looks_like_binary_blob(content_to_save):
        content_to_save = ""

    if not content_to_save and not parsed_items:
        _update_import_job(
            job_id,
            "error",
            error="Nao foi possivel extrair conteudo util do arquivo enviado.",
        )
        return

    try:
        local_file = _save_romaneio_text(data_dir, content_to_save)
        if parsed_items:
            service.create_many(parsed_items)  # type: ignore[attr-defined]
        else:
            warnings.append("Nenhum item de produto foi detectado no arquivo.")

        result = ImportRomaneioResultResponse(
            status="ok",
            saved_file=saved_file,
            local_file=str(local_file),
            content=content_to_save,
            warnings=warnings,
            total_itens=len(parsed_items),
        )
        _update_import_job(job_id, "completed", result=result)
    except Exception as exc:
        _update_import_job(job_id, "error", error=f"Falha ao importar romaneio: {exc}")


def _as_target_point(value: Any) -> TargetPoint | None:
    if isinstance(value, dict) and "x" in value and "y" in value:
        try:
            return TargetPoint(x=int(value["x"]), y=int(value["y"]))
        except Exception:
            return None
    return None


def _build_targets_response(payload: dict[str, Any]) -> TargetsResponse:
    return TargetsResponse(
        title=str(payload.get("title")).strip() if isinstance(payload.get("title"), str) and payload.get("title") else None,
        byte_empresa_posicao=_as_target_point(payload.get("byte_empresa_posicao")),
        campo_descricao=_as_target_point(payload.get("campo_descricao")),
        tres_pontinhos=_as_target_point(payload.get("tres_pontinhos")),
    )

@router.get("/products", response_model=ProductListResponse)
async def list_products(request: Request) -> ProductListResponse:
    products = _service(request).list_products()
    return ProductListResponse(items=[_to_response(item) for item in products])


@router.get("/catalog/sizes")
async def catalog_sizes() -> dict[str, list[str]]:
    return {"sizes": _CATALOG_SIZES}


@router.post("/products", response_model=ProductItemResponse, status_code=201)
async def create_product(payload: ProductPayload, request: Request) -> ProductItemResponse:
    created = _service(request).create_product(
        Product(
            nome=payload.nome,
            codigo=payload.codigo,
            quantidade=payload.quantidade,
            preco=payload.preco,
            categoria=payload.categoria,
            marca=payload.marca,
            preco_final=payload.preco_final,
            descricao_completa=payload.descricao_completa,
            codigo_original=payload.codigo,
            grades=payload.grades,
            cores=payload.cores,
        )
    )
    return ProductItemResponse(item=_to_response(created))


@router.patch("/products/{ordering_key:path}", response_model=ProductItemResponse)
async def patch_product(ordering_key: str, payload: ProductPatchPayload, request: Request) -> ProductItemResponse:
    updated = _service(request).update_product(
        ordering_key,
        payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return ProductItemResponse(item=_to_response(updated))


@router.delete("/products")
async def clear_products(request: Request) -> dict[str, int]:
    removed = _service(request).clear_products()
    return {"removed": removed}


@router.delete("/products/{ordering_key:path}")
async def delete_product(ordering_key: str, request: Request) -> dict[str, str]:
    success = _service(request).delete_product(ordering_key)
    if not success:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return {"status": "deleted", "ordering_key": ordering_key}


@router.get("/brands", response_model=BrandsResponse)
async def list_brands(request: Request) -> BrandsResponse:
    return BrandsResponse(marcas=_service(request).list_brands())


@router.post("/brands", response_model=BrandsResponse)
async def add_brand(payload: BrandPayload, request: Request) -> BrandsResponse:
    return BrandsResponse(marcas=_service(request).add_brand(payload.nome))


@router.get("/settings/margin", response_model=MarginSettingsResponse)
async def get_margin(request: Request) -> MarginSettingsResponse:
    margin = _service(request).get_default_margin()
    percentual = (margin - 1) * 100
    return MarginSettingsResponse(margem=margin, percentual=percentual)


@router.post("/settings/margin", response_model=MarginSettingsResponse)
async def set_margin(payload: MarginSettingsPayload, request: Request) -> MarginSettingsResponse:
    margin = _service(request).set_default_margin(1 + payload.percentual / 100.0)
    return MarginSettingsResponse(margem=margin, percentual=payload.percentual)


@router.get("/totals", response_model=TotalsResponse)
async def get_totals(request: Request) -> TotalsResponse:
    summary = _service(request).get_summary()
    return TotalsResponse(
        atual=TotalsInfo(
            quantidade=summary.atual.quantidade,
            custo=summary.atual.custo,
            venda=summary.atual.venda,
        ),
        historico=TotalsInfo(
            quantidade=summary.historico.quantidade,
            custo=summary.historico.custo,
            venda=summary.historico.venda,
        ),
        tempo_economizado=summary.metrics.tempo_economizado,
        caracteres_digitados=summary.metrics.caracteres_digitados,
    )


@router.post("/actions/apply-category")
async def apply_category(payload: BulkActionPayload, request: Request) -> dict[str, object]:
    total = _service(request).apply_category(payload.valor)
    return {"status": "categoria aplicada", "categoria": payload.valor, "total": total}


@router.post("/actions/apply-brand")
async def apply_brand(payload: BulkActionPayload, request: Request) -> dict[str, object]:
    total = _service(request).apply_brand(payload.valor)
    return {"status": "marca aplicada", "marca": payload.valor, "total": total}


@router.post("/actions/join-duplicates")
async def join_duplicates(request: Request) -> dict[str, int]:
    return _service(request).join_duplicates()


@router.post("/actions/reorder")
async def reorder_products(payload: ReorderPayload, request: Request) -> dict[str, int]:
    total = _service(request).reorder_by_keys(payload.keys)
    return {"total": total}


@router.post("/actions/join-grades")
async def join_grades(request: Request) -> JoinGradesResponse:
    result = _service(request).join_with_grades()
    return JoinGradesResponse(**result)


@router.post("/actions/restore-snapshot", response_model=SnapshotRestoreResponse)
async def restore_snapshot(payload: SnapshotRestorePayload, request: Request) -> SnapshotRestoreResponse:
    products = [Product.from_dict(item.model_dump()) for item in payload.items]
    total = _service(request).restore_snapshot(products)
    return SnapshotRestoreResponse(total=total)


@router.post("/actions/format-codes", response_model=FormatCodesResponse)
async def format_codes(payload: FormatCodesPayload, request: Request) -> FormatCodesResponse:
    result = _service(request).format_codes(payload.model_dump())
    return FormatCodesResponse(**result)


@router.post("/actions/restore-original-codes", response_model=RestoreCodesResponse)
async def restore_original_codes(request: Request) -> RestoreCodesResponse:
    result = _service(request).restore_original_codes()
    return RestoreCodesResponse(**result)


@router.post("/actions/apply-margin", response_model=MarginResponse)
async def apply_margin(payload: MarginPayload, request: Request) -> MarginResponse:
    margin_factor = payload.margem if payload.margem is not None else None
    if margin_factor is None and payload.percentual is not None:
        margin_factor = 1 + payload.percentual / 100.0
    if margin_factor is None or margin_factor <= 0:
        raise HTTPException(status_code=400, detail="Margem invalida")
    total = _service(request).apply_margin_to_products(margin_factor)
    percentual = (margin_factor - 1) * 100
    return MarginResponse(
        total_atualizados=total,
        margem_utilizada=margin_factor,
        percentual_utilizado=percentual,
    )


@router.post("/actions/create-set", response_model=CreateSetResponse)
async def create_set(payload: CreateSetPayload, request: Request) -> CreateSetResponse:
    result = _service(request).create_set_by_keys(payload.key_a, payload.key_b)
    if not result:
        raise HTTPException(status_code=400, detail="Nao foi possivel criar o conjunto selecionado.")
    return CreateSetResponse(**result)


@router.post("/actions/improve-descriptions", response_model=ImproveDescriptionResponse)
async def improve_descriptions(payload: ImproveDescriptionPayload, request: Request) -> ImproveDescriptionResponse:
    has_terms = bool([term for term in payload.remover_termos if str(term).strip()])
    if not payload.remover_numeros and not payload.remover_especiais and not has_terms:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma opcao de limpeza.")
    result = _service(request).improve_descriptions(
        payload.remover_numeros,
        payload.remover_especiais,
        payload.remover_termos,
    )
    return ImproveDescriptionResponse(**result)


@router.post("/actions/parser-grades", response_model=GradeExtractionStartResponse)
async def start_grade_parser(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> GradeExtractionStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou invalido")
    job = _create_grade_job()
    _update_grade_job(job.job_id, "uploading")
    background.add_task(
        _run_grade_extraction_job,
        job_id=job.job_id,
        contents=contents,
        filename=file.filename or "nota_fiscal",
        content_type=file.content_type,
        service=request.app.state.container["product_service"],
    )
    return GradeExtractionStartResponse(job_id=job.job_id)


@router.get("/actions/parser-grades/status/{job_id}", response_model=GradeExtractionStatusResponse)
async def parser_grades_status(job_id: str) -> GradeExtractionStatusResponse:
    with _grade_lock:
        job = _grade_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@router.get("/actions/parser-grades/result/{job_id}", response_model=GradeExtractionResponse)
async def parser_grades_result(job_id: str) -> GradeExtractionResponse:
    with _grade_lock:
        job = _grade_jobs.get(job_id)
        result = _grade_results.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponivel")
    return result


@router.delete("/actions/parser-grades/status/{job_id}")
async def parser_grades_cleanup(job_id: str) -> dict[str, str]:
    with _grade_lock:
        exists = job_id in _grade_jobs or job_id in _grade_results
        _grade_jobs.pop(job_id, None)
        _grade_results.pop(job_id, None)
    if not exists:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}


@router.get("/automation/targets", response_model=TargetsResponse)
async def get_targets(request: Request) -> TargetsResponse:
    return _build_targets_response(_automation(request).load_targets())


@router.post("/automation/targets", response_model=TargetsResponse)
async def set_targets(payload: TargetsPayload, request: Request) -> TargetsResponse:
    data = payload.model_dump(exclude_none=True)
    saved = _automation(request).save_targets(data)
    return _build_targets_response(saved)


@router.post("/automation/targets/capture", response_model=TargetCaptureResponse)
async def capture_target(payload: TargetCapturePayload, request: Request) -> TargetCaptureResponse:
    try:
        captured = _automation(request).capture_target(payload.target)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    point = _as_target_point(captured.get("point"))
    if point is None:
        raise HTTPException(status_code=500, detail="Falha ao capturar coordenadas")
    return TargetCaptureResponse(target=payload.target, point=point)


@router.get("/automation/status")
async def automation_status(request: Request) -> dict[str, str | None]:
    return _automation(request).status()


@router.post("/automation/execute")
async def automation_execute(request: Request) -> dict[str, str]:
    try:
        return _automation(request).execute()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/cancel")
async def automation_cancel(request: Request) -> dict[str, str]:
    return _automation(request).cancel()


@router.get("/automation/agents")
async def automation_agents(request: Request) -> dict[str, list[dict[str, Any]]]:
    return _automation(request).agents()


@router.get("/automation/grades/config")
async def grades_config_get(request: Request) -> dict[str, Any]:
    return {"config": _automation(request).get_gradebot_config()}


@router.post("/automation/grades/config")
async def grades_config_set(payload: GradeConfigPayload, request: Request) -> dict[str, Any]:
    config = _automation(request).set_gradebot_config(payload.model_dump(exclude_none=True))
    return {"config": config}


@router.post("/automation/grades/run")
async def grades_run(payload: GradeRunPayload, request: Request) -> dict[str, str]:
    try:
        return _automation(request).run_gradebot(
            grades=payload.grades,
            grades_json=payload.grades_json,
            model_index=payload.model_index,
            pause=payload.pause,
            speed=payload.speed,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/grades/batch")
async def grades_batch(payload: GradesBatchPayload, request: Request) -> dict[str, Any]:
    tasks = [task.model_dump(exclude_none=True) for task in payload.tasks]
    try:
        return _automation(request).run_gradebot_batch(
            tasks=tasks,
            pause=payload.pause,
            speed=payload.speed,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/automation/grades/stop")
async def grades_stop(request: Request) -> dict[str, str]:
    return _automation(request).stop_gradebot()


@router.get("/actions/export-json")
async def export_json(request: Request) -> FileResponse:
    paths = request.app.state.container["paths"]
    return FileResponse(paths.products_active_file, media_type="application/json", filename="products_active.jsonl")


@router.post("/actions/import-romaneio", response_model=ImportRomaneioStartResponse)
async def import_romaneio(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> ImportRomaneioStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou invalido")

    job = _create_import_job()
    _update_import_job(job.job_id, "uploading")
    container = request.app.state.container
    background.add_task(
        _run_import_job,
        job_id=job.job_id,
        contents=contents,
        filename=file.filename or "romaneio",
        content_type=file.content_type,
        service=container["product_service"],
        data_dir=container["paths"].data_dir,
    )
    return ImportRomaneioStartResponse(job_id=job.job_id)


@router.get("/actions/import-romaneio/status/{job_id}", response_model=ImportRomaneioStatusResponse)
async def import_romaneio_status(job_id: str) -> ImportRomaneioStatusResponse:
    with _import_lock:
        job = _import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return job


@router.get("/actions/import-romaneio/result/{job_id}", response_model=ImportRomaneioResultResponse)
async def import_romaneio_result(job_id: str) -> ImportRomaneioResultResponse:
    with _import_lock:
        job = _import_jobs.get(job_id)
        result = _import_results.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponivel")
    return result


@router.delete("/actions/import-romaneio/status/{job_id}")
async def import_romaneio_cleanup(job_id: str) -> dict[str, str]:
    with _import_lock:
        exists = job_id in _import_jobs or job_id in _import_results
        _import_jobs.pop(job_id, None)
        _import_results.pop(job_id, None)
    if not exists:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    return {"status": "removed", "job_id": job_id}
