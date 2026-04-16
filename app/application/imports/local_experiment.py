from __future__ import annotations

import io
import json
import re
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


_INVOICE_QTY_PATTERN = r"\d+(?:\.\d{3})*,\d{2,4}"
_INVOICE_UNIT_PATTERN = r"\d+(?:\.\d{3})*,\d{2,4}"
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
_CONCAT_PREFIX_REGEX = re.compile(
    r"^(?P<codigo>(?:\d{15}|\d{14}[A-Z]|\d{15}[A-Z]?))"
    r"(?P<descricao>.+?)"
    r"(?P<ncm>\d{8})"
    r"(?P<cst>\d{3})"
    r"(?P<cfop>\d{4})"
    r"(?P<un>[A-Z]{2,5})"
    r"(?P<tail>.+)$"
)

_MONTH_SIZE_ORDER = {"RN": 0, "0M": 0, "1M": 1, "3M": 3, "6M": 6, "9M": 9, "12M": 12, "18M": 18, "24M": 24}
_ALPHA_SIZE_ORDER = {
    "RN": 0,
    "U": 1,
    "UN": 1,
    "PP": 2,
    "P": 3,
    "M": 4,
    "G": 5,
    "GG": 6,
    "XG": 7,
    "XXG": 8,
    "G1": 9,
    "G2": 10,
    "G3": 11,
    "G4": 12,
    "E": 13,
}
_SIZE_REGEX = re.compile(
    r"(?i)\btam(?:anho)?\.?\s*[:\-]?\s*"
    r"(?P<size>\d{1,3}M|\d{1,3}|PP|P|M|G|GG|XG|XXG|G[1-4]|U|UN|RN|E)\b"
)
_COLOR_REGEX = re.compile(r"(?i)\bcor\s+(?P<color>[0-9A-Z]+)\b")
_REMESSA_REGEX = re.compile(r"(?i)qtd\s+de\s+.*?remessa\s*:\s*(?P<qty>\d+)")
_TOTAL_PRODUCTS_REGEX = re.compile(
    r"(?i)valor\s+total\s+dos\s+produtos(?:\s*[:\-]|\s+)(?P<value>\d+(?:\.\d{3})*,\d{2})"
)
_TOTAL_NOTE_REGEX = re.compile(
    r"(?i)valor\s+total\s+da\s+nota(?:\s*[:\-]|\s+)(?P<value>\d+(?:\.\d{3})*,\d{2})"
)
_TOTAL_DISCOUNT_REGEX = re.compile(r"(?i)\bdesconto\b(?:\s*[:\-]|\s+)(?P<value>\d+(?:\.\d{3})*,\d{2})")
_OCR_CODE_REGEXES = (
    re.compile(r"^\d{8,16}[A-Z]?$"),
    re.compile(r"^\d{5,8}[A-Z]?$"),
    re.compile(r"^\d{5,8}[._-]\d{2,4}[A-Z]?$"),
    re.compile(r"^[A-Z]{2}[._-][A-Z]{3}[ ._-]\d{5}$"),
    re.compile(r"^[A-Z]{2}[._-][A-Z]{3}[._-]\d{5}$"),
)
_OCR_NUMBER_REGEX = re.compile(r"^\d+(?:[.,]\d{2,4})?$")
_MONEY_CAPTURE_REGEX = re.compile(r"\d+(?:\.\d{3})*(?:,\d{2}|\.\d{2})")
_CATIVE_ROW_REGEX = re.compile(
    rf"^(?P<codigo>[A-Z]\d{{5}}-[A-Z0-9]{{4}}-[A-Z0-9]{{1,3}})\s+"
    rf"(?P<descricao>.+?)\s+"
    rf"(?P<codigo_repetido>[A-Z]\d{{5}}-[A-Z0-9]{{4}}-[A-Z0-9]{{1,3}})\s+"
    rf"(?P<ncm>\d{{8}})\s+"
    rf"(?P<cstcfop>\d{{7}})\s+"
    rf"(?P<un>[A-Z]{{2,5}})\s+"
    rf"(?P<quantidade>{_INVOICE_QTY_PATTERN})\s+"
    rf"(?P<unitario>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<valor_total>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<bc_icms>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<valor_icms>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<aliq_icms>{_INVOICE_MONEY_PATTERN})\s*$"
)
_AURIFLAMA_ROW_WITH_DESC_REGEX = re.compile(
    r"^\s*(?P<codigo>\d{5})\s+(?P<descricao>.+?)\s+(?P<quantidade>\d+)\s+(?P<unitario>\d+\.\d{2})\s+(?P<valor_total>\d{1,3}(?:,\d{3})*\.\d{2})\s*$"
)
_AURIFLAMA_ROW_SIMPLE_REGEX = re.compile(
    r"^\s*(?P<codigo>\d{5})\s+(?P<quantidade>\d+)\s+(?P<unitario>\d+\.\d{2})\s+(?P<valor_total>\d{1,3}(?:,\d{3})*\.\d{2})\s*$"
)
_SISPLAN_PRODUCT_HEADER_REGEX = re.compile(r"^\s*(?P<codigo>\d{4,5})\s*-\s*(?P<descricao>.+?)\s*$")
_SISPLAN_ROW_REGEX = re.compile(
    rf"^\s*(?P<cor>\d+)\s*-\s*(?P<padrao>.+?)\s+(?P<tamanho>\d{{1,2}})\s+"
    rf"(?P<valor_total>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<valor_bruto>{_INVOICE_MONEY_PATTERN})\s+"
    rf"(?P<quantidade>\d+)\s+"
    rf"(?P<unitario>{_INVOICE_MONEY_PATTERN})\s*$"
)
_LEGACY_DANFE_NUMERIC_ROW_REGEX = re.compile(
    rf"^(?P<codigo>\d{{4,6}})\s+\d{{3}}\s+\d{{4}}\s+(?P<un>[A-Z]{{2,5}})\s+"
    rf"(?P<quantidade>{_INVOICE_QTY_PATTERN})\s+"
    rf"(?P<unitario>{_INVOICE_UNIT_PATTERN})\s+"
    rf"(?P<valor_total>{_INVOICE_MONEY_PATTERN})\b"
)
_OCR_PS_SCRIPT = r"""
param([string]$PathsJson)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null

function AwaitWinRt($op, $typeName) {
  $type = [Type]$typeName
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } |
    Select-Object -First 1
  $generic = $method.MakeGenericMethod($type)
  $task = $generic.Invoke($null, @($op))
  $task.Wait()
  return $task.Result
}

$paths = $PathsJson | ConvertFrom-Json
$payload = @()
foreach ($path in $paths) {
  $file = AwaitWinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) 'Windows.Storage.StorageFile'
  $stream = AwaitWinRt ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) 'Windows.Storage.Streams.IRandomAccessStream'
  $decoder = AwaitWinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) 'Windows.Graphics.Imaging.BitmapDecoder'
  $bitmap = AwaitWinRt ($decoder.GetSoftwareBitmapAsync()) 'Windows.Graphics.Imaging.SoftwareBitmap'
  $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
  $result = AwaitWinRt ($engine.RecognizeAsync($bitmap)) 'Windows.Media.Ocr.OcrResult'
  $lines = foreach ($line in $result.Lines) {
    $first = $line.Words | Select-Object -First 1
    if ($null -eq $first) { continue }
    [pscustomobject]@{
      text = $line.Text
      x = [int]$first.BoundingRect.X
      y = [int]$first.BoundingRect.Y
    }
  }
  $payload += [pscustomobject]@{
    path = $path
    width = [int]$decoder.PixelWidth
    height = [int]$decoder.PixelHeight
    text = $result.Text
    lines = $lines
  }
}
$payload | ConvertTo-Json -Depth 6 -Compress
"""


@dataclass(slots=True)
class ParsedInvoiceRow:
    codigo: str
    nome: str
    descricao_completa: str
    cor: str | None
    tamanho: str | None
    quantidade: int
    preco: str
    unidade: str
    valor_total: str | None = None
    desconto_total: str | None = None


@dataclass(slots=True)
class OcrPagePayload:
    width: int
    height: int
    text: str
    lines: list[dict[str, Any]]


def _parse_decimal(raw: str | Decimal | None) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    normalized = text.replace(" ", "")
    if "." in normalized and "," in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    elif normalized.count(".") == 1:
        left, right = normalized.split(".", 1)
        if len(right) in {2, 3, 4}:
            normalized = f"{left}.{right}"
        else:
            normalized = normalized.replace(".", "")
    else:
        normalized = normalized.replace(".", "")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _format_price(raw: str | Decimal | None, *, digits: int = 2) -> str:
    value = _parse_decimal(raw)
    if value is None:
        return str(raw or "").strip()
    quantizer = Decimal("1").scaleb(-digits)
    return format(value.quantize(quantizer, rounding=ROUND_HALF_UP), "f").replace(".", ",")


def _parse_quantity(raw: str | Decimal | None) -> int:
    value = _parse_decimal(raw)
    if value is None:
        return 0
    try:
        return max(int(value.to_integral_value(rounding=ROUND_HALF_UP)), 0)
    except Exception:
        return 0


def _normalize_size(value: str | None) -> str | None:
    label = str(value or "").strip().upper()
    if not label:
        return None
    label = re.sub(r"[^A-Z0-9]+", "", label)
    if not label:
        return None
    if label in _MONTH_SIZE_ORDER:
        return label
    if label in _ALPHA_SIZE_ORDER:
        return label
    if label.isdigit():
        number = int(label)
        return str(number) if number > 0 else None
    return label


def _size_sort_key(size: str) -> tuple[int, int | str]:
    normalized = _normalize_size(size) or str(size or "").strip().upper()
    if normalized in _MONTH_SIZE_ORDER:
        return (0, _MONTH_SIZE_ORDER[normalized])
    if normalized in _ALPHA_SIZE_ORDER:
        return (1, _ALPHA_SIZE_ORDER[normalized])
    if normalized.isdigit():
        return (2, int(normalized))
    return (3, normalized)


def _extract_pdf_text(contents: bytes) -> tuple[str, int]:
    if not contents:
        return "", 0
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(contents))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
        return "\n\n".join(parts).strip(), len(reader.pages)
    except Exception:
        return "", 0


def _normalize_header_cell(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def _find_table_indexes(header: list[str]) -> dict[str, int]:
    indexes: dict[str, int] = {}
    for index, cell in enumerate(header):
        normalized = _normalize_header_cell(cell)
        if not normalized:
            continue
        if "descr" in normalized:
            indexes.setdefault("desc", index)
        elif ("codigo" in normalized or normalized.startswith("cod")) and "prod" in normalized:
            indexes.setdefault("code", index)
        elif "quant" in normalized:
            indexes.setdefault("qty", index)
        elif ("valor" in normalized and "unit" in normalized) or "vunit" in normalized:
            indexes.setdefault("unit", index)
        elif "valortotal" in normalized and "produtos" not in normalized:
            indexes.setdefault("total", index)
        elif "unid" in normalized or normalized == "un":
            indexes.setdefault("un", index)
        elif "desconto" in normalized:
            indexes.setdefault("discount", index)
    return indexes


def _parse_pdf_table_rows(contents: bytes) -> list[ParsedInvoiceRow]:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []

    rows: list[ParsedInvoiceRow] = []
    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages or []:
                tables = page.extract_tables() or []
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = [str(cell or "").replace("\n", " ").strip() for cell in table[0]]
                    indexes = _find_table_indexes(header)
                    if "code" not in indexes or "desc" not in indexes:
                        continue
                    for row in table[1:]:
                        cells = [str(cell or "").replace("\n", " ").strip() for cell in row]
                        if not cells:
                            continue
                        codigo = re.sub(r"\s+", "", cells[indexes["code"]]) if indexes["code"] < len(cells) else ""
                        descricao = cells[indexes["desc"]] if indexes["desc"] < len(cells) else ""
                        quantidade = _parse_quantity(cells[indexes["qty"]]) if "qty" in indexes and indexes["qty"] < len(cells) else 1
                        unitario = cells[indexes["unit"]] if "unit" in indexes and indexes["unit"] < len(cells) else ""
                        valor_total = cells[indexes["total"]] if "total" in indexes and indexes["total"] < len(cells) else ""
                        desconto = cells[indexes["discount"]] if "discount" in indexes and indexes["discount"] < len(cells) else ""
                        unidade = cells[indexes["un"]] if "un" in indexes and indexes["un"] < len(cells) else "PC"
                        if not codigo or not descricao or quantidade <= 0:
                            continue

                        unit_value = _parse_decimal(unitario)
                        total_value = _parse_decimal(valor_total)
                        discount_value = _parse_decimal(desconto)
                        if total_value is None and unit_value is not None:
                            total_value = unit_value * Decimal(quantidade)
                        if discount_value is not None and unit_value is not None:
                            gross_total = total_value if total_value is not None else unit_value * Decimal(quantidade)
                            net_total = gross_total - discount_value
                            unit_value = net_total / Decimal(quantidade)
                            total_value = net_total
                        if unit_value is None:
                            unit_value = _parse_decimal(valor_total)
                        if unit_value is None:
                            continue

                        rows.append(
                            ParsedInvoiceRow(
                                codigo=codigo,
                                nome=_clean_name(descricao),
                                descricao_completa=descricao,
                                cor=_extract_color(descricao),
                                tamanho=_extract_size(descricao),
                                quantidade=quantidade,
                                preco=_format_price(unit_value),
                                unidade=(unidade or "PC").strip(),
                                valor_total=_format_price(total_value) if total_value is not None else None,
                                desconto_total=_format_price(discount_value) if discount_value is not None else None,
                            )
                        )
    except Exception:
        return rows
    return rows


def _clean_name(description: str) -> str:
    value = str(description or "").strip()
    value = _COLOR_REGEX.sub("", value)
    value = _SIZE_REGEX.sub("", value)
    value = re.sub(r"\b\d{13}-\d{2}\b", "", value)
    value = re.sub(r"\b\d{8}\b", "", value)
    value = value.replace("EMBULTIDO", "EMBUTIDO")
    value = value.replace("CINERVURAS", "C/NERVURAS")
    value = value.replace("C,'NERVURAS", "C/NERVURAS")
    value = re.sub(r"\s+", " ", value).strip(" -_/")
    return value


def _extract_money_values(line: str) -> list[Decimal]:
    values: list[Decimal] = []
    for token in _MONEY_CAPTURE_REGEX.findall(str(line or "")):
        parsed = _parse_decimal(token)
        if parsed is not None:
            values.append(parsed)
    return values


def _extract_cativa_color_and_size(codigo: str) -> tuple[str | None, str | None]:
    match = re.match(r"^[A-Z]\d{5}-(?P<cor>[A-Z0-9]{4})-(?P<tamanho>[A-Z0-9]{1,3})$", str(codigo or "").strip().upper())
    if not match:
        return None, None
    return str(match.group("cor") or "").strip().upper() or None, _normalize_size(match.group("tamanho"))


def _extract_size(description: str) -> str | None:
    match = _SIZE_REGEX.search(str(description or ""))
    if not match:
        return None
    return _normalize_size(match.group("size"))


def _extract_color(description: str) -> str | None:
    match = _COLOR_REGEX.search(str(description or ""))
    if not match:
        return None
    color = str(match.group("color") or "").strip().upper()
    return color or None


def _extract_remessa_quantity(text: str) -> int | None:
    raw = str(text or "")
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    match = _REMESSA_REGEX.search(normalized)
    if not match:
        return None
    try:
        return int(match.group("qty"))
    except Exception:
        return None


def _extract_document_money(pattern: re.Pattern[str], text: str) -> Decimal | None:
    raw = str(text or "")
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    match = pattern.search(normalized)
    if not match:
        return None
    return _parse_decimal(match.group("value"))


def _score_concatenated_split(parts: list[str]) -> Decimal:
    decimals = [_parse_decimal(item) for item in parts]
    if any(value is None for value in decimals):
        return Decimal("-999999")
    qty, unit, total, bc_icms, valor_icms, aliq_icms = decimals  # type: ignore[misc]
    score = Decimal("0")
    score -= abs((qty or Decimal("0")) * (unit or Decimal("0")) - (total or Decimal("0")))
    score -= abs((bc_icms or Decimal("0")) - (total or Decimal("0")))
    if bc_icms is not None and aliq_icms is not None:
        score -= abs((bc_icms * aliq_icms / Decimal("100")) - (valor_icms or Decimal("0")))
    return score


def _split_concatenated_tail(raw_tail: str) -> list[str] | None:
    source = str(raw_tail or "").strip()
    if not source:
        return None
    candidates: list[list[str]] = []

    def walk(position: int, index: int, parts: list[str]) -> None:
        if index == 6:
            if position == len(source):
                candidates.append(parts[:])
            return
        if position >= len(source):
            return

        decimal_options = (2, 3) if index == 0 else ((2, 4) if index == 1 else (2,))
        for before_digits in range(1, 7):
            for decimals in decimal_options:
                end = position + before_digits + 1 + decimals
                if end > len(source):
                    continue
                piece = source[position:end]
                if len(piece) < before_digits + decimals + 1:
                    continue
                if piece[before_digits] != ",":
                    continue
                walk(end, index + 1, parts + [piece])

    walk(0, 0, [])
    if not candidates:
        return None
    return max(candidates, key=_score_concatenated_split)


def _parse_classic_invoice_rows(text: str) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    for raw_line in text.splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue

        spaced = _INVOICE_LINE_REGEX.match(line)
        if spaced:
            descricao = str(spaced.group("descricao") or "").strip()
            quantidade = _parse_quantity(str(spaced.group("quantidade") or ""))
            if quantidade <= 0:
                continue
            rows.append(
                ParsedInvoiceRow(
                    codigo=str(spaced.group("codigo") or "").strip(),
                    nome=_clean_name(descricao),
                    descricao_completa=descricao,
                    cor=_extract_color(descricao),
                    tamanho=_extract_size(descricao),
                    quantidade=quantidade,
                    preco=_format_price(str(spaced.group("unitario") or "")),
                    unidade=str(spaced.group("un") or "").strip(),
                    valor_total=_format_price(str(spaced.group("valor_total") or "")),
                )
            )
            continue

        compact = _CONCAT_PREFIX_REGEX.match(line)
        if not compact:
            continue
        split = _split_concatenated_tail(str(compact.group("tail") or ""))
        if not split:
            continue
        quantidade_raw, unitario_raw, valor_total_raw, _, _, _ = split
        quantidade = _parse_quantity(quantidade_raw)
        if quantidade <= 0:
            continue
        descricao = str(compact.group("descricao") or "").strip()
        rows.append(
            ParsedInvoiceRow(
                codigo=str(compact.group("codigo") or "").strip(),
                nome=_clean_name(descricao),
                descricao_completa=descricao,
                cor=_extract_color(descricao),
                tamanho=_extract_size(descricao),
                quantidade=quantidade,
                preco=_format_price(unitario_raw),
                unidade=str(compact.group("un") or "").strip(),
                valor_total=_format_price(valor_total_raw),
            )
        )
    return rows


def _parse_cativa_rows(text: str) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    for raw_line in text.splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        start = re.search(r"[A-Z]\d{5}-[A-Z0-9]{4}-[A-Z0-9]{1,3}\s+", line)
        if start:
            line = line[start.start():]
        match = _CATIVE_ROW_REGEX.match(line)
        if not match:
            continue
        quantidade = _parse_quantity(match.group("quantidade"))
        if quantidade <= 0:
            continue
        codigo = str(match.group("codigo") or "").strip().upper()
        descricao = str(match.group("descricao") or "").strip()
        cor, tamanho = _extract_cativa_color_and_size(codigo)
        rows.append(
            ParsedInvoiceRow(
                codigo=codigo,
                nome=_clean_name(descricao) or descricao,
                descricao_completa=descricao,
                cor=cor,
                tamanho=tamanho or _extract_size(descricao),
                quantidade=quantidade,
                preco=_format_price(match.group("unitario")),
                unidade=str(match.group("un") or "").strip(),
                valor_total=_format_price(match.group("valor_total")),
            )
        )
    return rows


def _parse_auriflama_rows(text: str) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    pending_index: int | None = None
    for raw_line in text.splitlines():
        line = str(raw_line or "").rstrip()
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("page "):
            continue
        if "totais" in stripped.lower():
            break
        if "romaneio de faturamento" in stripped.lower() or "produto" in stripped.lower() or set(stripped) == {"-"}:
            continue

        full_match = _AURIFLAMA_ROW_WITH_DESC_REGEX.match(line)
        simple_match = _AURIFLAMA_ROW_SIMPLE_REGEX.match(line)
        if full_match or simple_match:
            match = full_match or simple_match
            assert match is not None
            descricao = str(match.groupdict().get("descricao") or "").strip() or str(match.group("codigo") or "").strip()
            rows.append(
                ParsedInvoiceRow(
                    codigo=str(match.group("codigo") or "").strip(),
                    nome=_clean_name(descricao) or descricao,
                    descricao_completa=descricao,
                    cor=None,
                    tamanho=None,
                    quantidade=_parse_quantity(match.group("quantidade")),
                    preco=_format_price(match.group("unitario")),
                    unidade="PC",
                    valor_total=_format_price(match.group("valor_total")),
                )
            )
            pending_index = len(rows) - 1
            continue

        if pending_index is None:
            continue
        if any(char.isdigit() for char in stripped) or len(stripped) > 80:
            continue
        previous = rows[pending_index]
        previous.descricao_completa = f"{previous.descricao_completa} {stripped}".strip()
        previous.nome = _clean_name(previous.descricao_completa) or previous.descricao_completa
    return [row for row in rows if row.quantidade > 0]


def _parse_sisplan_rows(text: str) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    current_codigo: str | None = None
    current_descricao: str | None = None
    for raw_line in text.splitlines():
        line = str(raw_line or "").rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        header_match = _SISPLAN_PRODUCT_HEADER_REGEX.match(stripped)
        if header_match:
            current_codigo = str(header_match.group("codigo") or "").strip()
            current_descricao = str(header_match.group("descricao") or "").strip()
            continue
        if current_codigo is None or current_descricao is None:
            continue
        if stripped.lower().startswith("preço valor") or stripped.lower().startswith("sisplan sistemas"):
            continue
        if stripped.lower().startswith("total "):
            break
        row_match = _SISPLAN_ROW_REGEX.match(stripped)
        if not row_match:
            continue
        quantidade = _parse_quantity(row_match.group("quantidade"))
        if quantidade <= 0:
            continue
        tamanho = _normalize_size(row_match.group("tamanho"))
        rows.append(
            ParsedInvoiceRow(
                codigo=current_codigo,
                nome=_clean_name(current_descricao) or current_descricao,
                descricao_completa=current_descricao,
                cor=None,
                tamanho=tamanho,
                quantidade=quantidade,
                preco=_format_price(row_match.group("unitario")),
                unidade="PC",
                valor_total=_format_price(row_match.group("valor_total")),
            )
        )
    return rows


def _parse_legacy_danfe_rows(text: str) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    description_parts: list[str] = []
    for raw_line in text.splitlines():
        line = str(raw_line or "").rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        match = _LEGACY_DANFE_NUMERIC_ROW_REGEX.match(stripped)
        if match:
            descricao = _clean_ocr_description(description_parts) or " ".join(description_parts).strip()
            if descricao:
                rows.append(
                    ParsedInvoiceRow(
                        codigo=str(match.group("codigo") or "").strip(),
                        nome=_clean_name(descricao) or descricao,
                        descricao_completa=descricao,
                        cor=_extract_color(descricao),
                        tamanho=_extract_size(descricao),
                        quantidade=_parse_quantity(match.group("quantidade")),
                        preco=_format_price(match.group("unitario")),
                        unidade=str(match.group("un") or "").strip(),
                        valor_total=_format_price(match.group("valor_total")),
                    )
                )
            description_parts = []
            continue

        lowered = unicodedata.normalize("NFKD", stripped).encode("ascii", "ignore").decode("ascii").lower()
        if (
            _is_header_noise(stripped)
            or lowered.startswith(("folha:", "numero data", "valor total", "impostos", "dados do produto", "consulta de autenticidade"))
            or set(stripped) == {"-"}
        ):
            continue
        if any(char.isalpha() for char in stripped):
            description_parts.append(stripped)
            if len(description_parts) > 4:
                description_parts = description_parts[-4:]
    return [row for row in rows if row.quantidade > 0]


def _parse_structured_text_rows(text: str) -> list[ParsedInvoiceRow]:
    normalized = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    candidates: list[list[ParsedInvoiceRow]] = [_parse_classic_invoice_rows(text)]
    if "cativa.portaldocliente.online" in normalized or "cativa textil" in normalized:
        candidates.append(_parse_cativa_rows(text))
    if "romaneio de faturamento" in normalized and "auriflama" in normalized:
        candidates.append(_parse_auriflama_rows(text))
    if "pedido de venda" in normalized and "sisplan" in normalized:
        candidates.append(_parse_sisplan_rows(text))
    if "confeccoes saullu" in normalized or "dados do produto/servico" in normalized:
        candidates.append(_parse_legacy_danfe_rows(text))
    return max(candidates, key=len, default=[])


def _normalize_ocr_code(value: str) -> str:
    raw = _normalize_ocr_text(value).upper()
    if not raw:
        return ""
    replacements = str.maketrans({"O": "0", "I": "1", "L": "1"})
    parts = raw.split()
    candidates = [
        raw,
        re.sub(r"\s+", "", raw),
        raw.replace(" ", "."),
        raw.translate(replacements),
        re.sub(r"\s+", "", raw).translate(replacements),
        raw.replace(" ", ".").translate(replacements),
    ]
    if parts:
        head = parts[0]
        candidates.extend([head, head.translate(replacements)])
    if len(parts) >= 2:
        joined = "".join(parts[:2])
        dotted = ".".join(parts[:2])
        candidates.extend([joined, dotted, joined.translate(replacements), dotted.translate(replacements)])
    for candidate in candidates:
        cleaned = re.sub(r"\s+", "", candidate) if candidate.count(" ") <= 1 else candidate
        for pattern in _OCR_CODE_REGEXES:
            if pattern.fullmatch(cleaned) or pattern.fullmatch(candidate):
                return cleaned
    return ""


def _looks_like_ocr_code(value: str) -> bool:
    return bool(_normalize_ocr_code(value))


def _is_header_noise(text: str) -> bool:
    lowered = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    return any(
        token in lowered
        for token in (
            "dados do produto",
            "dados dos produtos",
            "descricao",
            "quant",
            "valor",
            "aliquota",
            "ncm",
            "cfop",
            "unid",
            "codigo",
            "cod.",
            "prod.",
        )
    )


def _normalize_ocr_text(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_ocr_description(parts: list[str]) -> str:
    cleaned: list[str] = []
    for part in parts:
        text = _normalize_ocr_text(part)
        if not text:
            continue
        if re.fullmatch(r"\d{1,2}", text):
            continue
        cleaned.append(text)
    description = " ".join(cleaned)
    description = re.sub(r"\b\d{13}-\d{2}\b", "", description)
    description = re.sub(r"\b\d{8}\b", "", description)
    description = re.sub(r"\s+", " ", description).strip(" -_/")
    return description


def _nearest_numeric_value(
    row_lines: list[dict[str, Any]],
    *,
    center_x: int | None,
    tolerance: int = 140,
) -> str | None:
    if center_x is None:
        return None
    candidates: list[tuple[int, str]] = []
    for line in row_lines:
        text = _normalize_ocr_text(line.get("text") or "")
        if not _OCR_NUMBER_REGEX.fullmatch(text.replace(" ", "")):
            continue
        distance = abs(int(line.get("x") or 0) - center_x)
        if distance <= tolerance:
            candidates.append((distance, text))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _cluster_numeric_columns(lines: list[dict[str, Any]], *, min_y: int) -> list[int]:
    positions = sorted(
        int(line.get("x") or 0)
        for line in lines
        if int(line.get("y") or 0) >= min_y and _OCR_NUMBER_REGEX.fullmatch(_normalize_ocr_text(line.get("text") or "").replace(" ", ""))
    )
    if not positions:
        return []
    clusters: list[list[int]] = [[positions[0]]]
    for position in positions[1:]:
        if abs(position - clusters[-1][-1]) <= 90:
            clusters[-1].append(position)
        else:
            clusters.append([position])
    return [int(round(sum(cluster) / len(cluster))) for cluster in clusters]


def _header_x(lines: list[dict[str, Any]], *needles: str, min_y: int | None = None) -> int | None:
    candidates: list[tuple[int, int]] = []
    for line in lines:
        y = int(line.get("y") or 0)
        if min_y is not None and y < min_y:
            continue
        text = unicodedata.normalize("NFKD", str(line.get("text") or "")).encode("ascii", "ignore").decode("ascii").lower()
        if all(needle in text for needle in needles):
            candidates.append((y, int(line.get("x") or 0)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _parse_ocr_page_rows(page: OcrPagePayload) -> list[ParsedInvoiceRow]:
    lines = sorted(page.lines, key=lambda item: (int(item.get("y") or 0), int(item.get("x") or 0)))
    if not lines:
        return []

    table_header_y = max(
        [
            int(line.get("y") or 0)
            for line in lines
            if _is_header_noise(line.get("text") or "")
        ],
        default=0,
    )
    header_min_y = max(table_header_y - 80, 0)
    desc_x = _header_x(lines, "descr", min_y=header_min_y)
    ncm_x = _header_x(lines, "ncm", min_y=header_min_y)
    quant_x = _header_x(lines, "quant", min_y=header_min_y)
    unit_x = _header_x(lines, "unit", min_y=header_min_y)
    total_x = _header_x(lines, "total", min_y=header_min_y)
    discount_x = _header_x(lines, "desconto", min_y=header_min_y)
    numeric_columns = _cluster_numeric_columns(lines, min_y=table_header_y + 20)
    if total_x is None and unit_x is not None and (discount_x is None or abs(discount_x - unit_x) <= 80):
        later_columns = [column for column in numeric_columns if column > unit_x + 90]
        if later_columns:
            discount_x = later_columns[0]

    code_lines = [
        {
            "text": _normalize_ocr_code(line.get("text") or ""),
            "x": int(line.get("x") or 0),
            "y": int(line.get("y") or 0),
        }
        for line in lines
        if _looks_like_ocr_code(line.get("text") or "")
        and int(line.get("x") or 0) <= max(int(page.width * 0.16), 260)
        and int(line.get("y") or 0) > table_header_y + 20
    ]
    if not code_lines:
        return []

    code_lines.sort(key=lambda item: item["y"])
    deduped_codes: list[dict[str, int | str]] = []
    for line in code_lines:
        if deduped_codes and abs(int(deduped_codes[-1]["y"]) - line["y"]) <= 6 and str(deduped_codes[-1]["text"]) == line["text"]:
            continue
        deduped_codes.append(line)

    rows: list[ParsedInvoiceRow] = []
    for index, code_line in enumerate(deduped_codes):
        current_y = int(code_line["y"])
        next_y = int(deduped_codes[index + 1]["y"]) if index + 1 < len(deduped_codes) else current_y + max(int(page.height * 0.08), 120)
        row_lines = [
            {
                "text": _normalize_ocr_text(line.get("text") or ""),
                "x": int(line.get("x") or 0),
                "y": int(line.get("y") or 0),
            }
            for line in lines
            if current_y - 8 <= int(line.get("y") or 0) < next_y - 8
        ]
        if not row_lines:
            continue

        description_parts = [
            line["text"]
            for line in row_lines
            if not _is_header_noise(line["text"])
            and int(line["x"]) > int(code_line["x"]) + 80
            and int(line["x"]) < min(value for value in (ncm_x, quant_x, unit_x, total_x, discount_x, page.width) if value is not None) - 40
        ]
        description = _clean_ocr_description(description_parts)
        if not description:
            continue

        quantity_text = _nearest_numeric_value(row_lines, center_x=quant_x, tolerance=150)
        unit_text = _nearest_numeric_value(row_lines, center_x=unit_x, tolerance=180)
        total_text = _nearest_numeric_value(row_lines, center_x=total_x, tolerance=180)
        discount_text = _nearest_numeric_value(row_lines, center_x=discount_x, tolerance=180)

        quantity = _parse_quantity(quantity_text or "1")
        if quantity <= 0:
            quantity = 1

        unit_value = _parse_decimal(unit_text)
        total_value = _parse_decimal(total_text)
        discount_value = _parse_decimal(discount_text)
        if total_value is None and unit_value is not None:
            total_value = unit_value * Decimal(quantity)
        if discount_value is not None and unit_value is not None:
            gross_total = total_value if total_value is not None and total_x is not None else unit_value * Decimal(quantity)
            net_total = gross_total - discount_value
            unit_value = net_total / Decimal(quantity)
            total_value = net_total
        if unit_value is not None and quantity > 0:
            expected_total = unit_value * Decimal(quantity)
            if total_value is None or abs(total_value - expected_total) > Decimal("0.10"):
                total_value = expected_total

        if unit_value is None:
            continue

        rows.append(
            ParsedInvoiceRow(
                codigo=str(code_line["text"]),
                nome=_clean_name(description) or description,
                descricao_completa=description,
                cor=_extract_color(description),
                tamanho=_extract_size(description),
                quantidade=quantity,
                preco=_format_price(unit_value),
                unidade="PC",
                valor_total=_format_price(total_value) if total_value is not None else None,
                desconto_total=_format_price(discount_value) if discount_value is not None else None,
            )
        )
    return rows


def _run_windows_ocr(image_paths: list[Path]) -> list[OcrPagePayload]:
    if not image_paths:
        return []
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as script_file:
        script_file.write(_OCR_PS_SCRIPT)
        script_path = Path(script_file.name)
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                json.dumps([str(path) for path in image_paths], ensure_ascii=True),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except Exception:
            pass

    raw_stdout = completed.stdout or b""
    if isinstance(raw_stdout, bytes):
        stdout_text = raw_stdout.decode("utf-8", errors="replace")
    else:
        stdout_text = str(raw_stdout)
    output = stdout_text.strip()
    if not output:
        return []
    payload = json.loads(output)
    if isinstance(payload, dict):
        payload = [payload]

    pages: list[OcrPagePayload] = []
    for item in payload or []:
        if not isinstance(item, dict):
            continue
        lines = item.get("lines") if isinstance(item.get("lines"), list) else []
        pages.append(
            OcrPagePayload(
                width=int(item.get("width") or 0),
                height=int(item.get("height") or 0),
                text=str(item.get("text") or ""),
                lines=[line for line in lines if isinstance(line, dict)],
            )
        )
    return pages


def _ocr_pdf_pages(contents: bytes) -> tuple[list[OcrPagePayload], int]:
    try:
        import fitz  # type: ignore
    except Exception:
        return [], 0

    with tempfile.TemporaryDirectory() as temp_dir:
        image_paths: list[Path] = []
        document = fitz.open(stream=contents, filetype="pdf")
        for index, page in enumerate(document):
            output = Path(temp_dir) / f"page_{index}.png"
            rect = page.rect
            clip = fitz.Rect(rect.width * 0.02, rect.height * 0.12, rect.width * 0.98, rect.height * 0.94)
            page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False).save(str(output))
            image_paths.append(output)
        return _run_windows_ocr(image_paths), len(image_paths)


def _ocr_image_bytes(contents: bytes, suffix: str) -> list[OcrPagePayload]:
    try:
        from PIL import Image
    except Exception:
        return []

    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / f"source{suffix}"
        source_path.write_bytes(contents)
        image = Image.open(source_path)
        if min(image.size) < 1400:
            image = image.resize((image.width * 2, image.height * 2))

        def run_crop(top_ratio: float) -> list[OcrPagePayload]:
            crop = image.crop((int(image.width * 0.03), int(image.height * top_ratio), int(image.width * 0.99), int(image.height * 0.92)))
            output = Path(temp_dir) / f"ocr_input_{int(top_ratio * 100)}.png"
            crop.save(output)
            return _run_windows_ocr([output])

        receipt_payload = run_crop(0.12)
        receipt_text = "\n".join(page.text for page in receipt_payload)
        receipt_text_ascii = unicodedata.normalize("NFKD", receipt_text).encode("ascii", "ignore").decode("ascii").lower()
        if any(token in receipt_text_ascii for token in ("subtotal", "pecas", "desc (")):
            return receipt_payload
        return run_crop(0.22)


def _extract_text(contents: bytes, filename: str, content_type: str | None) -> tuple[str, int, list[OcrPagePayload]]:
    lower_name = (filename or "").lower()
    lower_type = (content_type or "").lower()
    if lower_name.endswith(".pdf") or "pdf" in lower_type:
        text, page_count = _extract_pdf_text(contents)
        if text.strip():
            return text, page_count, []
        ocr_pages, ocr_page_count = _ocr_pdf_pages(contents)
        return "\n\n".join(page.text for page in ocr_pages if page.text.strip()), ocr_page_count or page_count, ocr_pages

    if lower_name.endswith((".jpg", ".jpeg", ".png")) or any(token in lower_type for token in ("image/jpeg", "image/png")):
        ocr_pages = _ocr_image_bytes(contents, Path(filename or "image").suffix or ".png")
        return "\n\n".join(page.text for page in ocr_pages if page.text.strip()), max(len(ocr_pages), 1), ocr_pages

    for encoding in ("utf-8", "latin-1"):
        try:
            return contents.decode(encoding), 1, []
        except Exception:
            continue
    return "", 1, []


def _rows_from_ocr_pages(ocr_pages: list[OcrPagePayload]) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    for page in ocr_pages:
        rows.extend(_parse_ocr_page_rows(page))
    return rows


def _parse_simple_receipt_rows(page: OcrPagePayload) -> list[ParsedInvoiceRow]:
    lines = [
        {
            "text": _normalize_ocr_text(line.get("text") or ""),
            "x": int(line.get("x") or 0),
            "y": int(line.get("y") or 0),
        }
        for line in sorted(page.lines, key=lambda item: (int(item.get("y") or 0), int(item.get("x") or 0)))
    ]
    subtotal_y = min(
        [
            line["y"]
            for line in lines
            if "subtotal" in unicodedata.normalize("NFKD", line["text"]).encode("ascii", "ignore").decode("ascii").lower()
        ],
        default=page.height,
    )
    code_lines = [
        line
        for line in lines
        if 250 <= line["x"] <= 520 and line["y"] < subtotal_y and re.fullmatch(r"\d{4,6}", line["text"])
    ]
    if not code_lines:
        return []

    rows: list[ParsedInvoiceRow] = []
    for code_line in code_lines:
        current_y = code_line["y"]
        row_lines = [line for line in lines if abs(line["y"] - current_y) <= 30]
        qty_line = next((line for line in row_lines if line["x"] < code_line["x"] and re.fullmatch(r"\d{1,3}", line["text"])), None)
        desc_line = next((line for line in row_lines if 520 <= line["x"] <= 780 and any(char.isalpha() for char in line["text"])), None)
        value_line = next((line for line in row_lines if 780 <= line["x"] <= 940 and _OCR_NUMBER_REGEX.fullmatch(line["text"])), None)
        total_line = next((line for line in row_lines if line["x"] >= 960 and _OCR_NUMBER_REGEX.fullmatch(line["text"].replace(" ", ""))), None)
        if desc_line is None or (value_line is None and total_line is None):
            continue
        quantity = int(qty_line["text"]) if qty_line else 1
        unit_value = _parse_decimal(value_line["text"]) if value_line is not None else None
        total_value = _parse_decimal(total_line["text"]) if total_line else None
        if unit_value is None and total_value is not None and quantity > 0:
            unit_value = total_value / Decimal(quantity)
        if unit_value is None:
            continue
        if total_value is not None and quantity > 0:
            unit_value = total_value / Decimal(quantity)
        rows.append(
            ParsedInvoiceRow(
                codigo=code_line["text"],
                nome=_clean_name(desc_line["text"]) or desc_line["text"],
                descricao_completa=desc_line["text"],
                cor=None,
                tamanho=None,
                quantidade=max(quantity, 1),
                preco=_format_price(unit_value),
                unidade="PC",
                valor_total=_format_price(total_value) if total_value is not None else _format_price(unit_value * Decimal(max(quantity, 1))),
            )
        )
    return rows


def _rows_from_simple_receipts(ocr_pages: list[OcrPagePayload]) -> list[ParsedInvoiceRow]:
    rows: list[ParsedInvoiceRow] = []
    for page in ocr_pages:
        rows.extend(_parse_simple_receipt_rows(page))
    return rows


def _extract_special_remessa_quantity(text: str) -> int | None:
    normalized = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    for pattern in (
        re.compile(r"(?i)\bpecas:\s*(?P<qty>\d+)\b"),
        re.compile(r"(?i)\btotais\s+(?P<qty>\d+)\s+\d"),
        re.compile(r"(?is)total\s+de\s+pecas:.*?r\$\s*\d+(?:\.\d{3})*,\d{2}\s*(?P<qty>\d{1,4})\b"),
    ):
        match = pattern.search(normalized)
        if match:
            try:
                return int(match.group("qty"))
            except Exception:
                continue
    return None


def _extract_special_document_totals(text: str) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    raw = str(text or "")
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    lowered = normalized.lower()

    auriflama_match = re.search(r"(?im)totais\s+(?P<qty>\d+)\s+(?P<value>\d{1,3}(?:,\d{3})*\.\d{2})", normalized)
    if auriflama_match:
        total = _parse_decimal(auriflama_match.group("value"))
        return total, total, None

    if "pedido de venda" in lowered and "sisplan" in lowered:
        values = [_parse_decimal(match) for match in re.findall(r"R\$\s*(\d+(?:\.\d{3})*,\d{2})", normalized)]
        values = [value for value in values if value is not None]
        if values:
            values.sort()
            discount = values[0] if len(values) >= 3 else None
            gross = values[-1]
            net = values[-2] if len(values) >= 2 else gross
            return gross, net, discount

    money_lines = [
        [value for value in values if value <= Decimal("99999.99")]
        for values in (_extract_money_values(line) for line in normalized.splitlines())
        if len(values) >= 5
    ]
    if money_lines:
        flattened = [value for values in money_lines for value in values]
        if flattened:
            inferred = max(flattened)
            return inferred, None, None

    return None, None, None


def parse_local_romaneio_experiment(
    *,
    contents: bytes,
    filename: str,
    content_type: str | None,
) -> dict[str, Any]:
    text, page_count, ocr_pages = _extract_text(contents, filename, content_type)
    remessa_quantity = _extract_remessa_quantity(text)
    document_total_products = _extract_document_money(_TOTAL_PRODUCTS_REGEX, text)
    document_total_note = _extract_document_money(_TOTAL_NOTE_REGEX, text)
    document_discount_total = _extract_document_money(_TOTAL_DISCOUNT_REGEX, text)
    warnings: list[str] = []

    lower_name = (filename or "").lower()
    lower_type = (content_type or "").lower()
    table_rows = _parse_pdf_table_rows(contents) if lower_name.endswith(".pdf") or "pdf" in lower_type else []
    rows = table_rows or _parse_structured_text_rows(text)
    if not rows and ocr_pages:
        rows = _rows_from_ocr_pages(ocr_pages)
    if not rows and ocr_pages:
        rows = _rows_from_simple_receipts(ocr_pages)

    if remessa_quantity is None:
        remessa_quantity = _extract_special_remessa_quantity(text)
    if document_total_products is None or document_total_note is None:
        fallback_products, fallback_note, fallback_discount = _extract_special_document_totals(text)
        if document_total_products is None:
            document_total_products = fallback_products
        if document_total_note is None:
            document_total_note = fallback_note
        if document_discount_total is None:
            document_discount_total = fallback_discount

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str, str]] = []
    for row in rows:
        key = (
            row.codigo,
            row.nome,
            row.cor or "",
            row.preco,
        )
        if key not in grouped:
            grouped[key] = {
                "codigo": row.codigo,
                "nome": row.nome,
                "descricao_completa": row.descricao_completa,
                "cor": row.cor,
                "preco": row.preco,
                "quantidade": 0,
                "unidade": row.unidade,
                "grades": {},
                "linhas_originais": 0,
                "valor_total": Decimal("0"),
                "desconto_total": Decimal("0"),
            }
            ordered_keys.append(key)
        entry = grouped[key]
        entry["quantidade"] = int(entry["quantidade"] or 0) + row.quantidade
        entry["linhas_originais"] = int(entry["linhas_originais"] or 0) + 1
        if len(row.descricao_completa) > len(str(entry.get("descricao_completa") or "")):
            entry["descricao_completa"] = row.descricao_completa
        if row.tamanho:
            grades = entry["grades"]
            assert isinstance(grades, dict)
            grades[row.tamanho] = int(grades.get(row.tamanho, 0) or 0) + row.quantidade
        if row.valor_total:
            entry["valor_total"] = Decimal(entry["valor_total"]) + (_parse_decimal(row.valor_total) or Decimal("0"))
        if row.desconto_total:
            entry["desconto_total"] = Decimal(entry["desconto_total"]) + (_parse_decimal(row.desconto_total) or Decimal("0"))

    items: list[dict[str, Any]] = []
    for key in ordered_keys:
        entry = grouped[key]
        grades = entry.get("grades") or {}
        grade_items = [
            {"tamanho": size, "quantidade": int(qty)}
            for size, qty in sorted(grades.items(), key=lambda item: _size_sort_key(item[0]))
            if int(qty or 0) > 0
        ]
        items.append(
            {
                "codigo": entry["codigo"],
                "nome": entry["nome"],
                "descricao_completa": entry["descricao_completa"],
                "cor": entry["cor"],
                "preco": entry["preco"],
                "quantidade": int(entry["quantidade"] or 0),
                "unidade": entry["unidade"],
                "grades": grade_items,
                "linhas_originais": int(entry["linhas_originais"] or 0),
                "valor_total": _format_price(entry["valor_total"]) if entry["valor_total"] else _format_price((_parse_decimal(entry["preco"]) or Decimal("0")) * int(entry["quantidade"] or 0)),
                "desconto_total": _format_price(entry["desconto_total"]) if entry["desconto_total"] else None,
            }
        )

    total_quantity = sum(int(item["quantidade"]) for item in items)
    extracted_total_products = sum((_parse_decimal(str(item.get("valor_total") or "")) or Decimal("0")) for item in items)
    extracted_discount_total = sum((_parse_decimal(str(item.get("desconto_total") or "")) or Decimal("0")) for item in items)

    if (
        document_discount_total is not None
        and extracted_discount_total
        and document_discount_total < (extracted_discount_total * Decimal("0.25"))
    ):
        document_discount_total = None

    quantity_matches_remessa = remessa_quantity is not None and total_quantity == remessa_quantity
    products_value_matches = (
        (document_total_products is not None and abs(extracted_total_products - document_total_products) <= Decimal("0.05"))
        or (document_total_note is not None and abs(extracted_total_products - document_total_note) <= Decimal("0.05"))
    )
    discount_matches = document_discount_total is not None and abs(extracted_discount_total - document_discount_total) <= Decimal("0.05")

    if remessa_quantity is not None and not quantity_matches_remessa:
        warnings.append(
            f"Extracted quantity ({total_quantity}) does not match the remessa quantity printed in the document ({remessa_quantity})."
        )

    if document_total_products is not None and not products_value_matches:
        warnings.append(
            "Extracted product total does not match the printed 'Valor total dos produtos' in the document."
        )

    if document_discount_total is not None and extracted_discount_total and not discount_matches:
        warnings.append("Extracted discount total does not match the printed discount value in the document.")

    if not rows:
        warnings.append("No structured invoice rows were detected by the isolated local parser.")

    return {
        "status": "ok" if rows else "partial",
        "filename": filename or "romaneio",
        "warnings": warnings,
        "total_rows": len(rows),
        "total_itens": len(items),
        "total_quantity": total_quantity,
        "remessa_quantity": remessa_quantity,
        "quantity_matches_remessa": quantity_matches_remessa,
        "document_total_products": _format_price(document_total_products) if document_total_products is not None else None,
        "document_total_note": _format_price(document_total_note) if document_total_note is not None else None,
        "document_discount_total": _format_price(document_discount_total) if document_discount_total is not None else None,
        "extracted_total_products": _format_price(extracted_total_products),
        "extracted_discount_total": _format_price(extracted_discount_total) if extracted_discount_total else None,
        "products_value_matches_document": products_value_matches,
        "discount_matches_document": discount_matches if document_discount_total is not None else None,
        "items": items,
        "metrics": {
            "page_count": page_count,
            "text_chars": len(text),
            "matched_invoice_rows": len(rows),
            "grouped_items": len(items),
            "colors_detected": len({str(item.get("cor") or "").strip() for item in items if str(item.get("cor") or "").strip()}),
            "items_with_grades": sum(1 for item in items if item.get("grades")),
            "ocr_pages_used": len(ocr_pages),
            "extraction_mode": "isolated_local_parser",
        },
    }


__all__ = ["parse_local_romaneio_experiment"]
