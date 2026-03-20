import asyncio
import base64
import io
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

try:  # Importa somente se existir
    from . import keys as api_keys
except ImportError:  # pragma: no cover - fallback quando módulo não existir
    api_keys = None  # type: ignore[assignment]
router = APIRouter(prefix="/api")

_OLLAMA_BASE_URL_ENV = os.getenv("OLLAMA_BASE_URL")
OLLAMA_BASE_URL = _OLLAMA_BASE_URL_ENV or "http://localhost:11434"
OLLAMA_API_CHAT_PATH = os.getenv("OLLAMA_API_CHAT_PATH", "/api/chat")
OLLAMA_API_STATUS_PATH = os.getenv("OLLAMA_API_STATUS_PATH", "/api/tags")


def _join_url(base: str, path: str) -> str:
    base_clean = base.rstrip("/")
    path_clean = path if path.startswith("/") else f"/{path}"
    return f"{base_clean}{path_clean}"


OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_API_KEY_HEADER = os.getenv("OLLAMA_API_KEY_HEADER", "Authorization")
OLLAMA_API_KEY_SCHEME = os.getenv("OLLAMA_API_KEY_SCHEME", "Bearer")
_JOB_API_KEYS: Dict[str, tuple[str, str]] = {}
_JOB_API_KEYS_LOCK = Lock()


def _has_configured_api_key() -> bool:
    return bool((OLLAMA_API_KEY or "").strip()) or bool(api_keys and api_keys.has_keys())


def _resolve_api_key(job_id: Optional[str] = None) -> Optional[str]:
    if OLLAMA_API_KEY:
        return OLLAMA_API_KEY.strip() or None
    if api_keys and api_keys.has_keys():
        pair: Optional[tuple[str, str]]
        announce = False
        if job_id:
            with _JOB_API_KEYS_LOCK:
                pair = _JOB_API_KEYS.get(job_id)
                if pair is None:
                    pair = api_keys.get_next_key_with_name()
                    if pair:
                        _JOB_API_KEYS[job_id] = pair
                        announce = True
        else:
            pair = api_keys.get_next_key_with_name()
            announce = True
        if not pair:
            return None
        name, key = pair
        if key and announce:
            print(f"[LLM3] utilizando chave '{name}'")
        return key.strip() if key else None
    return None


def _build_llm_headers(job_id: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    api_key_value = _resolve_api_key(job_id=job_id)
    if api_key_value:
        value = api_key_value
        if OLLAMA_API_KEY_SCHEME:
            value = f"{OLLAMA_API_KEY_SCHEME.strip()} {value}"
        headers[OLLAMA_API_KEY_HEADER] = value
    return headers


def _truncate_text(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return value
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip()


if _has_configured_api_key() and not _OLLAMA_BASE_URL_ENV:
    OLLAMA_BASE_URL = "https://ollama.com"


OLLAMA_URL = _join_url(OLLAMA_BASE_URL, OLLAMA_API_CHAT_PATH)
OLLAMA_STATUS_URL = _join_url(OLLAMA_BASE_URL, OLLAMA_API_STATUS_PATH)
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen3.5:cloud")
LLM3_MAX_DOC_CHARS = int(os.getenv("LLM3_MAX_DOC_CHARS", "14000"))
LLM3_MAX_PROMPT_CHARS = int(os.getenv("LLM3_MAX_PROMPT_CHARS", "20000"))
LLM3_RETRY_STATUS_CODES = {500, 502, 503, 504}
ROMANEIO_PROMPT = (
    "You are an information extraction assistant for shipment manifests (romaneios). "
    "Return ONLY JSON in the form {\"items\": [...]}."
    " Do not wrap the response in markdown fences."
    " Each item must contain: "
    "\"codigo\", \"descricao_original\", \"nome_curto\", \"quantidade\", \"preco\", and optionally \"tamanho\" or \"grades\". "
    "\"nome_curto\" must be a short canonical product name with only the core defining words. "
    "Remove noise such as age/gender markers (INF, JUV, BB, MASC, FEM, UNISSEX), colors, references, observations, "
    "\"SORTIDO\", and any size markers. "
    "Example: \"JAQUETA AVULSA INF MASC MOLETOM (Tam 04)\" -> \"JAQUETA AVULSA MOLETOM\". "
    "Prefer the explicit product SKU/code column for \"codigo\". Do not use NCM/SH, CFOP, barcodes, or long reference numbers as \"codigo\" when a short product code is present. "
    "If a row has one size, fill \"tamanho\" preserving labels like 1, 2, 3, 04, 06, 08, 10, 12, 14, P, M, G, GG or 34..56. "
    "Copy sizes exactly as printed. Never convert numeric sizes to letter sizes. If a trailing token is only a size, keep it in \"tamanho\" and do not append it to \"codigo\". "
    "If the document already shows a full grade distribution for one product, fill \"grades\" as an object mapping size to quantity. "
    "Do not merge rows. Quantities must be integers and \"preco\" must be the unit price."
)

# Prompt para extração de grades a partir de NF/romaneio
GRADE_PROMPT = (
    "You are an information extraction assistant. Extract product GRADES from the provided invoice/romaneio text or images. "
    "Return ONLY JSON. The JSON must be an object with a key 'items' that is an array. Each item must contain: "
    "Do not wrap the response in markdown fences. "
    "'codigo' (string or null), 'nome' (string or null), and 'grades' (object mapping size labels to integer quantities). "
    "Example: {\n  \"items\": [ { \"codigo\": \"123\", \"nome\": \"CAMISETA X\", \"grades\": { \"P\": 2, \"M\": 3, \"G\": 1 } } ]\n}. "
    "Use usual apparel sizes like PP, P, M, G, GG, or numeric sizes like 34..52 when applicable. Quantities must be integers."
)

print(
    f"[LLM3] LLM host={OLLAMA_BASE_URL} chat_path={OLLAMA_API_CHAT_PATH} auth={'enabled' if _has_configured_api_key() else 'disabled'}"
)


class Mode(str, Enum):
    DEFAULT = "default"
    ROMANEIO = "romaneio_extractor"
    GRADE = "grade_extractor"


class ImagePayload(BaseModel):
    name: str
    data: str
    mime: Optional[str] = None


class DocumentPayload(BaseModel):
    name: str
    content: str


class ChatRequest(BaseModel):
    message: str = ""
    mode: Mode = Mode.DEFAULT
    images: Optional[List[ImagePayload]] = None
    documents: Optional[List[DocumentPayload]] = None


class ChatResponse(BaseModel):
    role: str
    content: str
    saved_file: Optional[str] = None
    llm_prompt: Optional[str] = None
    llm_prompt_len: Optional[int] = None
    llm_model: Optional[str] = None
    llm_images: Optional[int] = None


async def _extract_text(message):
    content = message.get("content", "")
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue

            text_value = item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value)
                continue

            alt_value = item.get("output_text") or item.get("content")
            if isinstance(alt_value, str) and alt_value.strip():
                parts.append(alt_value)
        return "".join(parts)
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("text", "output_text", "content"):
            value = content.get(key)
            if isinstance(value, str):
                return value
    return ""


@router.get("/status")
async def get_status():
    """Retorna informações sobre o modelo conectado"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(OLLAMA_STATUS_URL, headers=_build_llm_headers())
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            model_exists = any(m.get("name") == MODEL_NAME for m in models)
            return {
                "model": MODEL_NAME,
                "connected": model_exists,
                "ollama_running": True,
            }
    except Exception:
        return {
            "model": MODEL_NAME,
            "connected": False,
            "ollama_running": False,
        }



@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    images: List[ImagePayload] = []
    documents: List[DocumentPayload] = []
    errors: List[str] = []

    for uploaded in files:
        content = await uploaded.read()
        suffix = Path(uploaded.filename or "").suffix.lower()

        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
            b64_data = base64.b64encode(content).decode("utf-8")
            mime = uploaded.content_type or "image/jpeg"
            images.append(
                ImagePayload(
                    name=uploaded.filename or "imagem",
                    data=b64_data,
                    mime=mime,
                )
            )
            continue

        if suffix == ".txt":
            text_content = content.decode("utf-8", errors="ignore")
            documents.append(
                DocumentPayload(
                    name=uploaded.filename or "texto.txt",
                    content=text_content,
                )
            )
            continue

        if suffix == ".pdf":
            extracted_text: Optional[str] = None
            min_chars = int(os.getenv("PDF_TEXT_MIN_CHARS", "200"))

            # 1) Tenta extrair texto com pdfplumber
            try:
                import pdfplumber

                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    parts: List[str] = []
                    for page in pdf.pages:
                        extracted = page.extract_text() or ""
                        if extracted.strip():
                            parts.append(extracted)
                if parts:
                    extracted_text = "\n\n".join(parts)
            except ImportError:
                pdfplumber = None  # type: ignore[assignment]
            except Exception as exc:
                errors.append(f"Erro ao processar PDF com pdfplumber '{uploaded.filename}': {exc}")

            # 2) Se falhar, tenta PyPDF2
            if extracted_text is None or len(extracted_text.strip()) < min_chars:
                try:
                    from PyPDF2 import PdfReader

                    reader = PdfReader(io.BytesIO(content))
                    parts = []
                    for page in reader.pages:
                        extracted = page.extract_text() or ""
                        if extracted.strip():
                            parts.append(extracted)
                    if parts:
                        extracted_text = "\n\n".join(parts)
                except ImportError:
                    errors.append(
                        "Dependências para leitura de PDF ausentes. Instale 'pdfplumber' ou 'PyPDF2'."
                    )
                except Exception as exc:
                    errors.append(f"Erro ao processar PDF com PyPDF2 '{uploaded.filename}': {exc}")

            # 3) Se o texto ainda for insuficiente, renderiza páginas em imagens (OCR-friendly)
            if extracted_text is None or len(extracted_text.strip()) < min_chars:
                try:
                    import fitz  # PyMuPDF

                    doc = fitz.open(stream=content, filetype="pdf")
                    zoom = float(os.getenv("PDF_RENDER_ZOOM", "2.0"))  # 2.0 ~= 144 DPI
                    mat = fitz.Matrix(zoom, zoom)
                    max_pages = int(os.getenv("PDF_RENDER_MAX_PAGES", "30"))

                    for page_index, page in enumerate(doc, start=1):
                        if page_index > max_pages:
                            break
                        pix = page.get_pixmap(matrix=mat)
                        img_bytes = pix.tobytes("png")
                        b64_data = base64.b64encode(img_bytes).decode("utf-8")
                        images.append(
                            ImagePayload(
                                name=f"{(uploaded.filename or 'arquivo.pdf')}#p{page_index}",
                                data=b64_data,
                                mime="image/png",
                            )
                        )
                except ImportError:
                    errors.append("PyMuPDF não instalado; renderização de páginas em imagens indisponível.")
                except Exception as exc:
                    errors.append(f"Erro ao renderizar PDF '{uploaded.filename}': {exc}")

            # 4) Se houver texto, envia como documento também (ajuda no chunking posterior)
            if extracted_text and len(extracted_text.strip()) >= min_chars:
                documents.append(
                    DocumentPayload(
                        name=uploaded.filename or "arquivo.pdf",
                        content=extracted_text,
                    )
                )
            elif not images:
                errors.append(f"Não foi possível extrair conteúdo útil do PDF '{uploaded.filename}'.")
            continue

        errors.append(f"Tipo de arquivo não suportado: {uploaded.filename}")

    return {
        "images": [image.dict() for image in images],
        "documents": [doc.dict() for doc in documents],
        "errors": errors,
    }


def _save_to_desktop(content: str, prefix: str) -> Optional[str]:
    base = Path(os.path.join(os.path.expanduser("~"), "Desktop"))
    target_dir = base / "RomaneiosProcessados"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = target_dir / f"{prefix}_{timestamp}.txt"
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)
    except Exception:
        return None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    user_message = (request.message or "").strip()
    job_id = (http_request.headers.get("x-job-id") or "").strip() or None
    images_payload: List[str] = []
    image_notes: List[str] = []

    if request.images:
        for image in request.images:
            base64_data = (image.data or "").strip()
            if not base64_data:
                continue
            images_payload.append(base64_data)
            if image.name:
                image_notes.append(f"Imagem anexada: {image.name}")

    message_sections: List[str] = []

    if request.mode == Mode.ROMANEIO:
        message_sections.append(ROMANEIO_PROMPT)
        if user_message:
            message_sections.append(f"Notas adicionais:\n{user_message}")
    elif request.mode == Mode.GRADE:
        message_sections.append(GRADE_PROMPT)
        if user_message:
            message_sections.append(f"Notas adicionais:\n{user_message}")
    elif user_message:
        message_sections.append(user_message)

    if request.documents:
        doc_sections = []
        for document in request.documents:
            if not document or not (document.content or "").strip():
                continue
            name = document.name or "Documento"
            content = _truncate_text(document.content.strip(), LLM3_MAX_DOC_CHARS)
            doc_sections.append(f"{name}:\n{content}")
        docs_text = "\n\n".join(doc_sections)
        if docs_text:
            message_sections.append(f"Contexto adicional:\n{docs_text}")

    if image_notes:
        notes_text = "\n".join(image_notes)
        message_sections.append(notes_text)

    message_text = "\n\n".join(section for section in message_sections if section.strip())
    message_text = _truncate_text(message_text, LLM3_MAX_PROMPT_CHARS)

    if not message_text:
        if images_payload:
            if request.mode == Mode.ROMANEIO:
                message_text = ROMANEIO_PROMPT
            elif request.mode == Mode.GRADE:
                message_text = GRADE_PROMPT
            else:
                message_text = "Analyze the attached images and provide insights."
        else:
            raise HTTPException(status_code=400, detail="Mensagem vazia")

    content_string = message_text

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": content_string,
                **({"images": images_payload} if images_payload else {}),
            }
        ],
        "stream": False,
    }
    if request.mode in {Mode.ROMANEIO, Mode.GRADE}:
        payload["format"] = "json"
        payload["think"] = False
    attempt = 0
    last_error: Optional[Exception] = None
    while attempt < 3:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(OLLAMA_TIMEOUT_SECONDS, connect=10.0)
            ) as client:
                response = await client.post(
                    OLLAMA_URL,
                    json=payload,
                    headers=_build_llm_headers(job_id=job_id),
                )
                response.raise_for_status()
                break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in LLM3_RETRY_STATUS_CODES and attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                attempt += 1
                last_error = exc
                continue
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        except httpx.RequestError as exc:
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                attempt += 1
                last_error = exc
                continue
            raise HTTPException(status_code=502, detail=f"Falha ao conectar ao serviço LLM: {exc}") from exc
    else:
        if last_error:
            raise HTTPException(status_code=503, detail=f"Serviço LLM indisponível: {last_error}") from last_error
        raise HTTPException(status_code=503, detail="Serviço LLM indisponível")
    data = response.json()
    message = data.get("message", {})
    content = await _extract_text(message)
    role = message.get("role", "assistant")
    if not content:
        content = data.get("response", "")

    saved_file: Optional[str] = None
    if request.mode == Mode.ROMANEIO and content:
        saved_file = _save_to_desktop(content, "romaneio")

    return ChatResponse(
        role=role,
        content=content,
        saved_file=saved_file,
        llm_prompt=content_string,
        llm_prompt_len=len(content_string),
        llm_model=MODEL_NAME,
        llm_images=len(images_payload),
    )
