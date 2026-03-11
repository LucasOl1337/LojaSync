"""Backend provisório para o protótipo web do LojaSync.

Objetivo inicial:
- Fornecer uma API local simples (FastAPI) para gerenciar a lista de produtos
  exibidas no protótipo web.
- Replicar as operações básicas existentes na aplicação desktop:
  • Inserir produtos manualmente (botão "Salvar Dados" ou tecla Enter).
  • Aplicar categoria/marca atuais a toda a lista.
  • Juntar itens repetidos (same nome/código/preço somando quantidades).
  • Limpar lista.
- Manter persistência temporária em memória; em etapas futuras integraremos com
  arquivos JSONL/estrutura real. Este módulo já define pontos de extensão para
  persistência permanente se necessário.

Execução:
    uvicorn webapp.backend:app --reload --port 8000
ou usar ``webapp/launcher.py`` para orquestrar backend e frontend.
"""
from __future__ import annotations

import asyncio
import logging
import os
import json
import base64
import threading
from datetime import datetime
import io
from typing import Any, Dict, List, Optional, Tuple, Set
import importlib.util
import sys
from pathlib import Path

import httpx
import uuid
import time
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator, validator

from .database import ProductRecord, product_db, SIZES_CATALOG, GradeItem, CorItem, DATA_DIR
from .remote_manager import build_manager_from_env
from .sequencias import (
    iniciar_sequencia_basica,
    obter_status as obter_status_sequencia,
    cancelar_sequencia_basica,
    preparar_produtos_para_automacao,
)
from modules.core.file_manager import load_targets, save_targets
from modules.parsers.parser_grades import parse_grade_extraction

logger = logging.getLogger(__name__)

try:
    import pyautogui
except ImportError:  # pragma: no cover - ambientes sem pyautogui
    pyautogui = None  # type: ignore

lock = threading.RLock()


class GradeItemPayload(BaseModel):
    tamanho: str = Field(..., min_length=1)
    quantidade: int = Field(0, ge=0)

    @validator("tamanho")
    def _normalize_tamanho(cls, value: str) -> str:  # type: ignore[misc]
        return value.strip()


class CorItemPayload(BaseModel):
    cor: str = Field(..., min_length=1)
    quantidade: int = Field(0, ge=0)

    @validator("cor")
    def _normalize_cor(cls, value: str) -> str:  # type: ignore[misc]
        return value.strip()


class ProductPayload(BaseModel):
    nome: str = Field(..., min_length=1)
    codigo: str = Field("", min_length=0)
    quantidade: int = Field(1, ge=1)
    preco: str = Field(..., min_length=1)
    categoria: str = Field("", min_length=0)
    marca: str = Field("", min_length=0)
    preco_final: Optional[str] = None
    descricao_completa: Optional[str] = None
    grades: Optional[List[GradeItemPayload]] = None
    cores: Optional[List[CorItemPayload]] = None

    @validator("preco", "preco_final", pre=True, always=True)
    def _strip_values(cls, value):  # type: ignore[misc]
        if value is None:
            return value
        return str(value).strip()

    @validator("nome", "codigo", "categoria", "marca", pre=True, always=True)
    def _normalize_strings(cls, value):  # type: ignore[misc]
        if value is None:
            raise ValueError("campo obrigatório")
        return str(value).strip()


class BulkActionPayload(BaseModel):
    valor: str


class ProductResponse(BaseModel):
    nome: str
    codigo: str
    codigo_original: Optional[str] = None
    quantidade: int
    preco: str
    categoria: str
    marca: str
    preco_final: Optional[str] = None
    descricao_completa: Optional[str] = None
    grades: Optional[List[GradeItemPayload]] = None
    cores: Optional[List[CorItemPayload]] = None
    timestamp: datetime
    ordering_key: str

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class ProductListResponse(BaseModel):
    items: List[ProductResponse]


class ProductItemResponse(BaseModel):
    item: ProductResponse


class SnapshotProductPayload(BaseModel):
    nome: str = Field("", min_length=0)
    codigo: str = Field("", min_length=0)
    codigo_original: Optional[str] = None
    quantidade: int = Field(0, ge=0)
    preco: str = Field("", min_length=0)
    categoria: str = Field("", min_length=0)
    marca: str = Field("", min_length=0)
    preco_final: Optional[str] = None
    descricao_completa: Optional[str] = None
    grades: Optional[List[GradeItemPayload]] = None
    cores: Optional[List[CorItemPayload]] = None
    timestamp: datetime

    @validator("preco", "preco_final", pre=True, always=True)
    def _strip_prices(cls, value):  # type: ignore[misc]
        if value is None:
            return value
        return str(value).strip()

    @validator("nome", "codigo", "categoria", "marca", pre=True, always=True)
    def _normalize_strings(cls, value):  # type: ignore[misc]
        if value is None:
            return ""
        return str(value).strip()


class SnapshotRestorePayload(BaseModel):
    items: List[SnapshotProductPayload] = Field(default_factory=list)


class SnapshotRestoreResponse(BaseModel):
    total: int


def _to_response(record: ProductRecord) -> ProductResponse:
    grades = (
        [
            {"tamanho": getattr(g, "tamanho", str(getattr(g, "tamanho", ""))), "quantidade": int(getattr(g, "quantidade", 0))}
            for g in (record.grades or [])
        ]
        if record.grades
        else None
    )
    cores = (
        [
            {"cor": getattr(c, "cor", str(getattr(c, "cor", ""))), "quantidade": int(getattr(c, "quantidade", 0))}
            for c in (record.cores or [])
        ]
        if record.cores
        else None
    )
    return ProductResponse(
        nome=record.nome,
        codigo=record.codigo,
        quantidade=record.quantidade,
        preco=record.preco,
        categoria=record.categoria,
        marca=record.marca,
        codigo_original=record.codigo_original or record.codigo,
        preco_final=record.preco_final,
        descricao_completa=record.descricao_completa,
        grades=grades,
        cores=cores,
        timestamp=record.timestamp,
        ordering_key=f"{record.codigo.strip()}::{record.timestamp.isoformat()}",
    )


app = FastAPI(title="LojaSync Web Backend", version="0.1.0")
remote_agent_manager = build_manager_from_env()


class UIRealtimeHub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
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


ui_realtime_hub = UIRealtimeHub()


def schedule_broadcast_ui_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    payload: Dict[str, Any] = {"type": event_type, "ts": time.time()}
    if data:
        payload.update(data)
    loop.create_task(ui_realtime_hub.broadcast(payload))


LLM_HOST = os.getenv("LLM_HOST", "127.0.0.1")
LLM_PORT = os.getenv("LLM_PORT", "8002")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", f"http://{LLM_HOST}:{LLM_PORT}")
LLM_HTTP_TIMEOUT_SECONDS = float(os.getenv("LLM_HTTP_TIMEOUT_SECONDS", "900"))
DEFAULT_ROMANEIO_RETRY_PROMPT = (
    "A resposta anterior não trouxe itens válidos de produtos ou veio vazia. "
    "Reanalise o romaneio e retorne APENAS os itens. "
    "Formato aceito: JSON com chave 'items' (código/descricao/quantidade/preco/total) "
    "ou uma tabela com Code, Description, Quantity, Price e Total."
)


def _env_flag(name: str, default: str = "0") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _get_llm_trace_base_dir() -> Path:
    configured = os.getenv("LLM_TRACE_DIR")
    if configured:
        return Path(configured)
    return DATA_DIR / "llm_trace"


def _write_llm_trace_text(job_id: str, filename: str, text: str) -> None:
    if not _env_flag("LLM_TRACE_DUMP", "0"):
        return
    try:
        base = _get_llm_trace_base_dir() / job_id
        base.mkdir(parents=True, exist_ok=True)
        (base / filename).write_text(text or "", encoding="utf-8")
    except Exception:
        logger.exception(
            "llm trace: falha ao salvar arquivo (job=%s, filename=%s)",
            job_id,
            filename,
        )


def _write_llm_trace_json(job_id: str, filename: str, data: Any) -> None:
    if not _env_flag("LLM_TRACE_DUMP", "0"):
        return
    try:
        base = _get_llm_trace_base_dir() / job_id
        base.mkdir(parents=True, exist_ok=True)
        (base / filename).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.exception(
            "llm trace: falha ao salvar json (job=%s, filename=%s)",
            job_id,
            filename,
        )


def _sanitize_images_for_trace(images: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(images, list):
        return out
    for img in images:
        if not isinstance(img, dict):
            continue
        out.append(
            {
                "name": img.get("name"),
                "mime": img.get("mime"),
                "data_chars": len(str(img.get("data") or "")),
            }
        )
    return out


def _sanitize_documents_for_trace(documents: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(documents, list):
        return out
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        out.append(
            {
                "name": doc.get("name"),
                "content_chars": len(str(doc.get("content") or "")),
            }
        )
    return out


def _coerce_int_env(name: str, default: int) -> int:
    try:
        raw = str(os.getenv(name, str(default))).strip()
        if not raw:
            return default
        return int(raw)
    except Exception:
        return default


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return (text or "").strip()
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."


def _join_text_chunks(chunks: List[str], max_chars: int) -> str:
    if not chunks:
        return ""
    collected: List[str] = []
    total = 0
    for chunk in chunks:
        if not chunk:
            continue
        piece = str(chunk)
        if max_chars > 0 and total + len(piece) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            collected.append(piece[:remaining])
            total = max_chars
            break
        collected.append(piece)
        total += len(piece)
    return "\n\n".join(p for p in collected if p).strip()


def _build_retry_document_text(
    text_blobs: List[str], documents: Any, *, max_chars: int
) -> str:
    chunks: List[str] = []
    for chunk in text_blobs or []:
        if chunk:
            chunks.append(str(chunk))
    if not chunks and isinstance(documents, list):
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = str(doc.get("content") or "").strip()
            if content:
                chunks.append(content)
    return _join_text_chunks(chunks, max_chars)


def _render_pdf_images_for_retry(
    pdf_bytes: bytes, *, max_pages: int, zoom: float
) -> List[Dict[str, Any]]:
    if not pdf_bytes:
        return []
    try:
        import fitz  # type: ignore
    except Exception:
        return []
    images: List[Dict[str, Any]] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        mat = fitz.Matrix(zoom, zoom)
        for page_index, page in enumerate(doc, start=1):
            if page_index > max_pages:
                break
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            b64_data = base64.b64encode(img_bytes).decode("utf-8")
            images.append(
                {
                    "name": f"romaneio_retry#p{page_index}",
                    "data": b64_data,
                    "mime": "image/png",
                }
            )
    except Exception:
        logger.exception("romaneio retry: falha ao renderizar PDF em imagens")
    return images


def _get_llm_image_batches(images: Any) -> List[List[Dict[str, Any]]]:
    if not isinstance(images, list):
        return []
    imgs = [i for i in images if isinstance(i, dict)]
    if not imgs:
        return []
    batch_size = _coerce_int_env("LLM_IMAGE_BATCH_SIZE", 6)
    if batch_size <= 0:
        return [imgs]
    out: List[List[Dict[str, Any]]] = []
    for i in range(0, len(imgs), batch_size):
        out.append(imgs[i : i + batch_size])
    return out


def _select_images_for_text_chunk(images: Any, chunk_index: int) -> List[Dict[str, Any]]:
    if not isinstance(images, list):
        return []
    imgs = [i for i in images if isinstance(i, dict)]
    if not imgs:
        return []
    if not _env_flag("LLM_INCLUDE_IMAGES_WITH_TEXT", "0"):
        return []
    if _env_flag("LLM_IMAGES_FIRST_CHUNK_ONLY", "1") and chunk_index > 1:
        return []
    batch_size = _coerce_int_env("LLM_IMAGE_BATCH_SIZE", 6)
    if batch_size <= 0:
        return imgs
    return imgs[:batch_size]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/ui")
async def ui_ws(websocket: WebSocket) -> None:
    await ui_realtime_hub.connect(websocket)
    try:
        await websocket.send_json({"type": "ui.connected", "ts": time.time()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ui_realtime_hub.disconnect(websocket)


# ---------------------------------------------------------------------------
# Import job tracking (romaneio)
# ---------------------------------------------------------------------------


IMPORT_STAGES = {
    "pending": "Aguardando início",
    "uploading": "Enviando arquivo para serviço LLM",
    "processing": "Processando romaneio com modelo LLM",
    "parsing": "Interpretando itens e salvando",
    "completed": "Processamento concluído",
    "error": "Processamento interrompido",
}

import_jobs: Dict[str, ImportRomaneioStatus] = {}
import_job_results: Dict[str, ImportRomaneioResponse] = {}


def _create_job() -> ImportRomaneioStatus:
    job_id = uuid.uuid4().hex
    now = time.time()
    status = ImportRomaneioStatus(
        job_id=job_id,
        stage="pending",
        message=IMPORT_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    import_jobs[job_id] = status
    return status


def _update_job(
    job: ImportRomaneioStatus,
    stage: str,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    result: Optional[ImportRomaneioResponse] = None,
) -> None:
    if stage not in IMPORT_STAGES:
        raise ValueError(f"Invalid stage '{stage}'")
    job.stage = stage
    job.message = message or IMPORT_STAGES[stage]
    job.updated_at = time.time()
    if error is not None:
        job.error = error
    if result is not None:
        job.completed_at = job.updated_at
        import_job_results[job.job_id] = result
    elif stage == "completed":
        job.completed_at = job.updated_at

    schedule_broadcast_ui_event(
        "job.updated",
        {
            "job": "import_romaneio",
            "job_id": job.job_id,
            "stage": stage,
            "message": job.message,
        },
    )
    if stage == "completed":
        schedule_broadcast_ui_event(
            "state.changed",
            {"scopes": ["products", "totals", "brands"]},
        )


def _remove_job(job_id: str) -> None:
    import_jobs.pop(job_id, None)
    import_job_results.pop(job_id, None)


# ---------------------------------------------------------------------------
# Grade extraction job tracking
# ---------------------------------------------------------------------------


GRADE_JOB_STAGES = {
    "pending": "Aguardando início",
    "uploading": "Enviando nota para serviço LLM",
    "processing": "Detectando grades via LLM",
    "parsing": "Interpretando grades e aplicando nos produtos",
    "completed": "Processo de grades concluído",
    "error": "Processamento de grades interrompido",
}

grade_jobs: Dict[str, "GradeExtractionStatus"] = {}
grade_job_results: Dict[str, "GradeExtractionResponse"] = {}


def _create_grade_job() -> "GradeExtractionStatus":
    job_id = uuid.uuid4().hex
    now = time.time()
    status = GradeExtractionStatus(
        job_id=job_id,
        stage="pending",
        message=GRADE_JOB_STAGES["pending"],
        started_at=now,
        updated_at=now,
    )
    grade_jobs[job_id] = status
    return status


def _update_grade_job(
    job: "GradeExtractionStatus",
    stage: str,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    result: Optional["GradeExtractionResponse"] = None,
) -> None:
    if stage not in GRADE_JOB_STAGES:
        raise ValueError(f"Invalid grade stage '{stage}'")
    job.stage = stage
    job.message = message or GRADE_JOB_STAGES[stage]
    job.updated_at = time.time()
    if error is not None:
        job.error = error
    if result is not None or stage == "completed":
        job.completed_at = job.updated_at
    if result is not None:
        grade_job_results[job.job_id] = result

    schedule_broadcast_ui_event(
        "job.updated",
        {
            "job": "parser_grades",
            "job_id": job.job_id,
            "stage": stage,
            "message": job.message,
        },
    )
    if stage == "completed":
        schedule_broadcast_ui_event(
            "state.changed",
            {"scopes": ["products", "totals"]},
        )


def _remove_grade_job(job_id: str) -> None:
    grade_jobs.pop(job_id, None)
    grade_job_results.pop(job_id, None)


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
        parts: List[str] = []
        for item in raw:
            text = _extract_chat_content(item)
            if text:
                parts.append(text)
        return "".join(parts)
    return ""


def _split_text_chunks(text: str, *, max_chars: int = 8000) -> List[str]:
    """Split long text into chunks by line boundaries.

    This helps sending large multi-page documents to the LLM more reliably.
    """
    t = (text or "").strip()
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    parts: List[str] = []
    remaining = t
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
    return [p for p in parts if p]


def _parse_pdf_tables_bytes(pdf_bytes: bytes) -> List[ProductRecord]:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []
    out: List[ProductRecord] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in (pdf.pages or []):
                tables: List[List[List[str]]]
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    continue
                for tbl in tables:
                    if not tbl or len(tbl) < 1:
                        continue
                    header = [(c or "").strip() for c in tbl[0]]
                    idx = _find_header_indexes([c for c in header if c])
                    rows = tbl[1:] if idx else tbl
                    for parts in rows:
                        cells = [(c or "").strip() for c in parts]
                        if not cells:
                            continue
                        codigo = cells[idx["code"]] if idx and "code" in idx and idx["code"] < len(cells) else (cells[0] if cells else "")
                        descricao = cells[idx["desc"]] if idx and "desc" in idx and idx["desc"] < len(cells) else (cells[1] if len(cells) > 1 else "")
                        if not codigo or not _has_digits(codigo) or not descricao:
                            continue
                        quantidade_raw = cells[idx["qty"]] if idx and "qty" in idx and idx["qty"] < len(cells) else (cells[2] if len(cells) > 2 else "1")
                        preco_raw = cells[idx["price"]] if idx and "price" in idx and idx["price"] < len(cells) else (cells[3] if len(cells) > 3 else "")
                        out.append(ProductRecord(
                            nome=str(descricao).strip(),
                            codigo=str(codigo).strip(),
                            codigo_original=str(codigo).strip(),
                            quantidade=_parse_quantity(quantidade_raw),
                            preco=_normalize_price_str(preco_raw),
                            categoria="",
                            marca="",
                            preco_final=None,
                        ))
    except Exception:
        return out
    return out

def _parse_quantity(value: Any) -> int:
    if value is None:
        return 1
    if isinstance(value, (int, float)):
        try:
            q = int(round(float(value)))
            return q if q > 0 else 1
        except Exception:
            return 1
    s = str(value)
    import re as _re
    m = _re.search(r"[-+]?\d+(?:[.,]\d+)?", s)
    if not m:
        return 1
    try:
        v = float(m.group(0).replace(",", "."))
        q = int(round(v))
        return q if q > 0 else 1
    except Exception:
        return 1


def _normalize_price_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}".replace(".", ",")
    return str(value).strip()


def _has_digits(text: str) -> bool:
    import re as _re
    return bool(_re.search(r"\d", text or ""))


def _map_keys_lower(d: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in d.items()}


def _extract_json_items(text: str) -> List[Dict[str, Any]]:
    t = (text or "").strip()
    data: Any = None
    try:
        if t.startswith("{") or t.startswith("["):
            data = json.loads(t)
    except Exception:
        data = None
    if data is None:
        import re as _re
        blocks = _re.findall(r"```(?:json)?\s*(.*?)```", text, flags=_re.IGNORECASE | _re.DOTALL)
        for blk in blocks:
            try:
                data = json.loads(blk)
                break
            except Exception:
                continue
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        arr = data.get("items")
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict):
                    items.append(it)
    elif isinstance(data, list):
        for it in data:
            if isinstance(it, dict):
                items.append(it)
    return items


def _normalize_size_label(label: str) -> str:
    text = str(label or "").strip().upper().replace("TAM.", "TAM").replace("TAMANHO", "TAM")
    # capture common patterns like 'TAM 10', 'TAM10', 'TAM M', 'TAMM', or just raw labels '10', 'M', 'G1'
    import re as _re
    m = _re.search(r"\b(?:TAM\s*[:.-]?\s*)?([0-9]{1,3}|PP|P|M|G|GG|XG|G[1-4])\b", text)
    if not m:
        # if nothing matched, return cleaned alnum (e.g., '12' or 'M')
        alt = _re.sub(r"[^0-9A-Z]+", "", text)
        return alt
    return m.group(1)


def _derive_grades_from_current_items(allowed_sizes: List[str]) -> List[Dict[str, Any]]:
    """Agrupa itens já carregados na lista por código, detectando tamanho no nome.

    Retorna uma lista de objetos: {codigo, nome, grades, warnings}
    """
    items = product_db.list()
    if not items:
        return []
    allowed = {str(s).strip().upper() for s in (allowed_sizes or [])}
    groups: Dict[str, Dict[str, Any]] = {}
    import re as _re
    for rec in items:
        code = (rec.codigo or "").strip()
        if not code:
            continue
        nome = (rec.nome or "").strip()
        # Detecta tamanho
        # padrões: 'Tam 2', 'Tam M', 'Tamanho 10', 'Tam12'
        m = _re.search(r"(?i)\b(?:tam(?:anho)?\.?\s*)([0-9]{1,3}|pp|p|m|g|gg|xg|g[1-4])\b", nome)
        size = m.group(1) if m else ""
        size = _normalize_size_label(size)
        if not size:
            # tenta extrair um último token numérico como alternativa
            m2 = _re.search(r"(\d{1,3})\b", nome)
            size = m2.group(1) if m2 else ""
        size = str(size).strip().upper()
        if size and allowed and size not in allowed:
            # tamanho não aceito pelo catálogo, ignora
            size = ""

        grp = groups.setdefault(code, {"codigo": code, "nome": nome, "grades": {}, "warnings": []})
        # estabiliza nome base retirando o sufixo 'Tam X'
        if "Tam" in nome or "tam" in nome:
            base = _re.sub(r"(?i)\bTam(?:anho)?\.?\s*[A-Z0-9]+\b", "", nome).strip()
            if base:
                grp["nome"] = base
        if size:
            qty = int(getattr(rec, "quantidade", 0) or 0) or 1
            grp["grades"][size] = grp["grades"].get(size, 0) + qty
        else:
            grp["warnings"].append(f"Tamanho não detectado no item '{nome}'")

    out: List[Dict[str, Any]] = []
    for code, data in groups.items():
        if data["grades"]:
            out.append(data)
    return out


def _filter_suspect_records(records: List[ProductRecord]) -> List[ProductRecord]:
    import re as _re
    meta_words = {
        "série", "serie", "nº", "n°", "numero", "número", "nro", "centro", "data", "hora",
        "emissão", "emissao", "cliente", "pedido", "emitido", "cnpj", "ie",
    }
    out: List[ProductRecord] = []
    for r in (records or []):
        code = (r.codigo or "").strip()
        name = (r.nome or "").strip()
        if not code or not name:
            continue
        # discard codes with spaces or too short when alnum-only
        if " " in code:
            continue
        code_alnum = _re.sub(r"[^0-9A-Za-z]", "", code)
        if len(code_alnum) < 4:
            continue
        if code_alnum.isdigit() and len(code_alnum) < 5:
            continue
        first_token = code.split()[0].lower().strip(":") if code.split() else ""
        if ":" in first_token:
            first_token = first_token.split(":", 1)[0].strip()
        if first_token in meta_words:
            continue
        # Drop obvious header/meta lines in the description
        name_lower = name.lower()
        if any(w in name_lower for w in ("centro -", "data", "hora", "série", "nº", "n°", "numero", "número", "cnpj", "ie", "valor original", "valor do desconto", "desconto", "total", "volume malwee")):
            continue
        # Drop if description is a timestamp/date
        if _re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2}(:\d{2})?)?\b", name):
            continue
        # Require at least a few alphabetic characters to be a product description
        alpha_count = sum(1 for ch in name if ch.isalpha())
        if alpha_count < 2:
            continue
        out.append(r)
    return out

def _parse_space_aligned_table(text: str) -> List[ProductRecord]:
    import re as _re
    lines = (text or "").splitlines()
    out: List[ProductRecord] = []
    price_re = _re.compile(r"(?i)^(?:r\$\s*)?\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})$")
    header_re = _re.compile(r"(?i)\b(c[oó]d|codigo|c[oó]digo|ref|sku|descri|produto|item|quant|qtd|pre[cç]o|price)\b")
    meta_first_token = {"série", "serie", "nº", "n°", "numero", "nro", "centro", "data", "hora", "emissão", "emissao", "cliente", "pedido"}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or _re.fullmatch(r"[\-|_\s]+", line):
            continue
        if header_re.search(line) and not any(ch.isdigit() for ch in line.split()[0]):
            continue
        tokens = [t.strip() for t in _re.split(r"\s{2,}", line) if t.strip()]
        if len(tokens) < 2:
            continue
        code = tokens[0]
        first_lower = code.lower().strip(":")
        if first_lower in meta_first_token:
            continue
        # ignore dates/times in first token
        if "/" in code or ":" in code or _re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", code):
            continue
        # code must have digits and reasonable length; reject tokens with internal spaces
        if " " in code:
            continue
        if not _has_digits(code):
            continue
        code_alnum = _re.sub(r"[^0-9A-Za-z]", "", code)
        if len(code_alnum) < 4:
            continue
        # if numeric-only, require at least 5 digits to avoid capturing '00 58', '02464', etc.
        if code_alnum.isdigit() and len(code_alnum) < 5:
            continue
        price_raw = ""
        qty_raw: Any = None
        desc_tokens: List[str] = []
        if len(tokens) >= 4 and price_re.match(tokens[-1]):
            price_raw = tokens[-1]
            qty_raw = tokens[-2]
            # if qty looks implausible (e.g., 8700 from '87,00') or is not clean digits, try previous token
            clean_qty = qty_raw.replace(".", "").replace(",", "").strip()
            if not clean_qty.isdigit() or (clean_qty.isdigit() and int(clean_qty) > 500):
                if len(tokens) >= 5:
                    alt = tokens[-3].replace(".", "").replace(",", "").strip()
                    if alt.isdigit() and 1 <= int(alt) <= 500:
                        qty_raw = tokens[-3]
            desc_tokens = tokens[1:-2]
        elif len(tokens) >= 3 and tokens[-1] and tokens[-1].replace(".", "").replace(",", "").isdigit():
            qty_raw = tokens[-1]
            desc_tokens = tokens[1:-1]
        else:
            desc_tokens = tokens[1:]
        descricao = " ".join(desc_tokens).strip()
        if not descricao:
            continue
        # Require at least qty or price to avoid metadata rows turning into items
        if qty_raw is None and not price_raw:
            continue
        quantidade = _parse_quantity(qty_raw)
        preco = _normalize_price_str(price_raw)
        out.append(ProductRecord(
            nome=descricao,
            codigo=str(code).strip(),
            codigo_original=str(code).strip(),
            quantidade=quantidade,
            preco=preco,
            categoria="",
            marca="",
            preco_final=None,
        ))
    return out

def _records_from_json_items(items: List[Dict[str, Any]]) -> List[ProductRecord]:
    out: List[ProductRecord] = []
    if not items:
        return out
    code_keys = ("codigo", "código", "code", "cod", "sku", "referencia", "ref", "ref.")
    desc_keys = ("descricao", "descrição", "description", "produto", "nome", "item")
    qty_keys = ("quantidade", "qtd", "qtde", "qde", "quantity", "qty")
    price_keys = ("preco", "preço", "price", "valor", "unit_price", "unit price", "unitario", "unitário")
    for it in items:
        lower = _map_keys_lower(it)
        def _get(keys: Tuple[str, ...]) -> Any:
            for k in keys:
                if k in lower:
                    return lower[k]
            return None
        codigo = str(_get(code_keys) or "").strip()
        descricao = str(_get(desc_keys) or "").strip()
        if not codigo or not _has_digits(codigo) or not descricao:
            continue
        quantidade = _parse_quantity(_get(qty_keys))
        preco = _normalize_price_str(_get(price_keys))
        out.append(ProductRecord(
            nome=descricao,
            codigo=codigo,
            codigo_original=codigo,
            quantidade=quantidade,
            preco=preco,
            categoria="",
            marca="",
            preco_final=None,
        ))
    return out


def _find_header_indexes(headers: List[str]) -> Dict[str, int]:
    h = [x.strip().lower() for x in headers]
    mapping: Dict[str, int] = {}
    def _first(syns: Tuple[str, ...]) -> int:
        for idx, name in enumerate(h):
            for s in syns:
                if s in name:
                    return idx
        return -1
    code_i = _first(("código", "codigo", "cod", "sku", "ref", "code"))
    desc_i = _first(("descrição", "descricao", "description", "produto", "item", "nome", "desc"))
    qty_i = _first(("quantidade", "qtd", "qtde", "qde", "quantity", "qty"))
    price_i = _first(("preço", "preco", "price", "valor", "unit", "unit price", "custo"))
    if code_i >= 0:
        mapping["code"] = code_i
    if desc_i >= 0:
        mapping["desc"] = desc_i
    if qty_i >= 0:
        mapping["qty"] = qty_i
    if price_i >= 0:
        mapping["price"] = price_i
    return mapping


def _parse_markdown_table(text: str) -> List[ProductRecord]:
    lines = (text or "").splitlines()
    rows: List[List[str]] = []
    header: List[str] = []
    sep_found = False
    import re as _re
    for i in range(len(lines) - 1):
        a = lines[i]
        b = lines[i + 1]
        if "|" in a and _re.match(r"^\s*\|?\s*:?-{3,}.*", b):
            header = [c.strip() for c in a.split("|") if c.strip()]
            sep_found = True
            start = i + 2
            for j in range(start, len(lines)):
                line = lines[j].strip()
                if not line:
                    break
                if "|" not in line:
                    continue
                parts = [c.strip() for c in line.split("|") if c.strip()]
                if len([p for p in parts if p]) < 2:
                    continue
                rows.append(parts)
            break
    if not sep_found or not header or not rows:
        return []
    idx = _find_header_indexes(header)
    out: List[ProductRecord] = []
    for parts in rows:
        codigo = parts[idx["code"]] if "code" in idx and idx["code"] < len(parts) else (parts[0] if parts else "")
        descricao = parts[idx["desc"]] if "desc" in idx and idx["desc"] < len(parts) else (parts[1] if len(parts) > 1 else "")
        if not codigo or not _has_digits(codigo) or not descricao:
            continue
        quantidade_raw = parts[idx["qty"]] if "qty" in idx and idx["qty"] < len(parts) else (parts[2] if len(parts) > 2 else "1")
        preco_raw = parts[idx["price"]] if "price" in idx and idx["price"] < len(parts) else (parts[3] if len(parts) > 3 else "")
        out.append(ProductRecord(
            nome=str(descricao).strip(),
            codigo=str(codigo).strip(),
            codigo_original=str(codigo).strip(),
            quantidade=_parse_quantity(quantidade_raw),
            preco=_normalize_price_str(preco_raw),
            categoria="",
            marca="",
            preco_final=None,
        ))
    return out


def _parse_ascii_table(text: str) -> List[ProductRecord]:
    import re as _re
    lines = (text or "").splitlines()
    header_idx = -1
    for i in range(len(lines) - 1):
        a = lines[i].strip().lower()
        b = lines[i + 1].strip()
        if "|" in a and ("code" in a or "código" in a) and ("description" in a or "descri" in a) and ("quantity" in a or "quant" in a) and ("price" in a or "preço" in a or "preco" in a):
            if _re.match(r"^\s*\|?\s*-{2,}.*", b):
                header_idx = i
                break
    if header_idx < 0:
        return []
    header_parts = [c.strip() for c in lines[header_idx].split("|") if c.strip()]
    idx = _find_header_indexes(header_parts)
    if not idx or "code" not in idx or "desc" not in idx:
        return []
    out: List[ProductRecord] = []
    for j in range(header_idx + 2, len(lines)):
        line = lines[j].strip()
        if not line or "|" not in line:
            continue
        if _re.fullmatch(r"[\s\-|]+", line):
            continue
        line_clean = line.strip()
        if line_clean.startswith("|"):
            line_clean = line_clean[1:]
        if line_clean.endswith("|"):
            line_clean = line_clean[:-1]
        parts = [c.strip() for c in line_clean.split("|")]
        if len(parts) < 2:
            continue
        codigo = parts[idx["code"]] if idx["code"] < len(parts) else (parts[0] if parts else "")
        descricao = parts[idx["desc"]] if idx["desc"] < len(parts) else (parts[1] if len(parts) > 1 else "")
        if not codigo or not _has_digits(codigo) or not descricao:
            continue
        quantidade_raw = parts[idx["qty"]] if "qty" in idx and idx["qty"] < len(parts) else (parts[2] if len(parts) > 2 else "1")
        preco_raw = parts[idx["price"]] if "price" in idx and idx["price"] < len(parts) else (parts[3] if len(parts) > 3 else "")
        out.append(ProductRecord(
            nome=str(descricao).strip(),
            codigo=str(codigo).strip(),
            codigo_original=str(codigo).strip(),
            quantidade=_parse_quantity(quantidade_raw),
            preco=_normalize_price_str(preco_raw),
            categoria="",
            marca="",
            preco_final=None,
        ))
    return out


def _parse_delimited(text: str, delim: str) -> List[ProductRecord]:
    lines = (text or "").splitlines()
    usable: List[List[str]] = []
    for line in lines:
        if delim not in line:
            continue
        parts = [p.strip() for p in line.split(delim) if p.strip()]
        if len([p for p in parts if p]) >= 2:
            usable.append(parts)
    if not usable:
        return []
    header_map: Dict[str, int] = {}
    first = usable[0]
    if any(k in (c.lower()) for k in ("código", "codigo", "descrição", "descricao", "quantidade", "preço", "preco", "code", "description", "quantity", "price") for c in first):
        header_map = _find_header_indexes([c for c in first if c])
        usable = usable[1:]
    out: List[ProductRecord] = []
    for parts in usable:
        codigo = parts[header_map["code"]] if "code" in header_map and header_map["code"] < len(parts) else (parts[0] if parts else "")
        descricao = parts[header_map["desc"]] if "desc" in header_map and header_map["desc"] < len(parts) else (parts[1] if len(parts) > 1 else "")
        if not codigo or not _has_digits(codigo) or not descricao:
            continue
        quantidade_raw = parts[header_map["qty"]] if "qty" in header_map and header_map["qty"] < len(parts) else (parts[2] if len(parts) > 2 else "1")
        preco_raw = parts[header_map["price"]] if "price" in header_map and header_map["price"] < len(parts) else (parts[3] if len(parts) > 3 else "")
        out.append(ProductRecord(
            nome=str(descricao).strip(),
            codigo=str(codigo).strip(),
            codigo_original=str(codigo).strip(),
            quantidade=_parse_quantity(quantidade_raw),
            preco=_normalize_price_str(preco_raw),
            categoria="",
            marca="",
            preco_final=None,
        ))
    return out


def _parse_llm_romaneio(text: str) -> List[ProductRecord]:
    items = _extract_json_items(text)
    recs = _records_from_json_items(items) if items else []
    if recs:
        return recs
    ascii_rows = _parse_ascii_table(text)
    if ascii_rows:
        return ascii_rows
    md = _parse_markdown_table(text)
    if md:
        return md
    fixed = _parse_space_aligned_table(text)
    if fixed:
        return fixed
    for d in ("|", ";", "\t", ","):
        got = _parse_delimited(text, d)
        if got:
            return got
    return []

# ---------------------------------------------------------------------------
# API routes ---------------------------------------------------------------


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/catalog/sizes")
async def get_sizes_catalog() -> Dict[str, List[str]]:
    return {"sizes": SIZES_CATALOG}


@app.get("/products", response_model=ProductListResponse)
async def get_products() -> Dict[str, List[ProductResponse]]:
    items = [_to_response(record) for record in product_db.list()]
    return {"items": items}


@app.post("/products", status_code=201, response_model=ProductItemResponse)
async def add_product(payload: ProductPayload) -> Dict[str, ProductResponse]:
    grades_items = (
        [GradeItem(tamanho=g.tamanho.strip(), quantidade=int(g.quantidade)) for g in (payload.grades or [])]
        if payload.grades
        else None
    )
    cores_items = (
        [CorItem(cor=c.cor.strip(), quantidade=int(c.quantidade)) for c in (payload.cores or [])]
        if payload.cores
        else None
    )
    record = ProductRecord(
        nome=payload.nome,
        codigo=payload.codigo,
        codigo_original=payload.codigo,
        quantidade=payload.quantidade,
        preco=payload.preco,
        categoria=payload.categoria,
        marca=payload.marca,
        preco_final=payload.preco_final,
        descricao_completa=payload.descricao_completa,
        grades=grades_items,
        cores=cores_items,
    )
    stored = product_db.add(record)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return {"item": _to_response(stored)}


@app.delete("/products")
async def clear_products() -> Dict[str, int]:
    removed = product_db.clear_current()
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals"]},
    )
    return {"removed": removed}


@app.delete("/products/{ordering_key:path}")
async def delete_product(ordering_key: str) -> Dict[str, str]:
    success = product_db.delete_by_key(ordering_key)
    if not success:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals"]},
    )
    return {"status": "deleted", "ordering_key": ordering_key}


class ProductUpdatePayload(BaseModel):
    nome: Optional[str] = None
    codigo: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    descricao_completa: Optional[str] = None
    quantidade: Optional[int] = Field(default=None, ge=0)
    preco: Optional[str] = None
    preco_final: Optional[str] = None
    grades: Optional[List[GradeItemPayload]] = None
    cores: Optional[List[CorItemPayload]] = None

    @model_validator(mode="after")
    def ensure_any_field(cls, values):  # type: ignore[misc]
        if not any(
            getattr(values, field) is not None
            for field in (
                "nome",
                "codigo",
                "marca",
                "categoria",
                "descricao",
                "descricao_completa",
                "quantidade",
                "preco",
                "preco_final",
                "grades",
                "cores",
            )
        ):
            raise ValueError("Nenhum campo fornecido para atualização")
        return values


@app.patch("/products/{ordering_key:path}", response_model=ProductItemResponse)
async def update_product(ordering_key: str, payload: ProductUpdatePayload) -> Dict[str, ProductResponse]:
    updated = product_db.update(ordering_key, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return {"item": _to_response(updated)}


@app.post("/actions/apply-category")
async def apply_category(payload: BulkActionPayload) -> Dict[str, str]:
    valor = payload.valor.strip()
    if not valor:
        raise HTTPException(status_code=400, detail="Categoria inválida")
    product_db.apply_category(valor)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products"]},
    )
    return {"status": "categoria aplicada", "categoria": valor}


@app.post("/actions/apply-brand")
async def apply_brand(payload: BulkActionPayload) -> Dict[str, str]:
    valor = payload.valor.strip()
    if not valor:
        raise HTTPException(status_code=400, detail="Marca inválida")
    product_db.apply_brand(valor)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "brands"]},
    )
    return {"status": "marca aplicada", "marca": valor}


@app.post("/actions/join-duplicates")
async def join_duplicates() -> Dict[str, int]:
    resultado = product_db.join_duplicates()
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals"]},
    )
    return resultado


class ImportRomaneioResponse(BaseModel):
    status: str
    saved_file: Optional[str] = None
    local_file: Optional[str] = None
    content: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    total_itens: int = 0


class ImportRomaneioStatus(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None


class ImportRomaneioStartResponse(BaseModel):
    job_id: str


class GradeExtractionProduct(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    grades: Dict[str, int]
    atualizado: bool
    warnings: List[str] = Field(default_factory=list)


class GradeExtractionResponse(BaseModel):
    status: str
    total_itens: int
    total_atualizados: int
    warnings: List[str] = Field(default_factory=list)
    itens: List[GradeExtractionProduct] = Field(default_factory=list)
    content: Optional[str] = None


class GradeExtractionStatus(BaseModel):
    job_id: str
    stage: str
    message: str
    started_at: float
    updated_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None


class GradeExtractionStartResponse(BaseModel):
    job_id: str


@app.get("/actions/export-json")
async def export_json() -> FileResponse:
    path = product_db.get_active_file()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de produtos não encontrado")
    return FileResponse(path, media_type="application/json", filename=path.name)


class FormatCodesPayload(BaseModel):
    remover_prefixo5: bool = False
    remover_zeros_a_esquerda: bool = False
    ultimos_digitos: Optional[int] = Field(default=None, ge=1, le=50)
    primeiros_digitos: Optional[int] = Field(default=None, ge=1, le=50)
    remover_ultimos_numeros: Optional[int] = Field(default=None, ge=1, le=50)
    remover_primeiros_numeros: Optional[int] = Field(default=None, ge=1, le=50)


class FormatCodesResponse(BaseModel):
    total: int
    alterados: int
    prefixo: Optional[str] = None


class ReorderPayload(BaseModel):
    keys: List[str] = Field(..., min_items=1)


class ReorderResponse(BaseModel):
    total: int


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
    percentual: Optional[float] = Field(default=None, gt=0)
    margem: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _ensure_value(self) -> "MarginPayload":
        if self.percentual is None and self.margem is None:
            raise ValueError("Informe 'percentual' ou 'margem'.")
        return self


class MarginResponse(BaseModel):
    total_atualizados: int
    margem_utilizada: float
    percentual_utilizado: float


class MarginSettingsPayload(BaseModel):
    percentual: float = Field(..., gt=0)


class MarginSettingsResponse(BaseModel):
    margem: float
    percentual: float


class BrandPayload(BaseModel):
    nome: str = Field(..., min_length=1)

    @validator("nome")
    def _normalize_nome(cls, value: str) -> str:  # type: ignore[misc]
        return value.strip()


class BrandsResponse(BaseModel):
    marcas: List[str]


class TotalsInfo(BaseModel):
    quantidade: int
    custo: float
    venda: float


class TotalsResponse(BaseModel):
    atual: TotalsInfo
    historico: TotalsInfo
    tempo_economizado: int
    caracteres_digitados: int


class TargetPoint(BaseModel):
    x: int
    y: int


class TargetsPayload(BaseModel):
    title: Optional[str] = None
    byte_empresa_posicao: Optional[TargetPoint] = None
    campo_descricao: Optional[TargetPoint] = None
    tres_pontinhos: Optional[TargetPoint] = None


class TargetsResponse(BaseModel):
    title: Optional[str] = None
    byte_empresa_posicao: Optional[TargetPoint] = None
    campo_descricao: Optional[TargetPoint] = None
    tres_pontinhos: Optional[TargetPoint] = None


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


async def _run_import_job(job: ImportRomaneioStatus, contents: bytes, filename: str, content_type: Optional[str]) -> None:
    logger.info("romaneio job %s: iniciando processamento no backend", job.job_id)
    files = {
        "files": (
            filename or "romaneio",
            contents,
            content_type or "application/octet-stream",
        )
    }

    upload_data: Dict[str, Any]
    chat_data: Dict[str, Any]
    text_content = ""
    llm_records: List[ProductRecord] = []
    retry_attempts = 0
    retry_used_vision = False

    try:
        _update_job(job, "uploading")
        logger.info("romaneio job %s: enviando arquivo ao LLM (%s bytes)", job.job_id, len(contents))
        headers = {"X-Job-Id": job.job_id}
        _write_llm_trace_json(
            job.job_id,
            "upload_request_meta.json",
            {
                "llm_base_url": LLM_BASE_URL,
                "filename": filename,
                "content_type": content_type,
                "bytes": len(contents),
            },
        )
        upload_t0 = time.perf_counter()
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(LLM_HTTP_TIMEOUT_SECONDS, connect=10.0)
        ) as client:
            upload_resp = await client.post(
                f"{LLM_BASE_URL}/api/upload", files=files, headers=headers
            )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            upload_elapsed = time.perf_counter() - upload_t0
            logger.info(
                "romaneio job %s: upload concluído (elapsed=%.2fs, imagens=%s, documentos=%s)",
                job.job_id,
                upload_elapsed,
                len(upload_data.get("images", [])),
                len(upload_data.get("documents", [])),
            )
            _write_llm_trace_json(
                job.job_id,
                "upload_response_summary.json",
                {
                    "errors": upload_data.get("errors") or [],
                    "images": _sanitize_images_for_trace(upload_data.get("images")),
                    "documents": _sanitize_documents_for_trace(upload_data.get("documents")),
                },
            )
            docs_for_trace = [
                d
                for d in (upload_data.get("documents") or [])
                if isinstance(d, dict)
            ]
            docs_text_joined = "\n\n".join(
                str(d.get("content") or "") for d in docs_for_trace
            ).strip()
            _write_llm_trace_text(job.job_id, "upload_documents.txt", docs_text_joined)

            # Se o documento textual for muito grande, dividimos em partes
            max_chars = _coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000)
            raw_docs = [d for d in (upload_data.get("documents") or []) if isinstance(d, dict)]
            text_blobs: List[str] = []
            for d in raw_docs:
                ct = str(d.get("content") or "").strip()
                if ct:
                    text_blobs.extend(_split_text_chunks(ct, max_chars=max_chars))

            # Checagem para forçar parser local (sem /api/chat)
            if os.getenv("IMPORT_FORCE_LOCAL", "0") == "1":
                docs = [d for d in (upload_data.get("documents") or []) if isinstance(d, dict)]
                text_joined = "\n\n".join(str(d.get("content") or "") for d in docs).strip()
                _update_job(job, "parsing")
                saved_path = product_db.save_romaneio_text(text_joined)
                records = _parse_llm_romaneio(text_joined) or list(product_db.parse_romaneio_lines(text_joined))
                if not records:
                    pdf_rows = _parse_pdf_tables_bytes(contents)
                    if pdf_rows:
                        records = pdf_rows
                records = _filter_suspect_records(records)
                warnings: List[str] = list(upload_data.get("errors") or [])
                warnings.append("Importo local forçado por configuração (IMPORT_FORCE_LOCAL=1)")
                total_itens = len(records)
                if records:
                    product_db.add_many(records)
                else:
                    warnings.append("Nenhum item detectado no romaneio gerado.")
                response = ImportRomaneioResponse(
                    status="ok",
                    saved_file=None,
                    local_file=str(saved_path),
                    content=text_joined,
                    warnings=warnings,
                    total_itens=total_itens,
                )
                _update_job(job, "completed", result=response)
                return

            _update_job(job, "processing")
            logger.info("romaneio job %s: requisitando chat no LLM", job.job_id)

            images_from_upload = upload_data.get("images", [])
            documents_from_upload = upload_data.get("documents", [])
            if text_blobs:
                logger.info(
                    "romaneio job %s: texto dividido em %s partes (max_chars=%s)",
                    job.job_id,
                    len(text_blobs),
                    max_chars,
                )
                combined: List[str] = []
                total_parts = len(text_blobs)
                for idx, chunk in enumerate(text_blobs, start=1):
                    _update_job(job, "processing", message=f"Processando texto {idx}/{total_parts}")
                    images_payload = _select_images_for_text_chunk(images_from_upload, idx)
                    payload = {
                        "message": "",
                        "mode": "romaneio_extractor",
                        "images": images_payload,
                        "documents": [{"name": f"parte_{idx}", "content": chunk}],
                    }
                    _write_llm_trace_json(
                        job.job_id,
                        f"chat_request_chunk_{idx}.json",
                        {
                            "mode": payload.get("mode"),
                            "message_chars": len(payload.get("message") or ""),
                            "images": _sanitize_images_for_trace(payload.get("images")),
                            "documents": _sanitize_documents_for_trace(payload.get("documents")),
                        },
                    )
                    _write_llm_trace_text(job.job_id, f"chat_request_chunk_{idx}.txt", chunk)
                    chat_t0 = time.perf_counter()
                    resp = await client.post(
                        f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                    )
                    resp.raise_for_status()
                    resp_json = resp.json()
                    content_piece = _extract_chat_content(resp_json.get("content"))
                    combined.append(content_piece)
                    elapsed = time.perf_counter() - chat_t0
                    logger.info(
                        "romaneio job %s: resposta chunk %s/%s (elapsed=%.2fs, chars=%s)",
                        job.job_id,
                        idx,
                        total_parts,
                        elapsed,
                        len(content_piece),
                    )
                    _write_llm_trace_json(
                        job.job_id,
                        f"chat_response_chunk_{idx}.json",
                        {
                            "elapsed_seconds": elapsed,
                            "content_chars": len(content_piece),
                            "raw_keys": list(resp_json.keys())
                            if isinstance(resp_json, dict)
                            else [],
                        },
                    )
                    _write_llm_trace_text(
                        job.job_id, f"chat_response_chunk_{idx}.txt", content_piece
                    )
                chat_data = {"role": "assistant", "content": "\n\n".join(combined)}
            else:
                docs_payload = [
                    d for d in (documents_from_upload or []) if isinstance(d, dict)
                ]
                if docs_payload:
                    _update_job(job, "processing", message="Processando documento")
                    images_payload = _select_images_for_text_chunk(images_from_upload, 1)
                    payload = {
                        "message": "",
                        "mode": "romaneio_extractor",
                        "images": images_payload,
                        "documents": docs_payload,
                    }
                    _write_llm_trace_json(
                        job.job_id,
                        "chat_request.json",
                        {
                            "mode": payload.get("mode"),
                            "message_chars": len(payload.get("message") or ""),
                            "images": _sanitize_images_for_trace(payload.get("images")),
                            "documents": _sanitize_documents_for_trace(payload.get("documents")),
                        },
                    )
                    chat_t0 = time.perf_counter()
                    chat_resp = await client.post(
                        f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                    )
                    chat_resp.raise_for_status()
                    chat_data = chat_resp.json()
                    elapsed = time.perf_counter() - chat_t0
                    _write_llm_trace_json(
                        job.job_id,
                        "chat_response.json",
                        {
                            "elapsed_seconds": elapsed,
                            "raw_keys": list(chat_data.keys())
                            if isinstance(chat_data, dict)
                            else [],
                        },
                    )
                else:
                    image_batches = _get_llm_image_batches(images_from_upload)
                    if not image_batches:
                        _write_llm_trace_text(
                            job.job_id,
                            "chat_error.txt",
                            "Upload do LLM não retornou texto ou imagens para processar.",
                        )
                        _update_job(
                            job,
                            "error",
                            error="Upload do LLM não retornou texto ou imagens para processar.",
                        )
                        return
                    combined: List[str] = []
                    total_batches = len(image_batches)
                    for batch_idx, batch in enumerate(image_batches, start=1):
                        _update_job(
                            job,
                            "processing",
                            message=f"Processando imagens {batch_idx}/{total_batches}",
                        )
                        payload = {
                            "message": "",
                            "mode": "romaneio_extractor",
                            "images": batch,
                            "documents": [],
                        }
                        _write_llm_trace_json(
                            job.job_id,
                            f"chat_request_images_{batch_idx}.json",
                            {
                                "mode": payload.get("mode"),
                                "message_chars": len(payload.get("message") or ""),
                                "images": _sanitize_images_for_trace(payload.get("images")),
                                "documents": _sanitize_documents_for_trace(payload.get("documents")),
                            },
                        )
                        chat_t0 = time.perf_counter()
                        resp = await client.post(
                            f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                        )
                        resp.raise_for_status()
                        resp_json = resp.json()
                        content_piece = _extract_chat_content(resp_json.get("content"))
                        combined.append(content_piece)
                        elapsed = time.perf_counter() - chat_t0
                        _write_llm_trace_json(
                            job.job_id,
                            f"chat_response_images_{batch_idx}.json",
                            {
                                "elapsed_seconds": elapsed,
                                "content_chars": len(content_piece),
                                "raw_keys": list(resp_json.keys())
                                if isinstance(resp_json, dict)
                                else [],
                            },
                        )
                        _write_llm_trace_text(
                            job.job_id,
                            f"chat_response_images_{batch_idx}.txt",
                            content_piece,
                        )
                    chat_data = {"role": "assistant", "content": "\n\n".join(combined)}
            logger.info("romaneio job %s: resposta recebida do LLM", job.job_id)
            text_content = _extract_chat_content(chat_data.get("content")).strip()
            _write_llm_trace_text(
                job.job_id,
                "chat_response.txt",
                text_content,
            )
            llm_records = _parse_llm_romaneio(text_content) if text_content else []

            retry_max = max(_coerce_int_env("LLM_ROMANEIO_MAX_RETRIES", 1), 0)
            retry_prompt = str(
                os.getenv("LLM_ROMANEIO_CORRECTION_PROMPT", DEFAULT_ROMANEIO_RETRY_PROMPT)
            ).strip()
            if not retry_prompt:
                retry_prompt = DEFAULT_ROMANEIO_RETRY_PROMPT
            retry_doc_chars = _coerce_int_env("LLM_ROMANEIO_RETRY_MAX_CHARS", max_chars)
            retry_prev_chars = _coerce_int_env("LLM_ROMANEIO_RETRY_PREV_CHARS", 2000)
            force_vision_retry = _env_flag("LLM_ROMANEIO_FORCE_VISION_ON_RETRY", "0")
            retry_doc_text = _build_retry_document_text(
                text_blobs, documents_from_upload, max_chars=retry_doc_chars
            )
            previous_output = text_content

            while retry_attempts < retry_max and not llm_records:
                attempt_no = retry_attempts + 1
                retry_attempts = attempt_no
                _update_job(
                    job,
                    "processing",
                    message=f"Tentativa extra LLM {attempt_no}/{retry_max}",
                )
                prompt_parts = [retry_prompt]
                if previous_output:
                    prompt_parts.append(
                        "Resposta anterior (truncada):\n"
                        + _truncate_text(previous_output, retry_prev_chars)
                    )
                if retry_doc_text:
                    prompt_parts.append(
                        "Texto do romaneio (truncado):\n"
                        + _truncate_text(retry_doc_text, retry_doc_chars)
                    )
                retry_message = "\n\n".join(p for p in prompt_parts if p).strip()
                retry_images = images_from_upload
                retry_documents: List[Dict[str, Any]] = []
                if retry_doc_text:
                    retry_documents = [{"name": "romaneio_retry", "content": retry_doc_text}]
                if force_vision_retry and not retry_used_vision:
                    is_pdf = (content_type or "").lower().endswith("pdf") or (
                        filename or ""
                    ).lower().endswith(".pdf")
                    if is_pdf:
                        max_pages = _coerce_int_env("LLM_ROMANEIO_RETRY_VISION_MAX_PAGES", 6)
                        zoom = float(os.getenv("LLM_ROMANEIO_RETRY_VISION_ZOOM", "2.0"))
                        vision_images = _render_pdf_images_for_retry(
                            contents, max_pages=max_pages, zoom=zoom
                        )
                        if vision_images:
                            retry_images = vision_images
                            retry_used_vision = True
                payload = {
                    "message": retry_message,
                    "mode": "romaneio_extractor",
                    "images": retry_images,
                    "documents": retry_documents,
                }
                _write_llm_trace_json(
                    job.job_id,
                    f"chat_request_retry_{attempt_no}.json",
                    {
                        "mode": payload.get("mode"),
                        "message_chars": len(payload.get("message") or ""),
                        "images": _sanitize_images_for_trace(payload.get("images")),
                        "documents": _sanitize_documents_for_trace(payload.get("documents")),
                    },
                )
                _write_llm_trace_text(
                    job.job_id,
                    f"chat_request_retry_{attempt_no}.txt",
                    retry_message,
                )
                chat_t0 = time.perf_counter()
                retry_resp = await client.post(
                    f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                )
                retry_resp.raise_for_status()
                retry_json = retry_resp.json()
                text_content = _extract_chat_content(retry_json.get("content")).strip()
                elapsed = time.perf_counter() - chat_t0
                llm_records = _parse_llm_romaneio(text_content) if text_content else []
                previous_output = text_content or previous_output
                logger.info(
                    "romaneio job %s: resposta retry %s (elapsed=%.2fs, chars=%s)",
                    job.job_id,
                    attempt_no,
                    elapsed,
                    len(text_content),
                )
                _write_llm_trace_json(
                    job.job_id,
                    f"chat_response_retry_{attempt_no}.json",
                    {
                        "elapsed_seconds": elapsed,
                        "content_chars": len(text_content),
                        "raw_keys": list(retry_json.keys())
                        if isinstance(retry_json, dict)
                        else [],
                    },
                )
                _write_llm_trace_text(
                    job.job_id,
                    f"chat_response_retry_{attempt_no}.txt",
                    text_content,
                )
    except httpx.RequestError as exc:
        logger.exception("romaneio job %s: erro de requisição ao LLM", job.job_id)
        # Fallback: tenta interpretar apenas com os documentos extraídos no upload
        docs = [d for d in (locals().get("upload_data", {}).get("documents") or []) if isinstance(d, dict)]
        text_joined = "\n\n".join(str(d.get("content") or "") for d in docs).strip()
        if not text_joined:
            _update_job(job, "error", error=f"Falha na comunicação com o serviço LLM: {exc}")
            return
        try:
            _update_job(job, "parsing")
            saved_path = product_db.save_romaneio_text(text_joined)
            records = _parse_llm_romaneio(text_joined) or list(product_db.parse_romaneio_lines(text_joined))
            records = _filter_suspect_records(records)
            if not records:
                pdf_rows = _parse_pdf_tables_bytes(contents)
                if pdf_rows:
                    records = _filter_suspect_records(pdf_rows)
            warnings: List[str] = [
                f"Chat do LLM indisponível, usado parser local (erro: {exc})"
            ]
            if records and pdf_rows if 'pdf_rows' in locals() else False:
                warnings.append("Itens extraídos de tabelas do PDF (parser local)")
            records = _filter_suspect_records(records or [])
            if records:
                product_db.add_many(records)
            response = ImportRomaneioResponse(
                status="ok",
                saved_file=None,
                local_file=str(saved_path),
                content=text_joined,
                warnings=warnings,
                total_itens=len(records or []),
            )
            _update_job(job, "completed", result=response)
            return
        except Exception:
            _update_job(job, "error", error=f"Falha no parser local após erro de rede: {exc}")
            return
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "romaneio job %s: erro HTTP do LLM (status=%s)", job.job_id, exc.response.status_code
        )
        # Fallback igual ao acima para HTTP 5xx/4xx
        docs = [d for d in (locals().get("upload_data", {}).get("documents") or []) if isinstance(d, dict)]
        text_joined = "\n\n".join(str(d.get("content") or "") for d in docs).strip()
        if not text_joined:
            _update_job(job, "error", error=exc.response.text or str(exc))
            return
        try:
            _update_job(job, "parsing")
            saved_path = product_db.save_romaneio_text(text_joined)
            records = _parse_llm_romaneio(text_joined) or list(product_db.parse_romaneio_lines(text_joined))
            records = _filter_suspect_records(records)
            if not records:
                pdf_rows = _parse_pdf_tables_bytes(contents)
                if pdf_rows:
                    records = _filter_suspect_records(pdf_rows)
            warnings: List[str] = [
                f"Serviço LLM retornou erro {exc.response.status_code}; usado parser local"
            ]
            if records and pdf_rows if 'pdf_rows' in locals() else False:
                warnings.append("Itens extraídos de tabelas do PDF (parser local)")
            if records:
                product_db.add_many(records)
            response = ImportRomaneioResponse(
                status="ok",
                saved_file=None,
                local_file=str(saved_path),
                content=text_joined,
                warnings=warnings,
                total_itens=len(records or []),
            )
            _update_job(job, "completed", result=response)
            return
        except Exception:
            _update_job(job, "error", error=exc.response.text or str(exc))
            return

    try:
        if not text_content and isinstance(chat_data, dict):
            text_content = _extract_chat_content(chat_data.get("content")).strip()
        if text_content and not llm_records:
            llm_records = _parse_llm_romaneio(text_content)
        logger.info(
            "romaneio job %s: conteúdo processado com %s caracteres", job.job_id, len(text_content)
        )
    except Exception as exc:  # pragma: no cover - defensive
        _update_job(job, "error", error=f"Falha ao interpretar resposta do LLM: {exc}")
        logger.exception("romaneio job %s: falha ao interpretar resposta", job.job_id)
        return

    if not text_content:
        _update_job(job, "error", error="Serviço LLM não retornou conteúdo processado.")
        logger.warning("romaneio job %s: resposta vazia do LLM", job.job_id)
        return

    _update_job(job, "parsing")
    logger.info("romaneio job %s: iniciando parsing e persistência", job.job_id)

    try:
        saved_path = product_db.save_romaneio_text(text_content)

        fallback_used = ""
        records = llm_records or _parse_llm_romaneio(text_content)
        records = _filter_suspect_records(records)
        if not records:
            parsed_lines = list(product_db.parse_romaneio_lines(text_content))
            if parsed_lines:
                records = _filter_suspect_records(parsed_lines)
                fallback_used = "lines"
            else:
                docs = [d for d in (upload_data.get("documents") or []) if isinstance(d, dict)]
                text_joined = "\n\n".join(str(d.get("content") or "") for d in docs).strip()
                if text_joined:
                    parsed_from_upload = _filter_suspect_records(
                        _parse_llm_romaneio(text_joined)
                        or list(product_db.parse_romaneio_lines(text_joined))
                    )
                    if parsed_from_upload:
                        records = parsed_from_upload
                        fallback_used = "upload_docs"
        if not records:
            pdf_rows = _parse_pdf_tables_bytes(contents)
            if pdf_rows:
                records = _filter_suspect_records(pdf_rows)
                fallback_used = "pdf_tables"

        warnings: List[str] = list(upload_data.get("errors") or [])
        if retry_attempts:
            warnings.append(
                f"LLM executou {retry_attempts} tentativa(s) extra(s) para corrigir a resposta."
            )
        if retry_used_vision:
            warnings.append("Retry do LLM utilizou imagens renderizadas do PDF (vision fallback).")
        if fallback_used == "lines":
            warnings.append("Parser estruturado não encontrou itens; usado fallback por linhas.")
        elif fallback_used == "upload_docs":
            warnings.append("Conteúdo do LLM não gerou itens; usado texto bruto do upload (fallback).")
        elif fallback_used == "pdf_tables":
            warnings.append("Conteúdo do LLM não gerou itens; usado parser de tabelas do PDF (fallback).")

        total_itens = len(records)
        logger.info(
            "romaneio job %s: parsing gerou %s itens (warnings=%s)",
            job.job_id,
            total_itens,
            len(warnings),
        )

        if records:
            product_db.add_many(records)
        else:
            warnings.append("Nenhum item detectado no romaneio gerado.")

        response = ImportRomaneioResponse(
            status="ok",
            saved_file=chat_data.get("saved_file"),
            local_file=str(saved_path),
            content=text_content,
            warnings=warnings,
            total_itens=total_itens,
        )
    except Exception as exc:
        _update_job(job, "error", error=f"Falha ao salvar ou interpretar romaneio: {exc}")
        logger.exception("romaneio job %s: falha ao salvar/parsing", job.job_id)
        return

    _update_job(job, "completed", result=response)
    logger.info("romaneio job %s: concluído com sucesso", job.job_id)


async def _run_grade_extraction_job(job: GradeExtractionStatus, contents: bytes, filename: str, content_type: Optional[str]) -> None:
    logger.info("grade job %s: iniciando processamento", job.job_id)
    files = {
        "files": (
            filename or "nota_fiscal",
            contents,
            content_type or "application/octet-stream",
        )
    }

    upload_data: Dict[str, Any]
    chat_data: Dict[str, Any]

    try:
        _update_grade_job(job, "uploading")
        headers = {"X-Job-Id": job.job_id}
        _write_llm_trace_json(
            job.job_id,
            "upload_request_meta.json",
            {
                "llm_base_url": LLM_BASE_URL,
                "filename": filename,
                "content_type": content_type,
                "bytes": len(contents),
            },
        )
        upload_t0 = time.perf_counter()
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(LLM_HTTP_TIMEOUT_SECONDS, connect=10.0)
        ) as client:
            logger.info("grade job %s: enviando arquivo (%s bytes)", job.job_id, len(contents))
            upload_resp = await client.post(
                f"{LLM_BASE_URL}/api/upload", files=files, headers=headers
            )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            upload_elapsed = time.perf_counter() - upload_t0
            logger.info(
                "grade job %s: upload concluído (elapsed=%.2fs, imagens=%s, documentos=%s)",
                job.job_id,
                upload_elapsed,
                len(upload_data.get("images", [])),
                len(upload_data.get("documents", [])),
            )
            _write_llm_trace_json(
                job.job_id,
                "upload_response_summary.json",
                {
                    "errors": upload_data.get("errors") or [],
                    "images": _sanitize_images_for_trace(upload_data.get("images")),
                    "documents": _sanitize_documents_for_trace(upload_data.get("documents")),
                },
            )
            docs_for_trace = [
                d
                for d in (upload_data.get("documents") or [])
                if isinstance(d, dict)
            ]
            docs_text_joined = "\n\n".join(
                str(d.get("content") or "") for d in docs_for_trace
            ).strip()
            _write_llm_trace_text(job.job_id, "upload_documents.txt", docs_text_joined)

            # Chunking para notas extensas
            max_chars = _coerce_int_env("LLM_DOC_CHUNK_CHARS", 8000)
            raw_docs = [d for d in (upload_data.get("documents") or []) if isinstance(d, dict)]
            text_blobs: List[str] = []
            for d in raw_docs:
                ct = str(d.get("content") or "").strip()
                if ct:
                    text_blobs.extend(_split_text_chunks(ct, max_chars=max_chars))

            _update_grade_job(job, "processing")
            aggregated_items: List[Any] = []
            aggregated_warnings: List[str] = []
            images_from_upload = upload_data.get("images", [])
            documents_from_upload = upload_data.get("documents", [])
            if text_blobs:
                logger.info(
                    "grade job %s: texto dividido em %s partes (max_chars=%s)",
                    job.job_id,
                    len(text_blobs),
                    max_chars,
                )
                aggregated_texts: List[str] = []
                total_parts = len(text_blobs)
                for idx, chunk in enumerate(text_blobs, start=1):
                    _update_grade_job(
                        job,
                        "processing",
                        message=f"Processando texto {idx}/{total_parts}",
                    )
                    images_payload = _select_images_for_text_chunk(images_from_upload, idx)
                    payload = {
                        "message": "",
                        "mode": "grade_extractor",
                        "images": images_payload,
                        "documents": [{"name": f"parte_{idx}", "content": chunk}],
                    }
                    _write_llm_trace_json(
                        job.job_id,
                        f"chat_request_chunk_{idx}.json",
                        {
                            "mode": payload.get("mode"),
                            "message_chars": len(payload.get("message") or ""),
                            "images": _sanitize_images_for_trace(payload.get("images")),
                            "documents": _sanitize_documents_for_trace(payload.get("documents")),
                        },
                    )
                    _write_llm_trace_text(
                        job.job_id, f"chat_request_chunk_{idx}.txt", chunk
                    )
                    chat_t0 = time.perf_counter()
                    resp = await client.post(
                        f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                    )
                    resp.raise_for_status()
                    resp_json = resp.json()
                    content_piece = _extract_chat_content(resp_json.get("content"))
                    aggregated_texts.append(content_piece)
                    elapsed = time.perf_counter() - chat_t0
                    logger.info(
                        "grade job %s: resposta chunk %s/%s (elapsed=%.2fs, chars=%s)",
                        job.job_id,
                        idx,
                        total_parts,
                        elapsed,
                        len(content_piece),
                    )
                    _write_llm_trace_json(
                        job.job_id,
                        f"chat_response_chunk_{idx}.json",
                        {
                            "elapsed_seconds": elapsed,
                            "content_chars": len(content_piece),
                            "raw_keys": list(resp_json.keys())
                            if isinstance(resp_json, dict)
                            else [],
                        },
                    )
                    _write_llm_trace_text(
                        job.job_id, f"chat_response_chunk_{idx}.txt", content_piece
                    )
                    # parse cada parte individualmente
                    try:
                        items_i, warnings_i = parse_grade_extraction(
                            content_piece, allowed_sizes=SIZES_CATALOG
                        )
                    except Exception as _exc:  # pragma: no cover - defensivo
                        items_i, warnings_i = [], [f"Falha ao interpretar um bloco: {_exc}"]
                    if items_i:
                        aggregated_items.extend(items_i)
                    if warnings_i:
                        aggregated_warnings.extend(warnings_i)
                chat_data = {"role": "assistant", "content": "\n\n".join(aggregated_texts)}
            else:
                docs_payload = [
                    d for d in (documents_from_upload or []) if isinstance(d, dict)
                ]
                if docs_payload:
                    _update_grade_job(job, "processing", message="Processando documento")
                    images_payload = _select_images_for_text_chunk(images_from_upload, 1)
                    payload = {
                        "message": "",
                        "mode": "grade_extractor",
                        "images": images_payload,
                        "documents": docs_payload,
                    }
                    _write_llm_trace_json(
                        job.job_id,
                        "chat_request.json",
                        {
                            "mode": payload.get("mode"),
                            "message_chars": len(payload.get("message") or ""),
                            "images": _sanitize_images_for_trace(payload.get("images")),
                            "documents": _sanitize_documents_for_trace(payload.get("documents")),
                        },
                    )
                    chat_t0 = time.perf_counter()
                    chat_resp = await client.post(
                        f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                    )
                    chat_resp.raise_for_status()
                    chat_data = chat_resp.json()
                    elapsed = time.perf_counter() - chat_t0
                    _write_llm_trace_json(
                        job.job_id,
                        "chat_response.json",
                        {
                            "elapsed_seconds": elapsed,
                            "raw_keys": list(chat_data.keys())
                            if isinstance(chat_data, dict)
                            else [],
                        },
                    )
                else:
                    image_batches = _get_llm_image_batches(images_from_upload)
                    if not image_batches:
                        _write_llm_trace_text(
                            job.job_id,
                            "chat_error.txt",
                            "Upload do LLM não retornou texto ou imagens para processar.",
                        )
                        _update_grade_job(
                            job,
                            "error",
                            error="Upload do LLM não retornou texto ou imagens para processar.",
                        )
                        return
                    aggregated_texts: List[str] = []
                    total_batches = len(image_batches)
                    for batch_idx, batch in enumerate(image_batches, start=1):
                        _update_grade_job(
                            job,
                            "processing",
                            message=f"Processando imagens {batch_idx}/{total_batches}",
                        )
                        payload = {
                            "message": "",
                            "mode": "grade_extractor",
                            "images": batch,
                            "documents": [],
                        }
                        _write_llm_trace_json(
                            job.job_id,
                            f"chat_request_images_{batch_idx}.json",
                            {
                                "mode": payload.get("mode"),
                                "message_chars": len(payload.get("message") or ""),
                                "images": _sanitize_images_for_trace(payload.get("images")),
                                "documents": _sanitize_documents_for_trace(payload.get("documents")),
                            },
                        )
                        chat_t0 = time.perf_counter()
                        resp = await client.post(
                            f"{LLM_BASE_URL}/api/chat", json=payload, headers=headers
                        )
                        resp.raise_for_status()
                        resp_json = resp.json()
                        content_piece = _extract_chat_content(resp_json.get("content"))
                        aggregated_texts.append(content_piece)
                        elapsed = time.perf_counter() - chat_t0
                        _write_llm_trace_json(
                            job.job_id,
                            f"chat_response_images_{batch_idx}.json",
                            {
                                "elapsed_seconds": elapsed,
                                "content_chars": len(content_piece),
                                "raw_keys": list(resp_json.keys())
                                if isinstance(resp_json, dict)
                                else [],
                            },
                        )
                        _write_llm_trace_text(
                            job.job_id,
                            f"chat_response_images_{batch_idx}.txt",
                            content_piece,
                        )
                        try:
                            items_i, warnings_i = parse_grade_extraction(
                                content_piece, allowed_sizes=SIZES_CATALOG
                            )
                        except Exception as _exc:  # pragma: no cover - defensivo
                            items_i, warnings_i = [], [f"Falha ao interpretar um bloco: {_exc}"]
                        if items_i:
                            aggregated_items.extend(items_i)
                        if warnings_i:
                            aggregated_warnings.extend(warnings_i)
                    chat_data = {"role": "assistant", "content": "\n\n".join(aggregated_texts)}
            _write_llm_trace_text(
                job.job_id,
                "chat_response.txt",
                _extract_chat_content(chat_data.get("content")),
            )
            logger.info("grade job %s: resposta do LLM recebida", job.job_id)
    except httpx.RequestError as exc:
        _update_grade_job(job, "error", error=f"Falha na comunicação com o serviço LLM: {exc}")
        logger.exception("grade job %s: erro de requisição", job.job_id)
        return
    except httpx.HTTPStatusError as exc:
        _update_grade_job(job, "error", error=exc.response.text or str(exc))
        logger.exception(
            "grade job %s: erro HTTP do LLM (status=%s)", job.job_id, exc.response.status_code
        )
        return

    try:
        text_content = _extract_chat_content(chat_data.get("content")).strip()
    except Exception as exc:  # pragma: no cover
        _update_grade_job(job, "error", error=f"Falha ao interpretar resposta do LLM: {exc}")
        logger.exception("grade job %s: falha ao interpretar resposta", job.job_id)
        return

    if not text_content:
        _update_grade_job(job, "error", error="Serviço LLM não retornou conteúdo processado.")
        logger.warning("grade job %s: resposta vazia do LLM", job.job_id)
        return

    _update_grade_job(job, "parsing")

    # Se já agregamos itens por chunk acima, use-os; caso contrário, parse o conteúdo único
    if 'aggregated_items' in locals() and aggregated_items:
        parsed_items = aggregated_items
        parser_warnings = aggregated_warnings
    else:
        parsed_items, parser_warnings = parse_grade_extraction(text_content, allowed_sizes=SIZES_CATALOG)
    warnings: List[str] = list(upload_data.get("errors") or []) + (parser_warnings or [])

    detalhes: List[GradeExtractionProduct] = []
    total_atualizados = 0

    for item in parsed_items:
        updated = product_db.update_grades_by_identifier(
            codigo=item.codigo,
            nome=item.nome,
            grades=item.grades,
        )
        atualizado = updated is not None
        if atualizado:
            total_atualizados += 1
        else:
            warnings.append(
                f"Produto não localizado para aplicação de grade (codigo={item.codigo or '-'}, nome={item.nome or '-'})"
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

    # Fallback: se o LLM não retornou itens válidos, tenta derivar das linhas já carregadas
    if not parsed_items:
        derived = _derive_grades_from_current_items(SIZES_CATALOG)
        if derived:
            warnings.append("Fallback aplicado: grades derivadas da lista atual de produtos.")
            for entry in derived:
                codigo = entry.get("codigo")
                nome = entry.get("nome")
                grades = entry.get("grades") or {}
                upd = product_db.update_grades_by_identifier(codigo=codigo, nome=nome, grades=grades)
                atualizado = upd is not None
                if atualizado:
                    total_atualizados += 1
                else:
                    warnings.append(
                        f"Produto não localizado para aplicação de grade (codigo={codigo or '-'}, nome={nome or '-'})"
                    )
                detalhes.append(
                    GradeExtractionProduct(
                        codigo=codigo,
                        nome=nome,
                        grades=grades,
                        atualizado=atualizado,
                        warnings=entry.get("warnings") or [],
                    )
                )

    if not parsed_items:
        warnings.append("Parser não encontrou itens válidos com grades na resposta do LLM")

    response = GradeExtractionResponse(
        status="ok" if total_atualizados else "partial",
        total_itens=len(parsed_items),
        total_atualizados=total_atualizados,
        warnings=warnings,
        itens=detalhes,
        content=text_content,
    )

    _update_grade_job(job, "completed", result=response)
    logger.info(
        "grade job %s: concluído (itens=%s, atualizados=%s)",
        job.job_id,
        len(parsed_items),
        total_atualizados,
    )


@app.post("/actions/import-romaneio", response_model=ImportRomaneioStartResponse)
async def import_romaneio(file: UploadFile = File(...), background: BackgroundTasks = BackgroundTasks()) -> ImportRomaneioStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou inválido")
    job = _create_job()
    _update_job(job, "uploading")
    logger.info(
        "romaneio job %s: arquivo recebido (%s bytes, nome=%s, tipo=%s)",
        job.job_id,
        len(contents),
        file.filename,
        file.content_type,
    )
    background.add_task(_run_import_job, job, contents, file.filename or "romaneio", file.content_type)
    return ImportRomaneioStartResponse(job_id=job.job_id)


@app.get("/actions/import-romaneio/status/{job_id}", response_model=ImportRomaneioStatus)
async def get_import_romaneio_status(job_id: str) -> ImportRomaneioStatus:
    job = import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.get("/actions/import-romaneio/result/{job_id}", response_model=ImportRomaneioResponse)
async def get_import_romaneio_result(job_id: str) -> ImportRomaneioResponse:
    job = import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    result = import_job_results.get(job_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponível para o job solicitado")
    return result


@app.delete("/actions/import-romaneio/status/{job_id}")
async def delete_import_romaneio_job(job_id: str) -> Dict[str, str]:
    if job_id not in import_jobs and job_id not in import_job_results:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    _remove_job(job_id)
    return {"status": "removed", "job_id": job_id}


@app.post("/actions/parser-grades", response_model=GradeExtractionStartResponse)
async def start_grade_parser(
    file: UploadFile = File(...),
    background: BackgroundTasks = BackgroundTasks(),
) -> GradeExtractionStartResponse:
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou inválido")
    job = _create_grade_job()
    _update_grade_job(job, "uploading")
    logger.info(
        "grade job %s: arquivo recebido (%s bytes, nome=%s, tipo=%s)",
        job.job_id,
        len(contents),
        file.filename,
        file.content_type,
    )
    background.add_task(
        _run_grade_extraction_job,
        job,
        contents,
        file.filename or "nota_fiscal",
        file.content_type,
    )
    return GradeExtractionStartResponse(job_id=job.job_id)


@app.get("/actions/parser-grades/status/{job_id}", response_model=GradeExtractionStatus)
async def get_grade_parser_status(job_id: str) -> GradeExtractionStatus:
    job = grade_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.get("/actions/parser-grades/result/{job_id}", response_model=GradeExtractionResponse)
async def get_grade_parser_result(job_id: str) -> GradeExtractionResponse:
    job = grade_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.stage != "completed":
        raise HTTPException(status_code=409, detail="Processamento ainda em andamento")
    result = grade_job_results.get(job_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Resultado indisponível para o job solicitado")
    return result


@app.delete("/actions/parser-grades/status/{job_id}")
async def delete_grade_parser_job(job_id: str) -> Dict[str, str]:
    if job_id not in grade_jobs and job_id not in grade_job_results:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    _remove_grade_job(job_id)
    return {"status": "removed", "job_id": job_id}


@app.post("/actions/format-codes", response_model=FormatCodesResponse)
async def format_codes(payload: FormatCodesPayload) -> FormatCodesResponse:
    result = product_db.format_codes(payload.dict())
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products"]},
    )
    return FormatCodesResponse(**result)


@app.post("/actions/restore-original-codes", response_model=RestoreCodesResponse)
async def restore_original_codes() -> RestoreCodesResponse:
    result = product_db.restore_original_codes()
    if not result["restaurados"]:
        return RestoreCodesResponse(**result)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products"]},
    )
    return RestoreCodesResponse(**result)


@app.post("/actions/reorder", response_model=ReorderResponse)
async def reorder_products(payload: ReorderPayload) -> ReorderResponse:
    total = product_db.reorder_by_keys(payload.keys)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products"]},
    )
    return ReorderResponse(total=total)


@app.post("/actions/restore-snapshot", response_model=SnapshotRestoreResponse)
async def restore_snapshot(payload: SnapshotRestorePayload) -> SnapshotRestoreResponse:
    records: List[ProductRecord] = []
    for item in payload.items:
        grades_items = (
            [GradeItem(tamanho=g.tamanho.strip(), quantidade=int(g.quantidade)) for g in (item.grades or [])]
            if item.grades
            else None
        )
        cores_items = (
            [CorItem(cor=c.cor.strip(), quantidade=int(c.quantidade)) for c in (item.cores or [])]
            if item.cores
            else None
        )
        record = ProductRecord(
            nome=item.nome,
            codigo=item.codigo,
            codigo_original=item.codigo_original or item.codigo,
            quantidade=item.quantidade,
            preco=item.preco,
            categoria=item.categoria,
            marca=item.marca,
            preco_final=item.preco_final,
            descricao_completa=item.descricao_completa,
            grades=grades_items,
            cores=cores_items,
            timestamp=item.timestamp,
        )
        records.append(record)

    product_db.replace_all(records)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return SnapshotRestoreResponse(total=len(records))


@app.post("/actions/apply-margin", response_model=MarginResponse)
async def apply_margin(payload: MarginPayload) -> MarginResponse:
    margin_factor = payload.margem if payload.margem is not None else (1 + (payload.percentual or 0) / 100.0)
    if margin_factor <= 0:
        raise HTTPException(status_code=400, detail="Margem inválida")
    total = product_db.apply_margin(margin_factor)
    percentual = (margin_factor - 1) * 100
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals"]},
    )
    return MarginResponse(
        total_atualizados=total,
        margem_utilizada=margin_factor,
        percentual_utilizado=percentual,
    )


@app.post("/actions/join-grades", response_model=JoinGradesResponse)
async def join_grades() -> JoinGradesResponse:
    result = product_db.join_with_grades()
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return JoinGradesResponse(**result)


@app.post("/actions/create-set", response_model=CreateSetResponse)
async def create_set(payload: CreateSetPayload) -> CreateSetResponse:
    result = product_db.create_set_by_keys(payload.key_a, payload.key_b)
    if not result:
        raise HTTPException(status_code=400, detail="Não foi possível criar o conjunto selecionado.")
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return CreateSetResponse(**result)


@app.get("/settings/margin", response_model=MarginSettingsResponse)
async def get_margin_settings() -> MarginSettingsResponse:
    margin = product_db.get_default_margin()
    percentual = (margin - 1) * 100
    return MarginSettingsResponse(margem=margin, percentual=percentual)


@app.post("/settings/margin", response_model=MarginSettingsResponse)
async def set_margin_settings(payload: MarginSettingsPayload) -> MarginSettingsResponse:
    percentual = payload.percentual
    margin_factor = 1 + percentual / 100.0
    if margin_factor <= 0:
        raise HTTPException(status_code=400, detail="Margem inválida")
    product_db.set_default_margin(margin_factor)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["margin"]},
    )
    return MarginSettingsResponse(margem=margin_factor, percentual=percentual)


@app.get("/brands", response_model=BrandsResponse)
async def list_brands() -> BrandsResponse:
    marcas = product_db.list_brands()
    return BrandsResponse(marcas=marcas)


@app.post("/brands", response_model=BrandsResponse)
async def add_brand(payload: BrandPayload) -> BrandsResponse:
    nome = payload.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Marca inválida")
    marcas = product_db.add_brand(nome)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["brands"]},
    )
    return BrandsResponse(marcas=marcas)


@app.get("/totals", response_model=TotalsResponse)
async def get_totals() -> TotalsResponse:
    totals = product_db.get_totals()
    atual_raw = totals.get("atual", {})
    historico_raw = totals.get("historico", {})

    def _build_totals(payload: Dict[str, Any]) -> TotalsInfo:
        return TotalsInfo(
            quantidade=int(payload.get("quantidade", 0)),
            custo=float(payload.get("custo", 0.0)),
            venda=float(payload.get("venda", 0.0)),
        )

    tempo = int(totals.get("tempo_economizado", 0))
    caracteres = int(totals.get("caracteres_digitados", 0))

    return TotalsResponse(
        atual=_build_totals(atual_raw),
        historico=_build_totals(historico_raw),
        tempo_economizado=tempo,
        caracteres_digitados=caracteres,
    )


@app.post("/actions/improve-descriptions", response_model=ImproveDescriptionResponse)
async def improve_descriptions(payload: ImproveDescriptionPayload) -> ImproveDescriptionResponse:
    has_terms = bool([term for term in payload.remover_termos if term.strip()])
    if not payload.remover_numeros and not payload.remover_especiais and not has_terms:
        raise HTTPException(status_code=400, detail="Selecione ao menos uma opção de limpeza.")

    result = product_db.improve_descriptions(
        payload.remover_numeros,
        payload.remover_especiais,
        payload.remover_termos,
    )
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products"]},
    )
    return ImproveDescriptionResponse(**result)


@app.get("/automation/targets", response_model=TargetsResponse)
async def get_targets() -> TargetsResponse:
    data = load_targets()
    response_payload: Dict[str, Any] = {"title": None}
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        response_payload["title"] = title.strip()
    for key in ("byte_empresa_posicao", "campo_descricao", "tres_pontinhos"):
        value = data.get(key)
        if isinstance(value, dict) and "x" in value and "y" in value:
            response_payload[key] = {"x": int(value["x"]), "y": int(value["y"])}
    return TargetsResponse(**response_payload)


@app.post("/automation/targets", response_model=TargetsResponse)
async def set_targets(payload: TargetsPayload) -> TargetsResponse:
    config: dict[str, Any] = {}
    if payload.title is not None:
        config["title"] = payload.title
    if payload.byte_empresa_posicao is not None: 
        config["byte_empresa_posicao"] = payload.byte_empresa_posicao.model_dump()
    if payload.campo_descricao is not None:
        config["campo_descricao"] = payload.campo_descricao.model_dump()
    if payload.tres_pontinhos is not None:
        config["tres_pontinhos"] = payload.tres_pontinhos.model_dump()

    existing = load_targets()
    existing.update(config)
    save_targets(existing)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["targets"]},
    )
    return await get_targets()


@app.post("/automation/targets/capture", response_model=TargetCaptureResponse)
async def capture_target(payload: TargetCapturePayload) -> TargetCaptureResponse:
    if pyautogui is None:
        raise HTTPException(status_code=500, detail="PyAutoGUI não disponível para captura de coordenadas")

    target = payload.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target inválido")

    try:
        x, y = pyautogui.position()
    except Exception as exc:  # pragma: no cover - interação com SO
        raise HTTPException(status_code=500, detail=f"Falha ao capturar coordenadas: {exc}") from exc

    point = TargetPoint(x=int(x), y=int(y))
    return TargetCaptureResponse(target=target, point=point)


@app.post("/automation/execute", response_model=Dict[str, str])
async def automation_execute() -> Dict[str, str]:
    try:
        if remote_agent_manager.has_connected_agents():
            produtos = preparar_produtos_para_automacao()
            if not produtos:
                raise RuntimeError("Nenhum produto disponível para cadastrar.")
            try:
                resultado = await remote_agent_manager.send_command(
                    "automation.basic",
                    {"products": produtos},
                    wait_for="result",
                    timeout=600.0,
                )
            except Exception as exc:
                raise RuntimeError(f"Falha ao despachar comando remoto: {exc}") from exc

            status = str(resultado.get("status", "accepted"))
            mensagem = resultado.get("message") or "Execução remota finalizada"

            response_payload: Dict[str, str] = {"status": status, "message": mensagem}

            concluidos_raw = resultado.get("concluidos")
            if not isinstance(concluidos_raw, list):
                concluidos_raw = resultado.get("ordering_keys")
            concluido_keys = [str(item) for item in concluidos_raw or [] if isinstance(item, str) and item]

            metrics: Dict[str, int] = {}
            if concluido_keys:
                registros = product_db.get_by_ordering_keys(concluido_keys)
                if registros:
                    metrics = product_db.record_automation_success(registros)

            if metrics:
                response_payload["tempo_economizado"] = str(metrics.get("tempo_economizado", 0))
                response_payload["caracteres_digitados"] = str(metrics.get("caracteres_digitados", 0))

            if "sucesso" in resultado:
                response_payload["sucesso"] = str(resultado.get("sucesso"))
            falhas_raw = resultado.get("falhas")
            if isinstance(falhas_raw, list):
                response_payload["falhas"] = str(len(falhas_raw))
            elif falhas_raw is not None:
                response_payload["falhas"] = str(falhas_raw)

            schedule_broadcast_ui_event(
                "state.changed",
                {"scopes": ["automation", "totals", "agents"]},
            )
            return response_payload

        result = iniciar_sequencia_basica()
        schedule_broadcast_ui_event(
            "state.changed",
            {"scopes": ["automation", "agents"]},
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/automation/status", response_model=Dict[str, Optional[str]])
async def automation_status() -> Dict[str, Optional[str]]:
    return obter_status_sequencia()


@app.post("/automation/cancel", response_model=Dict[str, str])
async def automation_cancel() -> Dict[str, str]:
    result = cancelar_sequencia_basica()
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["automation", "agents"]},
    )
    return result


@app.get("/automation/agents", response_model=Dict[str, Any])
async def automation_agents() -> Dict[str, Any]:
    snapshot = remote_agent_manager.snapshot()
    agentes = list(snapshot.get("agents", []))

    status_local = obter_status_sequencia()
    agentes.insert(
        0,
        {
            "agent_id": "Executor Local",
            "status": status_local.get("estado", "idle"),
            "capabilities": ("pyautogui",),
            "last_seen": 0,
            "last_event": {"message": status_local.get("message", "Executor interno")},
            "kind": "local",
            "is_local": True,
            "synchronized": status_local.get("estado") in {"idle", "running"},
        },
    )

    return {"agents": agentes}


class GradeConfigPayload(BaseModel):
    buttons: Optional[Dict[str, TargetPoint]] = None
    first_quant_cell: Optional[TargetPoint] = None
    second_quant_cell: Optional[TargetPoint] = None
    row_height: Optional[int] = None
    model_index: Optional[int] = None
    model_hotkey: Optional[str] = None
    erp_size_order: Optional[List[str]] = None


class GradeRunPayload(BaseModel):
    grades: Optional[Dict[str, int]] = None
    grades_json: Optional[str] = None
    model_index: Optional[int] = None
    pause: Optional[float] = None
    speed: Optional[float] = None


class GradesBatchPayload(BaseModel):
    tasks: List[GradeRunPayload]
    pause: Optional[float] = None
    speed: Optional[float] = None


def _gradebot_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "automation" / "gradebot" / "config.json"


@app.get("/automation/grades/config", response_model=Dict[str, Any])
async def grades_config_get() -> Dict[str, Any]:
    p = _gradebot_config_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    return {"config": data}


@app.post("/automation/grades/config", response_model=Dict[str, Any])
async def grades_config_set(payload: GradeConfigPayload) -> Dict[str, Any]:
    p = _gradebot_config_path()
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    else:
        cfg = {}
    if not isinstance(cfg.get("buttons"), dict):
        cfg["buttons"] = {}
    if not isinstance(cfg.get("grid"), dict):
        cfg["grid"] = {}
    if not isinstance(cfg.get("model"), dict):
        cfg["model"] = {"strategy": "index", "index": 0}
    if payload.buttons:
        for k, v in payload.buttons.items():
            if isinstance(v, TargetPoint):
                cfg["buttons"][k] = {"x": int(v.x), "y": int(v.y)}
    if payload.first_quant_cell is not None:
        cfg["grid"]["first_quant_cell"] = (int(payload.first_quant_cell.x), int(payload.first_quant_cell.y))
    rh: Optional[int] = payload.row_height
    if rh is None and payload.first_quant_cell is not None and payload.second_quant_cell is not None:
        rh = max(1, int(payload.second_quant_cell.y) - int(payload.first_quant_cell.y))
    if rh is not None:
        cfg["grid"]["row_height"] = int(rh)
    if payload.model_index is not None:
        cfg["model"]["index"] = int(payload.model_index)
        cfg["model"]["strategy"] = "index"
    if payload.model_hotkey is not None:
        hotkey = str(payload.model_hotkey).strip()
        cfg["model"]["hotkey"] = hotkey
        cfg["model"]["strategy"] = "hotkey" if hotkey else "index"
    if payload.erp_size_order is not None:
        cfg["erp_size_order"] = [str(s).strip() for s in payload.erp_size_order if str(s).strip()]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"config": cfg}


def _load_gradebot() -> Any:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from automation.gradebot import gradebot as gb  # type: ignore
        return gb
    except ModuleNotFoundError:
        module_path = root / "automation" / "gradebot" / "gradebot.py"
        if not module_path.exists():
            raise HTTPException(status_code=500, detail="Arquivo gradebot.py não encontrado.")
        spec = importlib.util.spec_from_file_location("gradebot", str(module_path))
        if spec is None or spec.loader is None:  # pragma: no cover
            raise HTTPException(status_code=500, detail="Falha ao preparar import do GradeBot.")
        gb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gb)  # type: ignore[attr-defined]
        return gb
    except Exception as exc:  # pragma: no cover - defensivo
        raise HTTPException(status_code=500, detail=f"Falha ao importar GradeBot: {exc}")


def _run_grade_job(grades_map: Dict[str, int], model_index: Optional[int], pause: Optional[float], speed: Optional[float]) -> None:
    gb = _load_gradebot()
    if pause is not None:
        gb.pag.PAUSE = max(0.0, float(pause))
    if speed is not None:
        gb.SPEED = max(0.05, float(speed))
    gb.reset_stop_flag()
    gb.run(grades_map, model_index=model_index, activation_step=True)


@app.post("/automation/grades/run", response_model=Dict[str, str])
async def grades_run(payload: GradeRunPayload, background: BackgroundTasks) -> Dict[str, str]:
    gb = _load_gradebot()
    if payload.grades_json:
        grades_map = gb.parse_grades_json(payload.grades_json)
    elif payload.grades:
        grades_map = {str(k): int(v) for k, v in payload.grades.items()}
    else:
        raise HTTPException(status_code=400, detail="Informe 'grades' ou 'grades_json'.")
    print("[grades_run] payload:", json.dumps(grades_map, ensure_ascii=False))
    background.add_task(_run_grade_job, grades_map, payload.model_index, payload.pause, payload.speed)
    return {"status": "started"}


@app.post("/automation/grades/batch", response_model=Dict[str, Any])
async def grades_batch(payload: GradesBatchPayload) -> Dict[str, Any]:
    gb = _load_gradebot()
    if payload.pause is not None:
        gb.pag.PAUSE = max(0.0, float(payload.pause))
    if payload.speed is not None:
        gb.SPEED = max(0.05, float(payload.speed))
    gb.reset_stop_flag()
    total = 0
    activation_step = True
    for job in payload.tasks or []:
        if gb.is_cancel_requested():
            break
        if job.grades_json:
            grades_map = gb.parse_grades_json(job.grades_json)
        elif job.grades:
            grades_map = {str(k): int(v) for k, v in job.grades.items()}
        else:
            continue
        gb.run(grades_map, model_index=job.model_index, activation_step=activation_step)
        activation_step = False
        total += 1
    return {"status": "ok", "executados": total}


@app.post("/automation/grades/stop", response_model=Dict[str, str])
async def grades_stop() -> Dict[str, str]:
    gb = _load_gradebot()
    gb.request_stop()
    return {"status": "stopping"}


@app.websocket("/automation/remote/ws")
async def automation_remote_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        initial = await websocket.receive_json()
    except Exception:
        await websocket.close(code=4000, reason="invalid registration payload")
        return

    agent = await remote_agent_manager.register(websocket, initial)
    if agent is None:
        await websocket.close(code=4001, reason="registration rejected")
        return

    await websocket.send_json({"type": "registered", "agent_id": agent.agent_id, "status": "ready"})
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["agents"]},
    )

    try:
        while True:
            message = await websocket.receive_json()
            await remote_agent_manager.handle_message(agent.agent_id, message)
            msg_type = message.get("type")
            if msg_type in {"event", "result"}:
                schedule_broadcast_ui_event(
                    "state.changed",
                    {"scopes": ["agents"]},
                )
    except WebSocketDisconnect:
        pass
    finally:
        await remote_agent_manager.disconnect(agent.agent_id)
        schedule_broadcast_ui_event(
            "state.changed",
            {"scopes": ["agents"]},
        )


@app.post("/actions/reseed", include_in_schema=False)
async def reseed(items: List[ProductPayload]) -> Dict[str, int]:
    product_db.clear_current()
    records = [
        ProductRecord(
            nome=payload.nome,
            codigo=payload.codigo,
            quantidade=payload.quantidade,
            preco=payload.preco,
            categoria=payload.categoria,
            marca=payload.marca,
            preco_final=payload.preco_final,
            descricao_completa=payload.descricao_completa,
        )
        for payload in items
    ]
    product_db.replace_all(records)
    schedule_broadcast_ui_event(
        "state.changed",
        {"scopes": ["products", "totals", "brands"]},
    )
    return {"seeded": len(items)}


# Launcher hooks -----------------------------------------------------------

def ensure_dependencies() -> None:
    """Hook opcional chamado pelo launcher para garantir dependências."""
    try:
        import importlib.metadata as importlib_metadata  # Python 3.8+
    except Exception:
        import importlib_metadata  # type: ignore

    try:
        importlib_metadata.version("fastapi")
        importlib_metadata.version("uvicorn")
    except importlib_metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "Dependências FastAPI/uvicorn não instaladas. Execute: pip install fastapi uvicorn"
        ) from exc


def run(host: str = "127.0.0.1", port: int = 8800) -> None:
    """Entry point chamado pelo launcher."""
    ensure_dependencies()
    import uvicorn

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
