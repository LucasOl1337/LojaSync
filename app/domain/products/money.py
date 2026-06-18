from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


def parse_price_decimal(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    normalized = text.replace("R$", "").replace(" ", "").replace("\u00a0", "")
    if "." in normalized and "," in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    elif normalized.count(".") > 1:
        normalized = normalized.replace(".", "")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def normalize_decimal_price(raw: Any, *, digits: int = 2) -> str:
    value = parse_price_decimal(raw)
    if value is None:
        return normalize_raw_price(raw)
    quantizer = Decimal("1").scaleb(-digits)
    normalized = value.quantize(quantizer, rounding=ROUND_HALF_UP)
    return format(normalized, "f").replace(".", ",")


def normalize_raw_price(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        return normalize_decimal_price(raw)
    text = str(raw).strip()
    if len(text) > 40:
        text = text[:40]
    return text
