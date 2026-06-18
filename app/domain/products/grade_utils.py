from __future__ import annotations

import re
import unicodedata

from app.domain.products.entities import GradeItem


MONTH_GRADE_SIZE_ORDER = {
    "RN": 0,
    "0M": 0,
    "1M": 1,
    "3M": 3,
    "6M": 6,
    "9M": 9,
    "12M": 12,
    "18M": 18,
    "24M": 24,
}
INVOICE_ALPHA_GRADE_SIZE_ORDER = {
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
GRADE_SIZE_ORDER = [
    "RN",
    "0M",
    "1M",
    "3M",
    "6M",
    "9M",
    "12M",
    "18M",
    "24M",
    "1",
    "2",
    "3",
    "4",
    "6",
    "8",
    "10",
    "12",
    "14",
    "16",
    "18",
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
GRADE_SIZE_INDEX = {label: index for index, label in enumerate(GRADE_SIZE_ORDER)}
NAME_NOISE_TOKENS = {
    "bb",
    "bebe",
    "bebea",
    "bebes",
    "inf",
    "infantil",
    "juvenil",
    "juv",
    "masc",
    "masculino",
    "fem",
    "feminino",
    "unisex",
    "unissex",
    "sort",
    "sortida",
    "sortido",
    "sortidos",
    "sortidas",
    "tam",
    "tamanho",
}


def fold_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_text.lower())


def normalize_grade_label(size: str) -> str:
    label = re.sub(r"(?i)\b(?:tam(?:anho)?\.?)\b", "", str(size or "")).strip().upper()
    label = re.sub(r"[^A-Z0-9]+", "", label)
    if not label:
        return ""
    if label.isdigit():
        try:
            number = int(label)
        except Exception:
            number = 0
        if number <= 0:
            return ""
        return str(number)
    return label


def is_known_grade_size(size: str) -> bool:
    label = normalize_grade_label(size)
    if not label:
        return False
    if label in GRADE_SIZE_INDEX:
        return True
    if label.isdigit():
        try:
            return 1 <= int(label) <= 56
        except Exception:
            return False
    return False


def grade_sort_key(size: str) -> tuple[int, int | str]:
    label = normalize_grade_label(size)
    if label in GRADE_SIZE_INDEX:
        return (0, GRADE_SIZE_INDEX[label])
    if label.isdigit():
        return (1, int(label))
    return (2, label)


def invoice_grade_sort_key(size: str) -> tuple[int, int | str]:
    label = normalize_grade_label(size)
    if label in MONTH_GRADE_SIZE_ORDER:
        return (0, MONTH_GRADE_SIZE_ORDER[label])
    if label in INVOICE_ALPHA_GRADE_SIZE_ORDER:
        return (1, INVOICE_ALPHA_GRADE_SIZE_ORDER[label])
    if label.isdigit():
        return (2, int(label))
    return (3, label)


def sort_grade_items(grades_map: dict[str, int]) -> list[GradeItem]:
    return [
        GradeItem(tamanho=size, quantidade=int(qty))
        for size, qty in sorted(
            (
                (normalize_grade_label(size), int(qty))
                for size, qty in (grades_map or {}).items()
                if normalize_grade_label(size) and int(qty or 0) > 0
            ),
            key=lambda item: grade_sort_key(item[0]),
        )
    ]


def normalize_grades_map(grades: dict[str, int]) -> list[GradeItem]:
    normalized: list[GradeItem] = []
    for tamanho, quantidade in (grades or {}).items():
        size = normalize_grade_label(str(tamanho or "").strip())
        try:
            qty = int(quantidade)
        except Exception:
            continue
        if not size or qty <= 0:
            continue
        normalized.append(GradeItem(tamanho=size, quantidade=qty))
    normalized.sort(key=lambda item: grade_sort_key(item.tamanho))
    return normalized


def detect_size_from_name(name: str) -> str | None:
    if not name:
        return None
    match = re.search(
        r"(?i)\b(?:tam(?:anho)?\.?\s*)([0-9]{1,3}m|[0-9]{1,3}|pp|p|m|g|gg|xg|xxg|g[1-4])\b",
        name,
    )
    if match:
        label = normalize_grade_label(match.group(1))
        if label:
            return label

    tokens = re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(name or "").upper())
    for token in reversed(tokens):
        label = normalize_grade_label(token)
        if is_known_grade_size(label):
            return label
    return None


def strip_size_suffix(name: str) -> str:
    if not name:
        return ""
    return canonicalize_product_name(name)


def extract_code_size_candidate(code: str) -> tuple[str, str] | None:
    value = str(code or "").strip()
    if not value:
        return None
    match = re.fullmatch(r"(.+?)([-_/])([A-Za-z0-9]+)", value)
    if not match:
        return None
    base = str(match.group(1) or "").strip()
    suffix = normalize_grade_label(match.group(3))
    if not base or not suffix or not is_known_grade_size(suffix):
        return None
    separators = sum(value.count(token) for token in "-_/")
    if suffix.isdigit() and not any(char.isalpha() for char in base) and separators < 2:
        return None
    return base, suffix


def canonicalize_product_name(name: str, descricao_completa: str | None = None) -> str:
    source = str(descricao_completa or name or "").strip()
    if not source:
        return ""

    tokens = re.findall(r"[A-Za-zÀ-ÿ0-9]+", source.upper())
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
        if cleaned and cleaned[-1] == token:
            continue
        cleaned.append(token)

    result = " ".join(cleaned).strip()
    if result:
        return result

    fallback = re.sub(r"[\-_]+", " ", source)
    fallback = re.sub(r"\s+", " ", fallback).strip()
    return fallback or str(name or "").strip()
