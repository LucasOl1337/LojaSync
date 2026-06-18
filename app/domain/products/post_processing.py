from __future__ import annotations

import re
from decimal import Decimal, ROUND_CEILING
from typing import Any

from app.domain.products.entities import Product, format_price
from app.domain.products.grade_utils import (
    NAME_NOISE_TOKENS,
    fold_token,
    is_known_grade_size,
    normalize_grade_label,
)
from app.domain.products.money import parse_price_decimal


def sanitize_store_name(value: str) -> str:
    text = str(value or "").upper().strip()
    if not text:
        return ""

    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\*[^*]*\*", " ", text)
    text = re.sub(r"(?i)\bCOR\s+[A-Z0-9]+\b", " ", text)
    text = re.sub(r"(?i)\bTAM(?:ANHO)?\s*[A-Z0-9]+\b", " ", text)
    text = re.sub(r"(?i)\b\d+\s*CM\b", " ", text)
    text = re.sub(r"(?i)\bREF(?:ERENCIA)?\s*[A-Z0-9-]+\b", " ", text)
    text = re.sub(r"(?i)\bCOD(?:IGO)?\s*[A-Z0-9-]+\b", " ", text)

    tokens = re.findall(r"[A-ZÀ-Ÿ0-9]+", text)
    cleaned: list[str] = []
    for token in tokens:
        folded = fold_token(token)
        normalized_size = normalize_grade_label(token)
        if not folded:
            continue
        if is_known_grade_size(normalized_size):
            continue
        if folded in NAME_NOISE_TOKENS:
            continue
        if folded.isdigit():
            continue
        if len(token) <= 2:
            continue
        if re.fullmatch(r"[A-Z]{3,4}", token) and not re.search(r"[AEIOUÁÉÍÓÚÃÕÂÊÔ]", token):
            continue
        cleaned.append(token)

    result = " ".join(cleaned)
    result = re.sub(r"\bBASICOA\b", "BASICO", result)
    result = re.sub(r"\bCALA\b", "CALCA", result)
    result = re.sub(r"\bCAMISETAA\b", "CAMISETA", result)
    result = re.sub(r"\bBLUSAA\b", "BLUSA", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def sanitize_code_for_store(value: str) -> str:
    code = re.sub(r"[^A-Za-z0-9]+", "", str(value or "").strip().upper())
    if not code:
        return ""

    repeated_chunk = re.fullmatch(r"([A-Z0-9]{2,})(?:\1)+", code)
    if repeated_chunk:
        return repeated_chunk.group(1)

    if re.search(r"(.)\1{3,}", code):
        code = re.sub(r"(.)\1{2,}", r"\1\1", code)

    for size in range(2, max(3, len(code) // 2 + 1)):
        if len(code) < size * 2:
            continue
        chunk = code[:size]
        if code == chunk * (len(code) // size) and len(code) % size == 0:
            return chunk
    return code


def normalize_price_to_next_tenth(value: str) -> str:
    parsed = parse_price_decimal(value)
    if parsed is None:
        return str(value or "").strip()
    normalized = (parsed * Decimal("10")).to_integral_value(rounding=ROUND_CEILING) / Decimal("10")
    return format_price(float(normalized)) or str(value or "").strip()


def coerce_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(parsed, 1.0))


def price_has_visual_noise(value: str) -> bool:
    parsed = parse_price_decimal(value)
    if parsed is None:
        return False
    cents = int((parsed * 100) % 100)
    return cents not in {0, 10, 20, 30, 40, 50, 60, 70, 80, 90}


def needs_llm_post_review(item: Product) -> bool:
    raw_name = str(item.descricao_completa or item.nome or "").strip().upper()
    current_name = str(item.nome or "").strip().upper()
    code = str(item.codigo or "").strip().upper()
    price = str(item.preco or "").strip()

    suspicious_name_patterns = [
        r"\bCOR\b",
        r"\[[^\]]+\]",
        r"\*[^*]+\*",
        r"\b[A-Z]{1}\b",
        r"\b[0-9]{2,}\s*CM\b",
        r"\bBASICO\s+A\b",
        r"\bCALA\b",
    ]
    if any(re.search(pattern, raw_name) for pattern in suspicious_name_patterns):
        return True
    if raw_name and current_name and raw_name != current_name:
        if len(raw_name) - len(current_name) >= 8:
            return True

    if len(code) >= 16:
        return True
    if re.fullmatch(r"([A-Z0-9]{2,})(?:\1)+", code):
        return True
    if re.search(r"(.)\1{4,}", code):
        return True

    if price_has_visual_noise(price):
        return True
    return False
