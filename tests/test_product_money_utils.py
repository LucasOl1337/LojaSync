from __future__ import annotations

from decimal import Decimal

from app.domain.products.money import normalize_decimal_price, normalize_raw_price, parse_price_decimal


def test_parse_price_decimal_accepts_brazilian_and_plain_decimal_formats() -> None:
    assert parse_price_decimal(0) == Decimal("0")
    assert parse_price_decimal("R$ 1.234,56") == Decimal("1234.56")
    assert parse_price_decimal("r$ 19,90") == Decimal("19.90")
    assert parse_price_decimal("RS 1.234,56") == Decimal("1234.56")
    assert parse_price_decimal("1,234.56") == Decimal("1234.56")
    assert parse_price_decimal("1.234.567") == Decimal("1234567")
    assert parse_price_decimal("33,495") == Decimal("33.495")
    assert parse_price_decimal("41.7") == Decimal("41.7")


def test_parse_price_decimal_returns_none_for_empty_or_invalid_values() -> None:
    assert parse_price_decimal(None) is None
    assert parse_price_decimal("") is None
    assert parse_price_decimal("sem preco") is None


def test_normalize_decimal_price_uses_half_up_and_brazilian_separator() -> None:
    assert normalize_decimal_price("1,234.56") == "1234,56"
    assert normalize_decimal_price("33,495") == "33,50"
    assert normalize_decimal_price("41.705") == "41,71"
    assert normalize_decimal_price(27.13) == "27,13"


def test_normalize_decimal_price_preserves_invalid_text_like_import_parser() -> None:
    assert normalize_decimal_price("sem preco") == "sem preco"
    assert normalize_decimal_price("x" * 45) == "x" * 40


def test_normalize_raw_price_formats_numbers_and_truncates_long_text() -> None:
    assert normalize_raw_price(0) == "0,00"
    assert normalize_raw_price(19.9) == "19,90"
    assert normalize_raw_price(None) == ""
    assert normalize_raw_price(" 19,90 ") == "19,90"
    assert normalize_raw_price("x" * 45) == "x" * 40
