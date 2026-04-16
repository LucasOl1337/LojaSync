from __future__ import annotations

import base64
import io
import json
import re
import string
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
from typing import Any

from app.domain.products.entities import Product

ROMANEIO_IMAGE_MESSAGE = (
    "The attached image is a scanned invoice product table. "
    "Extract every visible product row and return JSON only in the format "
    '{"items":[{"codigo":"","nome":"","quantidade":0,"preco":""}]}. '
    "Use the short SKU/product code as codigo, not NCM/SH, CFOP, barcode, or long reference numbers. "
    "Copy sizes exactly as printed; never convert numeric sizes to letter sizes. "
    "If a trailing token is only a size, put it in tamanho and do not append it to codigo. "
    "If a row is unreadable, partially cut, or ambiguous, skip it instead of guessing."
)

ROMANEIO_CROPPED_IMAGE_MESSAGE = (
    "The attached image is a cropped segment of a tall scanned invoice product table. "
    "Extract only the fully visible product rows from this crop and return JSON only in the format "
    '{"items":[{"codigo":"","nome":"","quantidade":0,"preco":""}]}. '
    "Use the short SKU/product code as codigo, not NCM/SH, CFOP, barcode, or long reference numbers. "
    "Copy sizes exactly as printed; never convert numeric sizes to letter sizes. "
    "If a trailing token is only a size, put it in tamanho and do not append it to codigo. "
    "Do not guess rows cut by the crop boundary; ignore partial rows."
)

_REMESSA_REGEX = re.compile(r"(?i)qtd\s+de\s+.*?remessa\s*:\s*(?P<qty>\d+)")
_TOTAL_PRODUCTS_REGEX = re.compile(
    r"(?i)valor\s+total\s+dos\s+produtos(?:\s*[:\-]|\s+)(?P<value>\d+(?:\.\d{3})*,\d{2})"
)
_TOTAL_NOTE_REGEX = re.compile(
    r"(?i)valor\s+total\s+da\s+nota(?:\s*[:\-]|\s+)(?P<value>\d+(?:\.\d{3})*,\d{2})"
)
_CONSISTENCY_TOLERANCE = Decimal("0.05")


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


def decode_text_content(
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
        warnings.append("Tipo de arquivo nao textual para parser local; aguardando retorno estruturado do LLM.")
        return "", warnings

    for encoding in ("utf-8", "latin-1"):
        try:
            return contents.decode(encoding), warnings
        except Exception:
            continue
    return "", warnings


def _normalize_header_token(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("cÃ³digo", "codigo")
    normalized = normalized.replace("descriÃ§Ã£o", "descricao")
    normalized = normalized.replace("preÃ§o", "preco")
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
    if qty <= 0 or qty > 100000:
        return 1
    return qty


def _normalize_price(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        return _normalize_decimal_price(raw)
    text = str(raw).strip()
    if len(text) > 40:
        text = text[:40]
    return text


def _parse_decimal_value(raw: Any) -> Decimal | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _normalize_decimal_price(raw: Any, *, digits: int = 2) -> str:
    value = _parse_decimal_value(raw)
    if value is None:
        return _normalize_price(raw)
    quantizer = Decimal("1").scaleb(-digits)
    normalized = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    return format(normalized, "f").replace(".", ",")


def _normalize_product_grades(raw: Any) -> list[dict[str, Any]] | None:
    if not raw:
        return None
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for tamanho, quantidade in raw.items():
            raw_size = str(tamanho or "").strip()
            size = _coerce_size_hint(raw_size) or re.sub(r"[^A-Za-z0-9]+", "", raw_size).upper()
            qty = _parse_qty(quantidade)
            if not size or qty <= 0:
                continue
            items.append({"tamanho": size, "quantidade": qty})
        return items or None
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                raw_size = str(entry.get("tamanho") or entry.get("size") or "").strip()
                qty = _parse_qty(entry.get("quantidade"))
            else:
                raw_size = str(getattr(entry, "tamanho", "") or getattr(entry, "size", "") or "").strip()
                qty = _parse_qty(getattr(entry, "quantidade", None))
            size = _coerce_size_hint(raw_size) or re.sub(r"[^A-Za-z0-9]+", "", raw_size).upper()
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
        try:
            number = int(candidate)
        except Exception:
            return ""
        return str(number) if number > 0 else ""
    if candidate in {"U", "PP", "P", "M", "G", "GG", "XG", "XXG", "G1", "G2", "G3", "G4"}:
        return candidate
    return ""


def _extract_document_money(pattern: re.Pattern[str], text: str) -> Decimal | None:
    match = pattern.search(str(text or ""))
    if not match:
        return None
    return _parse_decimal_value(match.group("value"))


def _extract_remessa_quantity(text: str) -> int | None:
    match = _REMESSA_REGEX.search(str(text or ""))
    if not match:
        return None
    try:
        quantity = int(match.group("qty"))
    except Exception:
        return None
    return quantity if quantity > 0 else None


def analyze_parsed_document(text: str, records: list[Product]) -> dict[str, Any]:
    source_text = str(text or "").strip()
    if not source_text:
        return {"warnings": [], "metrics": {}}

    extracted_quantity = sum(max(int(item.quantidade or 0), 0) for item in (records or []))
    extracted_total_products = Decimal("0")
    for item in records or []:
        unit_price = _parse_decimal_value(item.preco)
        if unit_price is None:
            continue
        extracted_total_products += unit_price * Decimal(max(int(item.quantidade or 0), 0))

    remessa_quantity = _extract_remessa_quantity(source_text)
    document_total_products = _extract_document_money(_TOTAL_PRODUCTS_REGEX, source_text)
    document_total_note = _extract_document_money(_TOTAL_NOTE_REGEX, source_text)

    quantity_matches_remessa = remessa_quantity is not None and extracted_quantity == remessa_quantity
    products_value_matches_document = False
    matched_reference = ""
    if document_total_products is not None:
        products_value_matches_document = (
            abs(extracted_total_products - document_total_products) <= _CONSISTENCY_TOLERANCE
        )
        if products_value_matches_document:
            matched_reference = "produtos"
    if not products_value_matches_document and document_total_note is not None:
        products_value_matches_document = abs(extracted_total_products - document_total_note) <= _CONSISTENCY_TOLERANCE
        if products_value_matches_document:
            matched_reference = "nota"

    warnings: list[str] = []
    if remessa_quantity is not None and not quantity_matches_remessa:
        warnings.append(
            f"Quantidade extraida ({extracted_quantity}) difere da quantidade de remessa impressa no documento ({remessa_quantity})."
        )

    if (document_total_products is not None or document_total_note is not None) and not products_value_matches_document:
        printed_totals: list[str] = []
        if document_total_products is not None:
            printed_totals.append(f"produtos: R$ {_normalize_decimal_price(document_total_products)}")
        if document_total_note is not None:
            printed_totals.append(f"nota: R$ {_normalize_decimal_price(document_total_note)}")
        warnings.append(
            "O total extraido dos itens nao bate com a nota. "
            f"Extraido: R$ {_normalize_decimal_price(extracted_total_products)}. "
            f"Documento: {' | '.join(printed_totals)}."
        )

    metrics: dict[str, Any] = {
        "remessa_quantity": remessa_quantity,
        "quantity_matches_remessa": quantity_matches_remessa if remessa_quantity is not None else None,
        "document_total_products": _normalize_decimal_price(document_total_products) if document_total_products is not None else None,
        "document_total_note": _normalize_decimal_price(document_total_note) if document_total_note is not None else None,
        "extracted_total_products": _normalize_decimal_price(extracted_total_products),
        "products_value_matches_document": products_value_matches_document if (document_total_products is not None or document_total_note is not None) else None,
        "products_value_match_reference": matched_reference or None,
    }
    return {"warnings": warnings, "metrics": metrics}


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


_INVOICE_QTY_PATTERN = r"\d+(?:\.\d{3})*,\d{3}"
_INVOICE_UNIT_PATTERN = r"\d+(?:\.\d{3})*,\d{4}"
_INVOICE_MONEY_PATTERN = r"\d+(?:\.\d{3})*,\d{2}"
_INVOICE_LINE_REGEX = re.compile(
    rf"^\s*(?P<codigo>\d{{5,}})\s+"
    rf"(?P<descricao>.+?)\s+"
    rf"(?P<ncm>\d{{4}}\.\d{{2}}\.\d{{2}})\s+"
    rf"(?P<cst>\d{{3}})\s+"
    rf"(?P<cfop>\d{{4}})\s+"
    rf"(?P<un>[A-Z]{{2,5}})\s+"
    rf"(?P<quantidade>{_INVOICE_QTY_PATTERN})\s+"
    rf"(?P<unitario>{_INVOICE_UNIT_PATTERN})\s+"
    rf"(?P<valor_total>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<bc_icms>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<valor_icms>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<valor_ipi>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<aliq_icms>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<aliq_ipi>{_INVOICE_MONEY_PATTERN})\s*$"
)


def _extract_invoice_size(description: str) -> str:
    match = re.search(
        r"(?i)\btam(?:anho)?\.?\s*[:\-]?\s*([0-9]{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4])\b",
        str(description or "").strip(),
    )
    if not match:
        return ""
    return _coerce_size_hint(match.group(1))


def _normalize_invoice_name(description: str) -> str:
    normalized = str(description or "").strip()
    if not normalized:
        return ""
    normalized = re.sub(r"(?i)\bcor\s+[0-9A-Z]+\b", "", normalized)
    normalized = re.sub(
        r"(?i)\btam(?:anho)?\.?\s*[:\-]?\s*(?:[0-9]{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4])\b",
        "",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip(" -_/")
    return normalized


def _split_code_and_size(code: Any) -> tuple[str, str]:
    value = str(code or "").strip()
    if not value:
        return "", ""
    match = re.fullmatch(
        r"([0-9A-Za-z._/-]+)\s+([0-9]{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4])",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value, ""
    size = _coerce_size_hint(match.group(2))
    if not size:
        return value, ""
    return match.group(1).strip(), size


def build_romaneio_image_message(images: list[dict[str, Any]]) -> str:
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


def products_to_text(records: list[Product]) -> str:
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


def split_text_chunks(text: str, *, max_chars: int = 8000) -> list[str]:
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


def extract_structured_invoice_row_lines(text: str) -> list[str]:
    rows: list[str] = []
    for raw_line in (text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        if _INVOICE_LINE_REGEX.match(line):
            rows.append(line)
    return rows


def split_structured_invoice_chunks(
    text: str,
    *,
    max_lines: int = 24,
    max_chars: int = 5000,
) -> list[str]:
    rows = extract_structured_invoice_row_lines(text)
    if not rows:
        return []

    safe_max_lines = max(int(max_lines or 1), 1)
    safe_max_chars = max(int(max_chars or 1), 1)
    chunks: list[str] = []
    current_rows: list[str] = []
    current_chars = 0

    for row in rows:
        projected_chars = current_chars + len(row) + (1 if current_rows else 0)
        if current_rows and (len(current_rows) >= safe_max_lines or projected_chars > safe_max_chars):
            chunks.append("\n".join(current_rows))
            current_rows = [row]
            current_chars = len(row)
            continue
        current_rows.append(row)
        current_chars = projected_chars

    if current_rows:
        chunks.append("\n".join(current_rows))
    return chunks


def split_image_batches(images: list[dict[str, Any]], *, batch_size: int = 1) -> list[list[dict[str, Any]]]:
    safe_size = max(int(batch_size or 1), 1)
    if not images:
        return []
    return [images[index : index + safe_size] for index in range(0, len(images), safe_size)]


def slice_image_payloads(images: list[dict[str, Any]], *, vertical_slices: int) -> list[dict[str, Any]]:
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


def extract_llm_json_items(text: str) -> list[dict[str, Any]]:
    return _extract_json_items(text)


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
    desc_keys = (
        "nome_curto",
        "short_name",
        "nome_limpo",
        "descricao_resumida",
        "descricao",
        "description",
        "produto",
        "nome",
        "item",
    )
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
        raw_description = str(
            _pick(raw_desc_keys) or _pick(("descricao", "description", "produto", "item", "nome")) or ""
        ).strip()
        nome = str(_pick(desc_keys) or raw_description).strip()
        grades_payload = _pick(grades_keys)
        size_payload = _pick(size_keys)
        codigo, code_size_hint = _split_code_and_size(codigo)
        explicit_size = _coerce_size_hint(size_payload)
        inferred_size = explicit_size or code_size_hint or _extract_embedded_size(raw_description) or _extract_embedded_size(nome)
        normalized_grades = _normalize_product_grades(grades_payload)
        if normalized_grades is None and inferred_size:
            normalized_grades = _normalize_product_grades([{"tamanho": inferred_size, "quantidade": _pick(qty_keys)}])
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
        codigo = parts[header_map["code"]] if "code" in header_map and header_map["code"] < len(parts) else (parts[0] if parts else "")
        nome = parts[header_map["desc"]] if "desc" in header_map and header_map["desc"] < len(parts) else (parts[1] if len(parts) > 1 else "")
        if not codigo or not _has_digits(codigo) or not nome:
            continue
        quantidade = parts[header_map["qty"]] if "qty" in header_map and header_map["qty"] < len(parts) else (parts[2] if len(parts) > 2 else "1")
        preco = parts[header_map["price"]] if "price" in header_map and header_map["price"] < len(parts) else (parts[3] if len(parts) > 3 else "")
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


def _parse_structured_invoice_lines(text: str) -> list[Product]:
    records: list[Product] = []
    for raw_line in (text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        match = _INVOICE_LINE_REGEX.match(line)
        if not match:
            continue

        codigo = str(match.group("codigo") or "").strip()
        descricao_original = str(match.group("descricao") or "").strip()
        nome = _normalize_invoice_name(descricao_original) or descricao_original
        quantidade = _parse_qty(match.group("quantidade"))
        preco = _normalize_decimal_price(match.group("unitario"))
        tamanho = _extract_invoice_size(descricao_original)
        grades = [{"tamanho": tamanho, "quantidade": quantidade}] if tamanho else None

        if not codigo or not _has_digits(codigo) or not nome:
            continue
        records.append(
            _build_product(
                codigo,
                nome,
                quantidade,
                preco,
                descricao_completa=descricao_original or nome,
                grades=grades,
            )
        )
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


def looks_like_binary_blob(text: str) -> bool:
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
    if looks_like_binary_blob(code) or looks_like_binary_blob(name):
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
    meta_patterns = ("data", "hora", "cnpj", "pedido", "numero", "desconto", "valor total", "serie")
    if any(pattern in lowered_name for pattern in meta_patterns):
        return False

    if record.quantidade <= 0 or record.quantidade > 100000:
        return False
    return True


def filter_suspect_records(records: list[Product]) -> list[Product]:
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


def parse_candidate_content(text: str) -> list[Product]:
    if not text.strip():
        return []
    if looks_like_binary_blob(text):
        return []
    structured = _parse_structured_invoice_lines(text)
    if structured:
        return filter_suspect_records(structured)
    candidates = _parse_llm_romaneio(text)
    if candidates:
        return filter_suspect_records(candidates)
    fallback = _parse_romaneio_lines(text)
    return filter_suspect_records(fallback)


__all__ = [
    "analyze_parsed_document",
    "build_romaneio_image_message",
    "decode_text_content",
    "extract_llm_json_items",
    "extract_structured_invoice_row_lines",
    "filter_suspect_records",
    "looks_like_binary_blob",
    "parse_candidate_content",
    "products_to_text",
    "save_romaneio_text",
    "split_structured_invoice_chunks",
    "slice_image_payloads",
    "split_image_batches",
    "split_text_chunks",
]
