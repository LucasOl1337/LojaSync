from __future__ import annotations

from app.domain.products.grade_utils import (
    canonicalize_product_name,
    detect_size_from_name,
    extract_code_size_candidate,
    invoice_grade_sort_key,
    is_known_grade_size,
    normalize_grade_label,
    normalize_grades_map,
    sort_grade_items,
)


def test_normalize_grade_label_removes_size_words_and_left_zeroes() -> None:
    assert normalize_grade_label("Tam. 02") == "2"
    assert normalize_grade_label(" tamanho gg ") == "GG"
    assert normalize_grade_label("0") == ""


def test_known_grade_size_accepts_catalog_and_numeric_range() -> None:
    assert is_known_grade_size("GG")
    assert is_known_grade_size("6M")
    assert is_known_grade_size("56")
    assert not is_known_grade_size("57")
    assert not is_known_grade_size("ABC")


def test_detect_size_from_name_prefers_explicit_size_marker_then_suffix() -> None:
    assert detect_size_from_name("CONJUNTO BEBE Tam. 6M") == "6M"
    assert detect_size_from_name("CAMISETA Tam. 08") == "8"
    assert detect_size_from_name("BLUSA BASICA GG") == "GG"
    assert detect_size_from_name("BLUSA BASICA") is None


def test_extract_code_size_candidate_avoids_plain_numeric_codes_with_single_separator() -> None:
    assert extract_code_size_candidate("ABC-38") == ("ABC", "38")
    assert extract_code_size_candidate("123-38") is None
    assert extract_code_size_candidate("123/456/38") == ("123/456", "38")


def test_sort_grade_items_normalizes_and_orders_known_sizes() -> None:
    items = sort_grade_items({"GG": 1, "02": 2, "P": 3, "M": 2, "0": 10, "": 5})

    assert [(item.tamanho, item.quantidade) for item in items] == [
        ("2", 2),
        ("P", 3),
        ("M", 2),
        ("GG", 1),
    ]


def test_invoice_grade_sort_key_keeps_baby_months_before_alpha_and_numeric_sizes() -> None:
    sizes = ["10", "P", "9M", "2", "6M", "M", "RN"]

    assert sorted(sizes, key=invoice_grade_sort_key) == ["RN", "6M", "9M", "P", "M", "2", "10"]


def test_normalize_grades_map_skips_invalid_quantities() -> None:
    items = normalize_grades_map({"04": "2", "GG": 1, "P": 0, "M": "x"})

    assert [(item.tamanho, item.quantidade) for item in items] == [("4", 2), ("GG", 1)]


def test_canonicalize_product_name_removes_noise_sizes_and_duplicate_tokens() -> None:
    assert canonicalize_product_name("CALCA INF TAM 08") == "CALCA"
    assert canonicalize_product_name("BLUSA BLUSA FEM GG") == "BLUSA"
    assert canonicalize_product_name("02", "CONJUNTO BEBE TAM P") == "CONJUNTO"
