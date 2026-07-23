"""Deterministic parser for vertical DANFE text extracted by PyMuPDF.

Many digital DANFEs extract as one field per line:
  codigo
  tamanho
  DESCRICAO...
  ncm
  cst
  cfop
  UN
  quant
  unitario
  valor_total
  ...

This recovers product rows without LLM when the layout matches.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.domain.products.entities import Product
from app.domain.products.money import normalize_decimal_price, parse_price_decimal

_CODE_RE = re.compile(r"^\d{8,14}$")
_NCM_RE = re.compile(r"^\d{8}$|^\d{4}\.\d{2}\.\d{2}$")
# Only real unit tokens — do NOT treat product tokens like OGPT/ESSE as UN.
_UN_RE = re.compile(r"^(PC|UN|UND|KG|CX|MT|M|PAR|PÇ|PC\$|KIT|CJ)$", re.I)
_QTY_RE = re.compile(r"^\d{1,5},\d{2}$")  # 1,00 / 12,00
_MONEY_RE = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")
_SIZE_RE = re.compile(r"^[0-9A-Za-z]{1,8}$")
_ALPHA_RE = re.compile(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]{2,}")


def _parse_qty(raw: str) -> int:
    value = parse_price_decimal(raw)
    if value is None:
        return 0
    # 1,00 -> 1; keep positive integers only for catalog qty.
    as_int = int(value)
    if value == Decimal(as_int) and as_int > 0:
        return as_int
    # rare fractional qty: round if close
    if value > 0:
        return max(1, int(value.to_integral_value(rounding="ROUND_HALF_UP")))
    return 0


def parse_vertical_danfe_items(text: str) -> list[dict[str, Any]]:
    lines = [str(line or "").strip() for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    items: list[dict[str, Any]] = []
    i = 0
    n = len(lines)
    while i < n - 7:
        if not _CODE_RE.fullmatch(lines[i]):
            i += 1
            continue
        codigo = lines[i]
        k = i + 1
        tamanho = ""
        # optional size token before description
        if (
            k < n
            and _SIZE_RE.fullmatch(lines[k])
            and not _NCM_RE.fullmatch(lines[k])
            and not _CODE_RE.fullmatch(lines[k])
            and k + 1 < n
            and _ALPHA_RE.search(lines[k + 1])
            and (re.search(r"[A-Za-z]", lines[k]) or (lines[k].isdigit() and 2 <= len(lines[k]) <= 4))
        ):
            tamanho = lines[k]
            k += 1
        desc_parts: list[str] = []
        while k < n and _ALPHA_RE.search(lines[k]) and not _NCM_RE.fullmatch(lines[k]) and not _UN_RE.fullmatch(lines[k]):
            # stop if this looks like a new product code line mishit
            if _CODE_RE.fullmatch(lines[k]):
                break
            desc_parts.append(lines[k])
            k += 1
            if len(desc_parts) >= 4:
                break
        if not desc_parts or k >= n or not _NCM_RE.fullmatch(lines[k]):
            i += 1
            continue
        ncm = lines[k].replace(".", "")
        k += 1
        if k + 1 >= n:
            i += 1
            continue
        # cst + cfop (usually 3 and 4 digits)
        cst = lines[k]
        cfop = lines[k + 1]
        if not re.fullmatch(r"\d{2,4}", cst) or not re.fullmatch(r"\d{4}", cfop):
            i += 1
            continue
        k += 2
        if k >= n or not _UN_RE.fullmatch(lines[k]):
            i += 1
            continue
        k += 1  # unit
        if k >= n or not _QTY_RE.fullmatch(lines[k]):
            i += 1
            continue
        quantidade = _parse_qty(lines[k])
        k += 1
        if k >= n or not _MONEY_RE.fullmatch(lines[k]):
            i += 1
            continue
        preco = normalize_decimal_price(parse_price_decimal(lines[k]) or Decimal("0"))
        k += 1
        if quantidade <= 0 or not preco:
            i += 1
            continue
        descricao = " ".join(desc_parts)
        descricao = re.sub(r"\s+", " ", descricao).strip()
        nome = descricao.upper()
        items.append(
            {
                "codigo": codigo,
                "descricao_original": descricao,
                "nome_curto": nome,
                "ncm_sh": ncm,
                "quantidade": quantidade,
                "preco": preco,
                "tamanho": tamanho,
            }
        )
        # jump past remaining tax columns of this row when possible
        i = k
    return items


def parse_vertical_danfe_products(text: str) -> list[Product]:
    from app.application.imports.parsing import _records_from_json_items, filter_suspect_records

    raw_items = parse_vertical_danfe_items(text)
    if not raw_items:
        return []
    records = _records_from_json_items(raw_items)
    return filter_suspect_records(records)


def vertical_danfe_extract_totals(text: str) -> dict[str, Any]:
    from app.application.imports.parsing import analyze_parsed_document

    products = parse_vertical_danfe_products(text)
    analysis = analyze_parsed_document(text, products)
    return {
        "products": products,
        "items": parse_vertical_danfe_items(text),
        "warnings": analysis.get("warnings") or [],
        "metrics": analysis.get("metrics") or {},
    }
